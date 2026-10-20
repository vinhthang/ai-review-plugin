"""Audit Stage: Target resolution, prompt generation, review execution, and verdict evaluation."""
import argparse
import fnmatch
import json
import os
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional, Tuple

try:
    from review.models import SCHEMA, extract_issue_description, format_review_envelope, sanitize_diagnostics
    from review.engines import get_engine_adapter, resolve_engine
    from review.prompts import (
        build_adr_context, build_review_prompt, build_audit_prompt, load_diagnostic_text, load_prior_review_text,
    )
except ImportError:
    from scripts.review.models import SCHEMA, extract_issue_description, format_review_envelope, sanitize_diagnostics
    from scripts.review.engines import get_engine_adapter, resolve_engine
    from scripts.review.prompts import (
        build_adr_context, build_review_prompt, build_audit_prompt, load_diagnostic_text, load_prior_review_text,
    )

VERDICT_LEAK_FILES: frozenset[str] = frozenset({
    "review.md",
    "SELF_REVIEW.md",
    "REVERIFICATION_REPORT.md",
    "architecture_review.md",
    "traceability_audit.json",
})


def is_verdict_leak_file(filename: str, allowed_names: frozenset[str] = frozenset()) -> bool:
    if filename in (VERDICT_LEAK_FILES - allowed_names):
        return True
    if fnmatch.fnmatch(filename, "review_round_*.md") and filename not in allowed_names:
        return True
    return False


def assert_no_verdict_leaks(sandbox_dir: str, allowed_names: frozenset[str] = frozenset(), **kwargs) -> None:
    """Walk sandbox_dir (skipping .git) and raise ValueError if any verdict leak file exists."""
    if "allowed_Names" in kwargs:
        allowed_names = kwargs["allowed_Names"]
    disallowed = VERDICT_LEAK_FILES - allowed_names
    for root, dirs, files in os.walk(sandbox_dir):
        if ".git" in dirs:
            dirs.remove(".git")
        for f in files:
            if (f in disallowed) or (fnmatch.fnmatch(f, "review_round_*.md") and f not in allowed_names):
                rel = os.path.relpath(os.path.join(root, f), sandbox_dir)
                raise ValueError(f"Evaluator verdict leak in sandbox: {rel}")


def prepare_repo_sandbox(repo: str, work_dir: Optional[str] = None) -> str:
    """Create a sandbox copy of repo in work_dir excluding VCS, build artifacts, and verdict leak files."""
    if work_dir is None:
        work_dir = tempfile.mkdtemp(prefix="repo_sandbox_")
    repo_copy = os.path.join(work_dir, "repo")
    rsync_bin = shutil.which("rsync")
    leak_excludes = [f"--exclude={f}" for f in sorted(VERDICT_LEAK_FILES)] + ["--exclude=review_round_*.md"]
    excludes = ["--exclude=.git", "--exclude=.gemini", "--exclude=AGENTS.md", "--exclude=target", "--exclude=node_modules"] + leak_excludes

    copied = False
    if rsync_bin:
        try:
            os.mkdir(repo_copy)
            subprocess.run([rsync_bin, "-a", *excludes, f"{repo}/", f"{repo_copy}/"], check=True)
            copied = True
        except (subprocess.CalledProcessError, OSError, ValueError) as e:
            print(f"Warning: rsync failed ({e}), falling back to shutil.copytree", file=sys.stderr)
            if os.path.exists(repo_copy):
                shutil.rmtree(repo_copy)
    if not copied:
        def ignore_filter(p, names):
            ignored = {n for n in names if n in {".git", ".gemini", "AGENTS.md", "target", "node_modules"}}
            for n in names:
                if is_verdict_leak_file(n):
                    ignored.add(n)
            return ignored
        shutil.copytree(repo, repo_copy, ignore=ignore_filter, dirs_exist_ok=True)

    # Ensure all matching verdict leak files are removed after copying/cloning
    for root, dirs, files in os.walk(repo_copy):
        if ".git" in dirs:
            dirs.remove(".git")
        for f in files:
            if is_verdict_leak_file(f):
                try:
                    os.remove(os.path.join(root, f))
                except OSError as rm_err:
                    _ = rm_err

    assert_no_verdict_leaks(repo_copy)
    return repo_copy


