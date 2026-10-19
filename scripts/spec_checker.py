#!/usr/bin/env python3
"""Shared Specification Verification Engine (REQ-032).

Validates that an active feature specification exists in docs/specs/INDEX.md
and complies with the 5-Document Architecture standard.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from semantic_checker import (
        compute_spec_package_hash,
        validate_semantic_traceability,
    )
except ImportError:
    from scripts.semantic_checker import (
        compute_spec_package_hash,
        validate_semantic_traceability,
    )

REQ_PATTERN = re.compile(r"\b(REQ-\d+|FLOW-\d+|ALIGN-\d+)\b")
PLACEHOLDER_REQS = {"REQ-XXX", "REQ-xxx"}
ADR_PATTERN = re.compile(r"\bADR-\d+\b")

PLANNING_STATUSES = {"draft", "planning", "review"}
EXECUTION_STATUSES = {"approved", "in-progress", "active"}
VERIFIABLE_TERMINAL_STATUSES = {"completed", "implemented", "done"}
TERMINAL_STATUSES = VERIFIABLE_TERMINAL_STATUSES | {"abandoned", "superseded"}
ACTIVE_STATUSES = EXECUTION_STATUSES | PLANNING_STATUSES

DECLARED_REQ_LINE_PATTERN = re.compile(
    r"^(?:\s*#{1,6}\s+.*?|\s*[-*+]\s+(?:\*\*|`)*|\s*\|\s*`?)\b(REQ-\d+|FLOW-\d+|ALIGN-\d+)\b",
    re.MULTILINE,
)


def normalize_status(raw: str) -> str:
    """Normalize status string to lowercase hyphenated format."""
    return raw.strip().lower().replace(" ", "-").replace("_", "-")


def extract_requirement_ids(text: str) -> List[str]:
    """Extract sorted, unique requirement IDs, excluding placeholders."""
    matches = set(REQ_PATTERN.findall(text))
    filtered = {m for m in matches if m not in PLACEHOLDER_REQS}
    return sorted(list(filtered))


def extract_declared_requirement_ids(spec_text: str) -> List[str]:
    """Extract declared requirement IDs from headings, bullet lead-ins, or table cells.

    Ignores historical or contextual mentions in prose paragraphs, falling back to
    extract_requirement_ids(spec_text) only if no structured declarations exist.
    """
    matches = set(DECLARED_REQ_LINE_PATTERN.findall(spec_text))
    filtered = {m for m in matches if m not in PLACEHOLDER_REQS}
    if filtered:
        return sorted(list(filtered))
    return extract_requirement_ids(spec_text)


def parse_specs_index_text(content: str) -> List[Dict[str, str]]:
    """Parse markdown table rows in docs/specs/INDEX.md content into structured dicts.

    Keys returned: feature_id, title, status, req_range, key_decisions, spec_path.
    Handles escaped pipes (\\|) inside table cells safely. Raises ValueError on malformed rows.
    """
    records: List[Dict[str, str]] = []

    for line_idx, line in enumerate(content.splitlines(), start=1):
        trimmed = line.strip()
        if not trimmed.startswith("|") or not trimmed.endswith("|"):
            continue

        raw_parts = re.split(r"(?<!\\)\|", trimmed[1:-1])
        parts = [p.replace(r"\|", "|").strip() for p in raw_parts]

        col0 = parts[0].strip("` ") if parts else ""
        if col0.lower() == "feature id" or re.match(r"^:?-+:?$", col0):
            continue

        if len(parts) != 6:
            raise ValueError(
                f"Malformed table row at line {line_idx} (expected 6 columns, got {len(parts)}): {line}"
            )

        feature_id = col0
        title = parts[1].strip()
        status = parts[2].strip("` ")
        req_range = parts[3].strip("` ")
        key_decisions = parts[4].strip()
        raw_spec_path = parts[5].strip()

        # Extract URL or relative path if formatted as [label](path)
        link_match = re.search(r"\[.*?\]\((.*?)\)", raw_spec_path)
        if link_match:
            spec_path = link_match.group(1).strip()
        else:
            spec_path = raw_spec_path.strip("` ")

        records.append({
            "feature_id": feature_id,
            "title": title,
            "status": status,
            "req_range": req_range,
            "key_decisions": key_decisions,
            "spec_path": spec_path,
        })

    return records


def parse_specs_index(index_path: Union[Path, str]) -> List[Dict[str, str]]:
    """Parse markdown table rows in docs/specs/INDEX.md into structured dicts."""
    path = Path(index_path)
    if not path.exists():
        raise FileNotFoundError(f"Index file not found: {path}")
    return parse_specs_index_text(path.read_text(encoding="utf-8"))


def get_active_specifications(records: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Filter records for active status (case-insensitive in ACTIVE_STATUSES)."""
    return [r for r in records if normalize_status(r.get("status", "")) in ACTIVE_STATUSES]


