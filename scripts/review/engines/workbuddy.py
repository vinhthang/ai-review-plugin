"""WorkBuddy AI Reviewer Adapter."""
import os
import sys
import subprocess
import tempfile
import json
import signal
import shutil
import re
import stat
from typing import List, Dict, Tuple, Optional, Any

from review.models import WORKBUDDY_MODEL_MAP
from review.engines.base import ReviewEngineAdapter

class WorkBuddyAdapter(ReviewEngineAdapter):
    def resolve_binary(self) -> List[str]:
        # 1. Check WORKBUDDY_BIN
        env_bin = os.environ.get("WORKBUDDY_BIN")
        if env_bin:
            if not os.path.isfile(env_bin):
                print(f"Fatal: WORKBUDDY_BIN points to non-existent path: {env_bin}", file=sys.stderr)
                sys.exit(2)
            if os.access(env_bin, os.X_OK):
                return [env_bin]
            if env_bin.endswith(".js"):
                node = self._find_node()
                return [node, env_bin]
            print(f"Fatal: WORKBUDDY_BIN is neither executable nor a recognized JavaScript bundle: {env_bin}", file=sys.stderr)
            sys.exit(2)

        # 2. Check standard macOS Application Bundle path
        bundle_bin = "/Applications/WorkBuddy AI.app/Contents/Resources/app.asar.unpacked/cli/bin/codebuddy"
        if os.path.isfile(bundle_bin):
            node = self._find_node()
            return [node, bundle_bin]

        # 3. Check PATH
        path_bin = shutil.which("codebuddy")
        if path_bin:
            if not os.access(path_bin, os.X_OK):
                print(f"Fatal: Discovered codebuddy on PATH is not executable: {path_bin}", file=sys.stderr)
                sys.exit(2)
            return [path_bin]

        raise FileNotFoundError("WorkBuddy CLI ('codebuddy') not found. Set WORKBUDDY_BIN or install WorkBuddy AI.")

    def _find_node(self) -> str:
        node = shutil.which("node")
        if node:
            return node
        for fallback in ["/opt/homebrew/bin/node", "/usr/local/bin/node"]:
            if os.path.isfile(fallback) and os.access(fallback, os.X_OK):
                return fallback
        print("Fatal: Node.js runtime not found required to execute WorkBuddy script bundle.", file=sys.stderr)
        sys.exit(2)

    def normalize_model(self, raw_model: Optional[str]) -> str:
        if not raw_model:
            raw_model = os.environ.get("WORKBUDDY_MODEL", "deepseek-v4.1-flash")
        cleaned = raw_model.strip().lower()
        return WORKBUDDY_MODEL_MAP.get(cleaned, raw_model.strip())

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
        target_model = self.normalize_model(model)
        cmd = list(launcher_cmd) + [
            "-p",
            "--model", target_model,
            "--output-format", "json",
            "-y",
            "--disallowedTools", "Bash,Write,Edit,NotebookEdit",
            "--json-schema", schema_path
        ]
        if session_id:
            unprefixed = session_id[len("workbuddy:"):] if session_id.startswith("workbuddy:") else session_id
            cmd.extend(["-r", unprefixed])
        cmd.append(prompt_text)
        return cmd

    def get_execution_environment(self) -> Dict[str, str]:
        env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": os.environ.get("HOME", ""),
            "USER": os.environ.get("USER", ""),
            "TMPDIR": tempfile.gettempdir(),
            "CODEBUDDY_FORCE_HEADLESS_BUNDLE": "1"
        }
        return env

    def extract_review_payload_and_session(
        self,
        stdout_path: str,
        stderr_path: str,
        review_file_path: str,
        prior_session_id: Optional[str]
    ) -> Tuple[Dict[str, Any], str]:
        if not os.path.isfile(stdout_path):
            print("Fatal: stdout.log missing from WorkBuddy execution.", file=sys.stderr)
            sys.exit(2)

        with open(stdout_path, "r", encoding="utf-8") as f:
            content = f.read().strip()

        if not content:
            print("Fatal: WorkBuddy stdout output is empty.", file=sys.stderr)
            self._dump_stderr(stderr_path)
            sys.exit(2)

        events: List[Dict[str, Any]] = []
        # Attempt JSON array parsing
        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                events = [e for e in parsed if isinstance(e, dict)]
            elif isinstance(parsed, dict):
                events = [parsed]
        except json.JSONDecodeError:
            # Fallback to NDJSON
            for line in content.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict):
                        events.append(obj)
                except json.JSONDecodeError:
                    continue

        result_events = [e for e in events if e.get("type") == "result"]
        if len(result_events) == 0:
            print("Fatal: No result event found in WorkBuddy stdout stream.", file=sys.stderr)
            self._dump_stderr(stderr_path)
            sys.exit(2)
        if len(result_events) > 1:
            print(f"Fatal: Multiple result events detected in WorkBuddy stdout stream ({len(result_events)}). Expected exactly one.", file=sys.stderr)
            sys.exit(2)

        terminal = result_events[0]
        if terminal.get("subtype") != "success":
            err_msg = terminal.get("error") or terminal.get("message") or "Unknown WorkBuddy error"
            print(f"Fatal: WorkBuddy returned error subtype: {sanitize_diagnostics(str(err_msg))}", file=sys.stderr)
            sys.exit(2)

        raw_session_id = terminal.get("session_id")
        if not raw_session_id:
            if prior_session_id:
                raw_session_id = prior_session_id[len("workbuddy:"):] if prior_session_id.startswith("workbuddy:") else prior_session_id
            else:
                print("Fatal: Could not determine session identifier from WorkBuddy execution.", file=sys.stderr)
                sys.exit(2)

        formatted_session = f"workbuddy:{raw_session_id}"

        # WorkBuddy may populate 'structured_output' or 'result'
        raw_payload = terminal.get("structured_output") or terminal.get("result")
        if not raw_payload:
            for ev in reversed(events):
                if ev.get("structured_output"):
                    raw_payload = ev["structured_output"]
                    break
                if ev.get("name") == "StructuredOutput" or ev.get("type") in ("tool_call", "tool_use"):
                    raw_payload = ev.get("arguments") or ev.get("input") or ev.get("parameters")
                    if raw_payload:
                        break
                for tc in ev.get("tool_calls", []):
                    if tc.get("name") == "StructuredOutput" or tc.get("function", {}).get("name") == "StructuredOutput":
                        raw_payload = tc.get("arguments") or tc.get("input") or tc.get("function", {}).get("arguments")
                        if raw_payload:
                            break
                if raw_payload:
                    break
        if not raw_payload:
            print("Fatal: Could not find structured_output or result in WorkBuddy output stream.", file=sys.stderr)
            self._dump_stderr(stderr_path)
            sys.exit(2)

        if isinstance(raw_payload, str):
            cleaned = raw_payload.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
            try:
                review_dict = json.loads(cleaned)
            except json.JSONDecodeError as exc:
                print(f"Fatal: review.json corrupt in WorkBuddy result payload: {exc}", file=sys.stderr)
                sys.exit(2)
        elif isinstance(raw_payload, dict):
            review_dict = raw_payload
        else:
            print("Fatal: WorkBuddy result is neither string nor dictionary.", file=sys.stderr)
            sys.exit(2)

        # Unwrap {"data": {"issues": [...]}} if wrapped by WorkBuddy tool call
        if isinstance(review_dict, dict) and "data" in review_dict and isinstance(review_dict["data"], dict) and "issues" in review_dict["data"]:
            review_dict = review_dict["data"]

        with open(review_file_path, "w", encoding="utf-8") as rf:
            json.dump(review_dict, rf)

        return review_dict, formatted_session

    def _dump_stderr(self, stderr_path: str):
        if os.path.isfile(stderr_path):
            with open(stderr_path, "r", encoding="utf-8") as f:
                content = f.read()
                if content:
                    print(sanitize_diagnostics(content), file=sys.stderr)