def execute_engine_process(
    cmd: List[str], repo_copy: str, env: Dict[str, str], fout_path: str, ferr_path: str, engine_name: str, timeout: int = 1800,
) -> None:
    """Execute review engine process with timeout and process group termination."""
    with open(fout_path, "w", encoding="utf-8") as fout, open(ferr_path, "w", encoding="utf-8") as ferr:
        try:
            process = subprocess.Popen(
                cmd, stdout=fout, stderr=ferr, stdin=subprocess.DEVNULL, start_new_session=True, cwd=repo_copy, env=env,
            )
        except OSError as e:
            print(f"Fatal: {engine_name} launch failed: {sanitize_diagnostics(str(e))}", file=sys.stderr)
            sys.exit(2)

        try:
            process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            for sig, grace in ((signal.SIGTERM, 5), (signal.SIGKILL, None)):
                try:
                    os.killpg(process.pid, sig)
                except (ProcessLookupError, PermissionError) as err:
                    print(f"Debug: process already exited or permission denied: {err}", file=sys.stderr)
                try:
                    process.communicate(timeout=grace)
                except (subprocess.TimeoutExpired, OSError, ValueError) as err:
                    print(f"Debug: process communicate timed out or failed: {err}", file=sys.stderr)
                if process.poll() is not None:
                    break
            print(f"Fatal: {engine_name} launch timed out", file=sys.stderr)
            if os.path.isfile(ferr_path):
                with open(ferr_path, "r", encoding="utf-8") as err_f:
                    print(sanitize_diagnostics(err_f.read()), file=sys.stderr)
            sys.exit(2)
        except BaseException as e:
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError) as err:
                    print(f"Warning: process kill failed: {err}", file=sys.stderr)
            try:
                process.communicate()
            except (OSError, ValueError, subprocess.SubprocessError) as comm_err:
                print(f"Warning: error during process communicate on cleanup: {comm_err}", file=sys.stderr)
            raise e

    if process.returncode != 0:
        print(f"Fatal: {engine_name} command failed with code {process.returncode}", file=sys.stderr)
        if os.path.isfile(ferr_path):
            with open(ferr_path, "r", encoding="utf-8") as err_f:
                print(sanitize_diagnostics(err_f.read()), file=sys.stderr)
        sys.exit(2)


