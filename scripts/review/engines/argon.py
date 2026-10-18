"""Argon Web Reviewer Engine Adapter."""
import os
import sys
import tempfile
import json
import re
import shutil
import uuid
from typing import List, Dict, Tuple, Optional, Any

from review.engines.base import ReviewEngineAdapter


class ArgonWebAdapter(ReviewEngineAdapter):
    DEFAULT_SKILL = "@software-architect-reviewer"

    def resolve_binary(self) -> List[str]:
        if not shutil.which("osascript"):
            print("Fatal: 'osascript' not found on PATH. Argon Web Reviewer requires macOS with AppleScript support.", file=sys.stderr)
            sys.exit(2)

        env_bin = os.environ.get("ARGON_RUNNER_BIN")
        if env_bin:
            if not os.path.isfile(env_bin):
                print(f"Fatal: ARGON_RUNNER_BIN points to invalid path: {env_bin}", file=sys.stderr)
                sys.exit(2)
            if env_bin.endswith(".py"):
                return [sys.executable, env_bin]
            return [env_bin]

        # Locate default runner inside scripts/review/runners/
        runner_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "runners", "edge_applescript_runner.py")
        )
        if not os.path.isfile(runner_path):
            print(f"Fatal: Argon runner script not found at {runner_path}", file=sys.stderr)
            sys.exit(2)

        return [sys.executable, runner_path]

    def build_command(
        self,
        launcher_cmd: List[str],
        repo_path: str,
        schema_path: str,
        review_file_path: str,
        prompt_text: str,
        session_id: Optional[str],
        model: Optional[str]
    ) -> List[str]:
        # Determine skill / model tag
        if model:
            skill = model.strip()
        elif os.environ.get("ARGON_SKILL"):
            skill = os.environ["ARGON_SKILL"].strip()
        else:
            skill = self.DEFAULT_SKILL

        if skill and not (skill.startswith("@") or skill.startswith("/")):
            skill = f"@{skill}"

        cmd = list(launcher_cmd)

        work_dir = os.path.dirname(review_file_path) if review_file_path else ""
        target_copy = os.path.join(work_dir, "target.file") if work_dir else "target.file"
        if os.path.isfile(target_copy):
            target_file = target_copy
        else:
            target_file = target_copy
            if work_dir and os.path.isdir(work_dir) and not os.path.exists(target_file):
                try:
                    with open(target_file, "w", encoding="utf-8") as tf:
                        tf.write(prompt_text or "")
                except OSError:
                    pass

        cmd.append(target_file)
        cmd.extend(["--out", review_file_path])
        if schema_path:
            cmd.extend(["--schema", schema_path])
        cmd.extend(["--skill", skill])
        cmd.append("--json-prompt")
        if prompt_text:
            cmd.extend(["--prompt", prompt_text])

        return cmd

    def get_execution_environment(self) -> Dict[str, str]:
        return {
            "PATH": os.environ.get("PATH", ""),
            "HOME": os.environ.get("HOME", ""),
            "USER": os.environ.get("USER", ""),
            "TMPDIR": tempfile.gettempdir()
        }

    def _normalize_issues(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean issues list."""
        issues = data.get("issues", [])
        if not isinstance(issues, list):
            return {"issues": []}
        cleaned = []
        for item in issues:
            if not isinstance(item, dict):
                continue
            raw_severity = str(item.get("severity", "")).strip()
            norm_severity = raw_severity.strip("[]").upper()
            if norm_severity in ("P0", "P1", "P2"):
                severity = norm_severity
            elif norm_severity in ("CRITICAL/BLOCKER", "CRITICAL", "BLOCKER", "HIGH"):
                severity = "P0"
            elif norm_severity in ("WARNING", "MEDIUM", "MODERATE"):
                severity = "P1"
            elif norm_severity in ("SUGGESTION", "LOW", "INFO", "MINOR"):
                severity = "P2"
            else:
                severity = "P1"

            description = item.get("description", "")
            if not description:
                for alt_key in ("details", "message", "summary", "finding", "title", "comment", "text", "note"):
                    if alt_key in item and item[alt_key]:
                        description = str(item[alt_key])
                        break
            if description and isinstance(description, str) and description.strip():
                cleaned.append({
                    "severity": severity,
                    "description": description.strip()
                })
        return {"issues": cleaned}

    def _parse_payload(self, content: str) -> Dict[str, Any]:
        """Hybrid JSON and markdown extractor."""
        refusal_pattern = re.compile(
            r"\b(something went wrong|usage limit|safety refusal|unable to process|I cannot fulfill|error:)\b",
            re.IGNORECASE
        )
        if refusal_pattern.search(content):
            print("Fatal: Error or refusal banner detected in review response.", file=sys.stderr)
            sys.exit(2)

        # 1. Try direct JSON parsing
        try:
            data = json.loads(content)
            if isinstance(data, dict) and "issues" in data and isinstance(data["issues"], list):
                return self._normalize_issues(data)
            elif isinstance(data, list):
                return self._normalize_issues({"issues": data})
        except json.JSONDecodeError:
            pass

        # 2. Try fenced code blocks (```json ... ``` or ``` ... ```) in reverse order
        fence_pattern = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)
        for match in reversed(list(fence_pattern.finditer(content))):
            block = match.group(1).strip()
            try:
                data = json.loads(block)
                if isinstance(data, dict) and "issues" in data and isinstance(data["issues"], list):
                    return self._normalize_issues(data)
            except json.JSONDecodeError:
                continue

        # 3. Fallback markdown severity parser
        # Matches: [Critical/Blocker], [Critical], [Blocker] -> P0
        #          [Warning] -> P1
        #          [Suggestion] -> P2
        tag_pattern = re.compile(
            r"(?:^|\n)\s*(?:[\*\-\d\.]+\s+|#+\s+)?\[(Critical/Blocker|Critical|Blocker|Warning|Suggestion)\]:?\s*(.*?)(?=(?:\n\s*(?:[\*\-\d\.]+\s+|#+\s+)?\[(?:Critical/Blocker|Critical|Blocker|Warning|Suggestion)\])|\Z)",
            re.IGNORECASE | re.DOTALL
        )

        matches = list(tag_pattern.finditer(content))
        if matches:
            issues = []
            for m in matches:
                tag = m.group(1).lower()
                desc = m.group(2).strip()
                if "critical" in tag or "blocker" in tag:
                    severity = "P0"
                elif "warning" in tag:
                    severity = "P1"
                elif "suggestion" in tag:
                    severity = "P2"
                else:
                    severity = "P1"

                if desc:
                    issues.append({
                        "severity": severity,
                        "description": desc
                    })
            if issues:
                return {"issues": issues}

        # 4. Check for explicit approval / zero issues statements
        approval_pattern = re.compile(
            r"\b(status:\s*approved|verdict:\s*approved|no issues found|no defects found|no critical issues|review passed|all checks passed)\b",
            re.IGNORECASE
        )
        if approval_pattern.search(content) and not refusal_pattern.search(content):
            return {"issues": []}

        # 5. Failed to parse
        print("Fatal: Could not parse review payload into valid schema.", file=sys.stderr)
        sys.exit(2)

    def extract_review_payload_and_session(
        self,
        stdout_path: str,
        stderr_path: str,
        review_file_path: str,
        prior_session_id: Optional[str]
    ) -> Tuple[Dict[str, Any], str]:
        # Bind or generate formatted session ID
        if prior_session_id:
            if prior_session_id.startswith("argon-web:"):
                formatted_session = prior_session_id
            else:
                formatted_session = f"argon-web:{prior_session_id}"
        else:
            formatted_session = f"argon-web:{uuid.uuid4()}"

        if not os.path.exists(review_file_path):
            print("Fatal: review.json missing.", file=sys.stderr)
            sys.exit(2)

        try:
            with open(review_file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
        except OSError as e:
            print(f"Fatal: Failed reading review.json: {e}", file=sys.stderr)
            sys.exit(2)

        if not content:
            print("Fatal: review.json is empty.", file=sys.stderr)
            sys.exit(2)

        review = self._parse_payload(content)

        # Write clean normalized JSON back to review_file_path
        try:
            with open(review_file_path, "w", encoding="utf-8") as f:
                json.dump(review, f, indent=2)
        except OSError:
            pass

        return review, formatted_session
