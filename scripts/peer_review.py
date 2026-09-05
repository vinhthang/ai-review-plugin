#!/usr/bin/env python3
import os
import sys
import argparse
import tempfile
import fcntl
import json
import subprocess
import shutil

SCHEMA = {
    "type": "object",
    "properties": {
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "severity": {"type": "string", "enum": ["P0", "P1", "P2"]},
                    "description": {"type": "string"}
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True, help="Absolute path to target file")
    parser.add_argument("--mode", required=True, choices=["plan", "code"])
    parser.add_argument("--repo", required=True, help="Absolute path to repo")
    parser.add_argument("--work-dir", help="Optional work dir for resuming")
    parser.add_argument("--message", help="Optional message")
    parser.add_argument("--debug", action="store_true", help="Debug mode")
    args = parser.parse_args()

    target = os.path.realpath(args.target)
    repo = os.path.realpath(args.repo)
    
    if args.work_dir:
        work_dir = os.path.realpath(args.work_dir)
        temp_dir = os.path.realpath(os.path.join(repo, ".tribunal"))
        
        if not os.path.exists(work_dir):
            print("Fatal: work_dir does not exist.", file=sys.stderr)
            sys.exit(2)

        if not work_dir.startswith(temp_dir + os.sep) or "tribunal_run_" not in os.path.basename(work_dir):
            print("Fatal: Invalid work_dir path.", file=sys.stderr)
            sys.exit(2)
        if os.stat(work_dir).st_uid != os.getuid():
            print("Fatal: Invalid work_dir ownership.", file=sys.stderr)
            sys.exit(2)
    else:
        temp_dir = os.path.join(repo, ".tribunal")
        os.makedirs(temp_dir, exist_ok=True)
        work_dir = tempfile.mkdtemp(dir=temp_dir, prefix="tribunal_run_")
        with open(os.path.join(work_dir, ".tribunal_marker"), "w") as f:
            f.write("")
    
    print(work_dir)
    sys.stdout.flush()

    lock_file_path = os.path.join(work_dir, "state.lock")
    with open(lock_file_path, 'a'): pass
    
    with open(lock_file_path, 'r+') as lock_f:
        fcntl.flock(lock_f, fcntl.LOCK_EX)
        try:
            if not os.path.exists(work_dir):
                print("Fatal: work_dir was deleted while waiting for lock.", file=sys.stderr)
                sys.exit(2)

            state_file = os.path.join(work_dir, "state.json")
            
            if os.path.exists(state_file):
                with open(state_file, 'r') as f:
                    try:
                        state = json.load(f)
                    except json.JSONDecodeError:
                        print("Fatal: Corrupt state.json", file=sys.stderr)
                        sys.exit(2)
                
                if args.mode != state.get("mode") or args.target != state.get("target") or args.repo != state.get("repo"):
                    print("Fatal: Mismatched arguments.", file=sys.stderr)
                    sys.exit(2)
                
                attempt = state.get("attempt", 1) + 1
            else:
                state = {
                    "mode": args.mode,
                    "target": args.target,
                    "repo": args.repo,
                    "attempt": 1
                }
                attempt = 1
                
            if attempt > 5:
                print("Fatal: Max attempts exceeded.", file=sys.stderr)
                sys.exit(2)

            state["attempt"] = attempt
            
            review_file = os.path.join(work_dir, "review.json")
            if os.path.exists(review_file):
                os.remove(review_file)
            
            schema_path = os.path.join(work_dir, "schema.json")
            with open(schema_path, 'w') as f:
                json.dump(SCHEMA, f)
            
            fout = open(os.path.join(work_dir, "stdout.log"), 'a+')
            ferr = open(os.path.join(work_dir, "stderr.log"), 'a+')
            
            prompt_text = "Review this file: " + args.target
            if args.message:
                prompt_text += "\nMessage: " + args.message
                
            prompt_file = os.path.join(work_dir, "prompt.txt")
            with open(prompt_file, 'w') as f:
                f.write(prompt_text)
                
            if attempt == 1:
                cmd = ["codex", "exec", "-C", args.repo, "--sandbox", "read-only", "--json", "--output-schema", schema_path, "-o", review_file, prompt_file]
                fout.seek(0)
                fout.truncate()
                ferr.seek(0)
                ferr.truncate()
            else:
                session_id = state.get("session_id")
                if not session_id:
                    fout.seek(0)
                    for line in fout:
                        try:
                            msg = json.loads(line)
                            if msg.get("type") == "thread.started" and "thread_id" in msg:
                                session_id = msg["thread_id"]
                                state["session_id"] = session_id
                                break
                        except Exception:
                            pass
                if not session_id:
                    print("Fatal: Could not find session_id from previous run", file=sys.stderr)
                    sys.exit(2)
                
                cmd = ["codex", "exec", "resume", session_id, "--output-schema", schema_path, "-o", review_file, prompt_file]

            with open(state_file, 'w') as f:
                json.dump(state, f)

            process = subprocess.run(cmd, stdout=fout, stderr=ferr, stdin=subprocess.DEVNULL)
            fout.close()
            ferr.close()
            
            if process.returncode != 0:
                print(f"Fatal: codex command failed with code {process.returncode}", file=sys.stderr)
                sys.exit(2)
                
            if not os.path.exists(review_file):
                print("Fatal: review.json missing.", file=sys.stderr)
                sys.exit(2)
                
            try:
                with open(review_file, 'r') as f:
                    review = json.load(f)
            except json.JSONDecodeError:
                print("Fatal: review.json corrupt.", file=sys.stderr)
                sys.exit(2)
                
            if "issues" not in review or not isinstance(review["issues"], list):
                print("Fatal: Invalid review.json format, 'issues' missing or not a list.", file=sys.stderr)
                sys.exit(2)

            issues = review.get("issues", [])
            blocking_issues = [i for i in issues if i.get("severity") in ["P0", "P1"]]
            non_blocking_issues = [i for i in issues if i.get("severity") == "P2"]

            if not blocking_issues:
                for issue in non_blocking_issues:
                    print(issue.get("description"))
                if not args.debug:
                    if os.path.exists(os.path.join(work_dir, ".tribunal_marker")):
                        try:
                            shutil.rmtree(work_dir)
                        except Exception:
                            pass
                sys.exit(0)
            else:
                for issue in blocking_issues:
                    print(f"[{issue.get('severity')}] {issue.get('description')}", file=sys.stderr)
                
                if attempt == 5:
                    print("Fatal: Max attempts reached, blocking issues remain.", file=sys.stderr)
                    sys.exit(2)
                    
                sys.exit(1)

        finally:
            fcntl.flock(lock_f, fcntl.LOCK_UN)

if __name__ == "__main__":
    main()