def validate_spec_package(
    package_dir: Union[Path, str],
    verify_evidence: bool = False,
    require_semantic: bool = False,
    run_semantic_agent: bool = False,
) -> Tuple[bool, str]:
    """Check that spec.md, decisions.md, design.md, and tasks.md exist and contain non-whitespace text.

    If verify_evidence is True, verification.md is also required and must be non-empty.
    Verifies that every requirement ID declared in spec.md is referenced in design.md
    and tasks.md (and verification.md if verify_evidence=True), and that decisions.md
    contains at least one ADR-\\d+ or declared requirement ID.
    """
    pkg = Path(package_dir)
    if not pkg.exists() or not pkg.is_dir():
        return False, f"Package directory not found: {pkg}"

    contents: Dict[str, str] = {}
    for req_file in ["spec.md", "decisions.md", "design.md"]:
        target = pkg / req_file
        if not target.is_file():
            return False, f"Missing required specification file: {req_file}"
        content = target.read_text(encoding="utf-8")
        if not content.strip():
            return False, f"Specification file is empty: {req_file}"
        contents[req_file] = content

    spec_reqs = extract_declared_requirement_ids(contents["spec.md"])
    if not spec_reqs:
        return False, "spec.md does not contain any valid requirement pattern (REQ-\\d+, FLOW-\\d+, ALIGN-\\d+)"

    for req_file in (["tasks.md", "verification.md"] if verify_evidence else ["tasks.md"]):
        target = pkg / req_file
        if not target.is_file():
            return False, f"Missing required specification file: {req_file}"
        content = target.read_text(encoding="utf-8")
        if not content.strip():
            return False, f"Specification file is empty: {req_file}"
        contents[req_file] = content

    trace_docs = ["design.md", "tasks.md"]
    if verify_evidence:
        trace_docs.append("verification.md")

    for doc in trace_docs:
        doc_content = contents[doc]
        doc_reqs = set(extract_requirement_ids(doc_content))
        missing = [r for r in spec_reqs if r not in doc_reqs]
        if missing:
            return False, f"{doc} is missing requirement IDs declared in spec.md: {', '.join(missing)}"

    decisions_content = contents["decisions.md"]
    has_adr = bool(ADR_PATTERN.search(decisions_content))
    decisions_reqs = set(extract_requirement_ids(decisions_content))
    has_spec_req = any(r in decisions_reqs for r in spec_reqs)
    if not has_adr and not has_spec_req:
        return False, "decisions.md must contain at least one ADR-\\d+ or declared requirement ID"

    if require_semantic or run_semantic_agent or (pkg / "traceability_audit.json").is_file():
        sem_ok, sem_err = validate_semantic_traceability(
            pkg,
            spec_reqs=spec_reqs,
            verify_evidence=verify_evidence,
            run_agent=run_semantic_agent,
        )
        if not sem_ok:
            return False, sem_err

    return True, ""


