#!/usr/bin/env python3
import os
import sys
import argparse
import tempfile
import json
import subprocess
import signal

SCHEMA = {
    "type": "object",
    "properties": {
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "severity": {"type": "string", "enum": ["P0", "P1", "P2"]},
                    "description": {"type": "string", "minLength": 1}
                },
                "required": ["severity", "description"],
                "additionalProperties": False
            }
        }
    },
    "required": ["issues"],
    "additionalProperties": False
}

def main():
    try:
        _main()
    except OSError as e:
        print(f"Fatal: I/O error: {e}", file=sys.stderr)
        sys.exit(2)

def _main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True, help="Absolute path to target file")
    parser.add_argument("--mode", required=True, choices=["plan", "code"])
    parser.add_argument("--repo", required=True, help="Absolute path to repo")
    parser.add_argument("--message", help="Optional message")
    parser.add_argument("--session-id", help="Optional session id to resume")
    args = parser.parse_args()

    target = os.path.realpath(args.target)
    if not os.path.isfile(target):
        print(f"Fatal: target is not a file: {target}", file=sys.stderr)
        sys.exit(2)
    repo = os.path.realpath(args.repo)
    if not os.path.isdir(repo):
        print(f"Fatal: repo is not a directory: {repo}", file=sys.stderr)
        sys.exit(2)

    with tempfile.TemporaryDirectory() as work_dir:
        review_file = os.path.join(work_dir, "review.json")
        schema_path = os.path.join(work_dir, "schema.json")
        with open(schema_path, 'w') as f:
            json.dump(SCHEMA, f)
        
        prompt_text = f"Perform a {args.mode} review of this file: " + target
        if args.mode == "plan":
            prompt_text += "\nFocus on architectural design and planning criteria."
        elif args.mode == "code":
            prompt_text += "\nFocus on code-level issues, logic, and correctness."
        prompt_text += "\nUse severity P0 or P1 for functional/correctness defects (these block execution)."
        prompt_text += "\nUse severity P2 for advisory/style feedback only."
        prompt_text += "\nContext: Before reviewing, please read the `.tribunal/adr/` directory for historical Architecture Decision Records, and the `.tribunal/tech_debt/` directory for accepted known issues and out-of-scope items. Do not raise P0/P1 issues for items explicitly documented as technical debt."
        if args.message:
            prompt_text += "\nMessage: " + args.message

        fout_path = os.path.join(work_dir, "stdout.log")
        ferr_path = os.path.join(work_dir, "stderr.log")
        
        if args.session_id:
            cmd = [
                "codex", "exec", "-C", repo, "--sandbox", "read-only", 
                "--json", "resume", args.session_id, 
                "--output-schema", schema_path, "-o", review_file, prompt_text
            ]
        else:
            cmd = [
                "codex", "exec", "-C", repo, "--sandbox", "read-only", 
                "--json", "--output-schema", schema_path, "-o", review_file, prompt_text
            ]
            
        with open(fout_path, "w") as fout, open(ferr_path, "w") as ferr:
            try:
                process = subprocess.Popen(cmd, stdout=fout, stderr=ferr, stdin=subprocess.DEVNULL, start_new_session=True)
            except OSError as e:
                print(f"Fatal: codex launch failed: {e}", file=sys.stderr)
                sys.exit(2)
            
            try:
                process.communicate(timeout=1800)
            except subprocess.TimeoutExpired:
                try: os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError: pass
                
                try: process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    try: os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                    process.communicate()
                print("Fatal: codex launch timed out", file=sys.stderr)
                sys.exit(2)
            except BaseException as e:
                try: os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError: pass
                process.communicate()
                raise e

        if process.returncode != 0:
            print(f"Fatal: codex command failed with code {process.returncode}", file=sys.stderr)
            sys.exit(2)

        session_id = args.session_id
        if not session_id:
            with open(fout_path, 'r') as fr:
                for line in fr:
                    try:
                        msg = json.loads(line)
                        if msg.get("type") == "thread.started" and "thread_id" in msg:
                            t_id = msg["thread_id"]
                            if isinstance(t_id, str) and t_id:
                                session_id = t_id
                                break
                    except Exception:
                        pass
            if not session_id:
                print("Fatal: Could not find thread.started event in stdout.log.", file=sys.stderr)
                sys.exit(2)

        if not os.path.exists(review_file):
            print("Fatal: review.json missing.", file=sys.stderr)
            sys.exit(2)
            
        try:
            with open(review_file, 'r') as f:
                review = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            print("Fatal: review.json corrupt.", file=sys.stderr)
            sys.exit(2)
            
        if not isinstance(review, dict) or set(review.keys()) != {"issues"} or not isinstance(review["issues"], list):
            print("Fatal: Invalid review.json format.", file=sys.stderr)
            sys.exit(2)
            
        for item in review["issues"]:
            if not isinstance(item, dict) or set(item.keys()) != {"severity", "description"}:
                print("Fatal: Invalid review.json format, issue item properties.", file=sys.stderr)
                sys.exit(2)
            if "severity" not in item or item["severity"] not in ["P0", "P1", "P2"]:
                print("Fatal: Invalid review.json format, missing or invalid severity.", file=sys.stderr)
                sys.exit(2)
            if "description" not in item or not isinstance(item["description"], str) or not item["description"].strip():
                print("Fatal: Invalid review.json format, description.", file=sys.stderr)
                sys.exit(2)

        review["session_id"] = session_id
        
        print(json.dumps(review))
        
        blocking_issues = [i for i in review["issues"] if i.get("severity") in ["P0", "P1"]]
        if not blocking_issues:
            sys.exit(0)
        else:
            sys.exit(1)

if __name__ == "__main__":
    main()