def _write_output_file(output_file: str, review: Dict[str, Any]) -> None:
    out_path = os.path.abspath(output_file)
    out_dir = os.path.dirname(out_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    temp_fd, temp_path = tempfile.mkstemp(dir=out_dir if out_dir else ".", prefix="review_out_", suffix=".tmp")
    try:
        os.fchmod(temp_fd, stat.S_IRUSR | stat.S_IWUSR)
        with open(temp_fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(review, indent=2) + "\n")
        os.replace(temp_path, out_path)
    except Exception as e:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError as cleanup_err:
                print(f"Warning: Failed to clean up temp file {temp_path}: {cleanup_err}", file=sys.stderr)
        print(f"Fatal: Failed writing to output file {output_file}: {e}", file=sys.stderr)
        sys.exit(2)


def register_audit_parser(parser: Optional[argparse.ArgumentParser] = None) -> argparse.ArgumentParser:
    if parser is None:
        parser = argparse.ArgumentParser(description="Multi-engine autonomous peer reviewer")
    parser.add_argument("--target", required=True, help="Absolute path to target file")
    parser.add_argument("--mode", required=True, choices=["design", "code", "spec"])
    parser.add_argument("--repo", required=True, help="Absolute path to repo")
    parser.add_argument("--spec", help="Absolute path to spec file (required for design unless --no-spec)")
    parser.add_argument("--no-spec", action="store_true", help="Explicitly indicate no spec is provided")
    parser.add_argument("--engine", help="Review engine to execute (workbuddy, codex, argon, etc.)")
    parser.add_argument("--model", help="Engine-specific model override")
    parser.add_argument("--session-id", help="Session ID for stateful review threads")
    parser.add_argument("--output-file", help="File to write raw review output")
    parser.add_argument("--message", help="Instruction message to prepend to prompt")
    parser.add_argument("--diagnostic-context", help="Path to diagnostic context file")
    parser.add_argument("--prior-review", help="Optional path to prior review JSON")
    parser.add_argument("--dimension", choices=["all", "inv", "dom"], default="all", help="Focus dimension")
    return parser


def run_audit(args: Any, *, dimension: Optional[str] = None) -> int:
    effective_dimension = dimension or getattr(args, "dimension", "all")

    if args.spec and args.no_spec:
        print("Fatal: --spec and --no-spec are mutually exclusive.", file=sys.stderr)
        sys.exit(2)

    if args.mode == "design":
        if not args.spec and not args.no_spec:
            print("Fatal: --mode design requires either --spec <path> or --no-spec.", file=sys.stderr)
            sys.exit(2)
    elif args.mode in ("spec", "code"):
        if args.spec:
            print(f"Fatal: --spec cannot be used with --mode {args.mode}.", file=sys.stderr)
            sys.exit(2)
        if args.no_spec:
            print(f"Fatal: --no-spec cannot be used with --mode {args.mode}.", file=sys.stderr)
            sys.exit(2)

    diagnostic_text = load_diagnostic_text(args.diagnostic_context, args.mode)
    target = os.path.realpath(args.target)
    if not os.path.isfile(target):
        print(f"Fatal: target is not a file: {target}", file=sys.stderr)
        sys.exit(2)

    repo = os.path.realpath(args.repo)
    if not os.path.isdir(repo):
        print(f"Fatal: repo is not a directory: {repo}", file=sys.stderr)
        sys.exit(2)

    spec_path = os.path.realpath(args.spec) if args.spec else None
    if spec_path and not os.path.isfile(spec_path):
        print(f"Fatal: spec file does not exist: {args.spec}", file=sys.stderr)
        sys.exit(2)

    engine_name = resolve_engine(args.engine, args.session_id)
    try:
        adapter = get_engine_adapter(engine_name)
    except ValueError as e:
        print(f"Fatal: {e}", file=sys.stderr)
        sys.exit(2)

    try:
        launcher_cmd = adapter.resolve_binary()
    except FileNotFoundError as e:
        if engine_name == "workbuddy" and not args.engine and not os.environ.get("AI_REVIEW_ENGINE"):
            if shutil.which("codex"):
                print("Notice: Default engine 'workbuddy' not found on system. Pass '--engine codex' or install WorkBuddy AI.", file=sys.stderr)
        print(f"Fatal: {e}", file=sys.stderr)
        sys.exit(2)

    with open(target, "r", encoding="utf-8", errors="replace") as f:
        target_content = f.read()

    spec_content = ""
    if spec_path:
        with open(spec_path, "r", encoding="utf-8", errors="replace") as f:
            spec_content = f.read()

    prior_review_text = load_prior_review_text(repo, getattr(args, "prior_review", None))

    if args.output_file and not os.path.isabs(args.output_file):
        real_repo, real_output = os.path.realpath(repo), os.path.realpath(os.path.join(repo, args.output_file))
        if not (real_output.startswith(real_repo + os.sep) or real_output == real_repo):
            print(f"Fatal: --output-file path escapes repository root: {args.output_file}", file=sys.stderr)
            sys.exit(2)

    diag_len = len(diagnostic_text) if diagnostic_text else 0
    adr_budget = max(0, 500_000 - diag_len)
    adr_content = build_adr_context(repo, target_content, spec_content, max_chars=adr_budget)

    with tempfile.TemporaryDirectory() as work_dir:
        try:
            os.chmod(work_dir, stat.S_IRWXU)
        except OSError as exc:
            print(f"Warning: Failed to set permissions on {work_dir}: {exc}", file=sys.stderr)

        review_file, schema_path = os.path.join(work_dir, "review.json"), os.path.join(work_dir, "schema.json")
        target_copy = os.path.join(work_dir, "target.file")
        shutil.copy(target, target_copy)

        spec_copy = os.path.join(work_dir, "spec.file") if spec_path else None
        if spec_path and spec_copy:
            shutil.copy(spec_path, spec_copy)

        repo_copy = prepare_repo_sandbox(repo, work_dir)
        with open(schema_path, "w", encoding="utf-8") as f:
            json.dump(SCHEMA, f)

        prompt_text = build_review_prompt(
            mode=args.mode, target_copy=target_copy, target_path=target, target_content=target_content,
            spec_path=spec_path, spec_content=spec_content, spec_copy=spec_copy, adr_content=adr_content,
            prior_review_text=prior_review_text, diagnostic_text=diagnostic_text, message=args.message,
            has_spec=bool(args.spec), dimension=effective_dimension,
        )

        fout_path, ferr_path = os.path.join(work_dir, "stdout.log"), os.path.join(work_dir, "stderr.log")
        cmd = adapter.build_command(
            launcher_cmd=launcher_cmd, repo_path=repo_copy, schema_path=schema_path,
            review_file_path=review_file, prompt_text=prompt_text, session_id=args.session_id, model=args.model,
        )

        execute_engine_process(
            cmd=cmd, repo_copy=repo_copy, env=adapter.get_execution_environment(),
            fout_path=fout_path, ferr_path=ferr_path, engine_name=engine_name, timeout=1800,
        )

        review, formatted_session = adapter.extract_review_payload_and_session(
            stdout_path=fout_path, stderr_path=ferr_path, review_file_path=review_file, prior_session_id=args.session_id,
        )

        if not isinstance(review, dict) or "issues" not in review or not isinstance(review["issues"], list):
            print("Fatal: Invalid review.json format.", file=sys.stderr)
            sys.exit(2)

        cleaned_issues = []
        for item in review["issues"]:
            if not isinstance(item, dict):
                print("Fatal: Invalid review.json format, issue item properties.", file=sys.stderr)
                sys.exit(2)
            desc = extract_issue_description(item)
            if not desc:
                for alt_key in (
                    "details", "message", "summary", "finding", "title", "comment",
                    "text", "note", "explanation", "problem", "issue", "reason", "defect", "desc"
                ):
                    if alt_key in item and isinstance(item[alt_key], (dict, list)):
                        desc = json.dumps(item[alt_key])
                        break
            if not desc or "severity" not in item or item["severity"] not in ("P0", "P1", "P2"):
                print(f"Fatal: Invalid review.json format, severity: {item}", file=sys.stderr)
                sys.exit(2)

            extra_ctx = []
            if "file" in item and isinstance(item["file"], str) and item["file"] not in desc:
                extra_ctx.append(f"file: {item['file']}")
            if "line" in item and item["line"] and str(item["line"]) not in desc:
                extra_ctx.append(f"line: {item['line']}")
            if extra_ctx:
                desc = f"[{', '.join(extra_ctx)}] {desc}"

            cleaned_issues.append({"severity": item["severity"], "description": desc})

        review = format_review_envelope(engine_name, formatted_session, cleaned_issues)
        print(json.dumps(review))

        if args.output_file:
            _write_output_file(args.output_file, review)

        blocking_issues = [i for i in review["issues"] if i.get("severity") in ["P0", "P1"]]
        return 0 if not blocking_issues else 1


def _main(argv=None):
    parser = register_audit_parser()
    args = parser.parse_args(argv[1:] if argv is not None else None)
    code = run_audit(args, dimension=getattr(args, "dimension", "all"))
    sys.exit(code)


def main(argv=None):
    try:
        _main(argv)
    except (OSError, subprocess.CalledProcessError) as e:
        print(f"Fatal: I/O or process error: {sanitize_diagnostics(str(e))}", file=sys.stderr)
        sys.exit(2)