def resolve_package_dir(
    spec: Dict[str, str],
    root: Union[Path, str],
    specs_dir: Optional[Union[Path, str]] = None,
) -> Tuple[Optional[Path], Optional[str]]:
    """Resolve candidate specification package directory and check path containment.

    Returns (pkg_dir, None) on success,
    (None, "invalid_path:...") on traversal or outside-root violation,
    or (None, "missing_dir:...") if no candidate directory exists.
    """
    root_path = Path(root).resolve()
    s_dir = Path(specs_dir).resolve() if specs_dir is not None else (root_path / "docs" / "specs")
    feat_id = spec.get("feature_id", "")
    spec_path_str = spec.get("spec_path", "")

    if ".." in feat_id or "/" in feat_id or "\\" in feat_id:
        return None, f"invalid_path:Feature ID '{feat_id}' contains invalid path characters"

    candidates: List[Path] = [s_dir / feat_id] if feat_id else []
    if spec_path_str:
        try:
            p1 = (s_dir / spec_path_str).resolve()
            p2 = (root_path / spec_path_str).resolve()
            if not p1.is_relative_to(root_path) or not p2.is_relative_to(root_path):
                return None, f"invalid_path:Specification candidate path for feature '{feat_id}' escapes workspace root"
        except (ValueError, RuntimeError):
            return None, f"invalid_path:Specification candidate path for feature '{feat_id}' escapes workspace root"

        candidates.extend([p.parent if p.is_file() else p for p in (p1, p2) if p.is_file() or p.is_dir()])

    for cand in candidates:
        try:
            if not cand.resolve().is_relative_to(root_path):
                return None, f"invalid_path:Specification candidate path for feature '{feat_id}' escapes workspace root"
        except (ValueError, RuntimeError):
            return None, f"invalid_path:Specification candidate path for feature '{feat_id}' escapes workspace root"

    for cand in candidates:
        if cand.is_dir():
            return cand, None

    return None, f"missing_dir:Package directory for feature '{feat_id}' not found"


