"""Codex Reviewer Adapter."""
import os
import sys
import subprocess
import tempfile
import json
import signal
import shutil
import re
from typing import List, Dict, Tuple, Optional, Any

from review.engines.base import ReviewEngineAdapter

class CodexAdapter(ReviewEngineAdapter):
    def resolve_binary(self) -> List[str]:
        env_bin = os.environ.get("CODEX_BIN")
        if env_bin:
            if not os.path.isfile(env_bin) or not os.access(env_bin, os.X_OK):
                print(f"Fatal: CODEX_BIN points to invalid path: {env_bin}", file=sys.stderr)
                sys.exit(2)
            return [env_bin]
        return ["codex"]

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
        codex_bin = launcher_cmd[0]
        unprefixed = None
        if session_id:
            unprefixed = session_id[len("codex:"):] if session_id.startswith("codex:") else session_id

        cmd = [
            codex_bin, "exec", "-C", repo_path, "--sandbox", "read-only",
            "--ignore-rules", "--ignore-user-config", "--skip-git-repo-check"
        ]
        if model:
            cmd.extend(["--model", model])
        cmd.append("--json")
        if unprefixed:
            cmd.extend(["resume", unprefixed])
        cmd.extend(["--output-schema", schema_path, "-o", review_file_path, prompt_text])
        return cmd

    def get_execution_environment(self) -> Dict[str, str]:
        env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": os.environ.get("HOME", ""),
            "USER": os.environ.get("USER", ""),
            "TMPDIR": tempfile.gettempdir()
        }
        if "OPENAI_API_KEY" in os.environ:
            env["OPENAI_API_KEY"] = os.environ["OPENAI_API_KEY"]
        return env

    def extract_review_payload_and_session(
        self,
        stdout_path: str,
        stderr_path: str,
        review_file_path: str,
        prior_session_id: Optional[str]
    ) -> Tuple[Dict[str, Any], str]:
        raw_session_id = prior_session_id
        if not raw_session_id:
            if os.path.isfile(stdout_path):
                with open(stdout_path, "r", encoding="utf-8") as fr:
                    for line in fr:
                        cleaned_line = line.strip()
                        if not cleaned_line:
                            continue
                        try:
                            msg = json.loads(cleaned_line)
                            if isinstance(msg, dict) and msg.get("type") == "thread.started" and "thread_id" in msg:
                                t_id = msg["thread_id"]
                                if isinstance(t_id, str) and t_id:
                                    raw_session_id = t_id
                                    break
                        except json.JSONDecodeError as err:
                            print(f"Debug: skipping non-json stdout line: {err}", file=sys.stderr)

        if not raw_session_id:
            print("Fatal: Could not find thread.started event in stdout.log.", file=sys.stderr)
            sys.exit(2)

        formatted_session = raw_session_id

        if not os.path.exists(review_file_path):
            print("Fatal: review.json missing.", file=sys.stderr)
            sys.exit(2)

        try:
            with open(review_file_path, "r", encoding="utf-8") as f:
                review = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            print("Fatal: review.json corrupt.", file=sys.stderr)
            sys.exit(2)

        return review, formatted_session