def verify_active_specification(
    workspace_root: Union[Path, str],
    require_approved: bool = True,
    feature_id: Optional[str] = None,
    verify_evidence: bool = False,
    require_semantic: bool = False,
    run_semantic_agent: bool = False,
) -> Dict[str, Any]:
    """Verify that an active and complete specification package exists in workspace.

    Returns a dict with 'status', 'valid', and additional diagnostic details.
    """
    if feature_id is not None:
        if ".." in feature_id or "/" in feature_id or "\\" in feature_id:
            return {
                "status": "invalid_path",
                "valid": False,
                "reason": f"Feature ID '{feature_id}' contains invalid path characters",
            }

    root = Path(workspace_root).resolve()
    specs_dir = root / "docs" / "specs"

    if not specs_dir.exists() or not specs_dir.is_dir():
        return {"status": "no_spec_framework", "valid": True, "reason": "No docs/specs directory in workspace"}

    index_path = specs_dir / "INDEX.md"
    if not index_path.is_file():
        return {"status": "invalid", "valid": False, "reason": "Missing docs/specs/INDEX.md"}

    try:
        records = parse_specs_index(index_path)
    except Exception as exc:
        return {"status": "corrupt_index", "valid": False, "reason": f"Failed to parse docs/specs/INDEX.md: {exc}"}

    if feature_id is not None:
        records = [r for r in records if r.get("feature_id") == feature_id]
        if not records:
            return {"status": "feature_not_found", "valid": False, "reason": f"Feature '{feature_id}' not found in docs/specs/INDEX.md"}

    exec_specs = [r for r in records if normalize_status(r.get("status", "")) in EXECUTION_STATUSES]
    plan_specs = [r for r in records if normalize_status(r.get("status", "")) in PLANNING_STATUSES]
    verifiable_term_specs = [
        r for r in records if normalize_status(r.get("status", "")) in VERIFIABLE_TERMINAL_STATUSES
    ]

    target_specs = exec_specs + plan_specs
    if verify_evidence or (feature_id is not None and not target_specs):
        target_specs += verifiable_term_specs

    if not target_specs:
        return {"status": "no_active_spec", "valid": False, "reason": "No active specification found in docs/specs/INDEX.md"}

    valid_exec_features: List[str] = []
    valid_plan_features: List[str] = []
    exec_errors: List[Dict[str, Any]] = []
    plan_errors: List[Dict[str, Any]] = []

    for spec in target_specs:
        feat_id = spec.get("feature_id", "")
        norm_status = normalize_status(spec.get("status", ""))
        effective_verify_evidence = verify_evidence or (norm_status in VERIFIABLE_TERMINAL_STATUSES)
        is_exec = norm_status in EXECUTION_STATUSES or (
            norm_status in VERIFIABLE_TERMINAL_STATUSES and (feature_id is not None or verify_evidence)
        )

        pkg_dir, resolve_err = resolve_package_dir(spec, root, specs_dir)
        if resolve_err:
            if resolve_err.startswith("invalid_path:"):
                return {"status": "invalid_path", "valid": False, "feature_id": feat_id, "reason": resolve_err.split(":", 1)[1]}
            err_dict = {"status": "incomplete_package", "valid": False, "feature_id": feat_id, "reason": resolve_err.split(":", 1)[1]}
            (exec_errors if is_exec else plan_errors).append(err_dict)
            continue

        is_valid, err = validate_spec_package(
            pkg_dir,
            verify_evidence=effective_verify_evidence,
            require_semantic=require_semantic,
            run_semantic_agent=run_semantic_agent,
        )
        if not is_valid:
            err_dict = {"status": "incomplete_package", "valid": False, "feature_id": feat_id, "reason": err}
            (exec_errors if is_exec else plan_errors).append(err_dict)
            continue

        (valid_exec_features if is_exec else valid_plan_features).append(feat_id)

    if require_approved:
        if exec_errors:
            return exec_errors[0]
        if valid_exec_features:
            res: Dict[str, Any] = {"status": "valid", "valid": True, "active_features": valid_exec_features}
            if plan_errors:
                res["warnings"] = plan_errors
            return res
        if plan_errors:
            return plan_errors[0]
        if valid_plan_features:
            return {
                "status": "unapproved_spec",
                "valid": False,
                "reason": "Specification exists in planning/draft status but is not yet approved (status must be Approved, In-Progress, or Active).",
            }
        return {"status": "no_active_spec", "valid": False, "reason": "No active specification found in docs/specs/INDEX.md"}

    all_valid = valid_exec_features + valid_plan_features
    all_errors = exec_errors + plan_errors
    if all_valid:
        res = {"status": "valid", "valid": True, "active_features": all_valid}
        if all_errors:
            res["warnings"] = all_errors
        return res
    if all_errors:
        return all_errors[0]
    return {"status": "no_active_spec", "valid": False, "reason": "No active specification found in docs/specs/INDEX.md"}


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint for spec verification engine."""
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="Shared Specification Verification Engine (REQ-032)"
    )
    parser.add_argument(
        "--workspace",
        default=os.getcwd(),
        help="Workspace root directory to verify (default: current working directory)",
    )
    parser.add_argument("--json", action="store_true", help="Emit structured verification report as JSON")
    parser.add_argument("--quiet", action="store_true", help="Suppress textual diagnostic messages")
    parser.add_argument("--feature", default=None, help="Validate a specific feature ID")
    parser.add_argument("--allow-planning", action="store_true", help="Permit planning-status specifications")
    parser.add_argument("--verify-evidence", action="store_true", help="Verify verification.md requirement ID coverage")
    parser.add_argument("--semantic", action="store_true", help="Enforce semantic traceability verification")
    args = parser.parse_args(argv)

    try:
        result = verify_active_specification(
            workspace_root=Path(args.workspace),
            require_approved=not args.allow_planning,
            feature_id=args.feature,
            verify_evidence=args.verify_evidence,
            require_semantic=args.semantic,
            run_semantic_agent=args.semantic,
        )
    except Exception as exc:
        if args.json:
            print(json.dumps({"status": "error", "valid": False, "reason": str(exc)}))
        elif not args.quiet:
            print(f"Error during specification verification: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result))
    elif not args.quiet:
        if result.get("valid"):
            print(f"Specification verification passed: status={result.get('status')}")
            if "active_features" in result:
                print(f"Active features: {', '.join(result['active_features'])}")
            if "warnings" in result:
                print(f"Warnings: {result['warnings']}")
        else:
            print(f"Specification verification failed: {result.get('reason')}", file=sys.stderr)

    if result.get("valid"):
        return 0
    elif result.get("status") in ("corrupt_index", "error"):
        return 2
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
