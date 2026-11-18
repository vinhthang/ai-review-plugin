#!/usr/bin/env python3
"""Semantic Traceability Verification Engine (REQ-016).

Validates that an Opus/high-reasoning model has semantically audited the 5-document
specification package and produced a valid, content-hashed traceability_audit.json receipt.
"""

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


def compute_spec_package_hash(
    package_dir: Union[Path, str],
    include_verification: bool = False,
) -> str:
    """Compute deterministic SHA-256 hex digest over specification package files."""
    pkg = Path(package_dir)
    files = ["spec.md", "decisions.md", "design.md", "tasks.md"]
    if include_verification:
        files.append("verification.md")

    hasher = hashlib.sha256()
    for fname in files:
        target = pkg / fname
        if target.is_file():
            text = target.read_text(encoding="utf-8")
        else:
            text = ""
        norm_text = text.replace("\r\n", "\n").strip()
        hasher.update(f"{fname}\n{norm_text}\n".encode("utf-8"))

    return hasher.hexdigest()


def run_cli_semantic_audit(
    package_dir: Path,
    spec_reqs: List[str],
    verify_evidence: bool = False,
) -> Tuple[bool, str]:
    """Execute external CLI agent to audit semantic traceability and write receipt."""
    model = os.environ.get("SPEC_CHECKER_AGENT_MODEL", "claude-opus-4-6").strip()
    if not model or "flash" in model.lower():
        return False, f"Semantic traceability audit model cannot be flash: '{model}'"

    custom_cmd = os.environ.get("SPEC_CHECKER_AGENT_CMD")
    prompt = (
        f"Audit specification package in {package_dir} for requirements {spec_reqs} "
        f"(verify_evidence={verify_evidence}). Write {package_dir / 'traceability_audit.json'} "
        f"with auditor_model='{model}', verdict='PASS'/'FAIL', and evaluated requirements."
    )

    try:
        if custom_cmd and custom_cmd.strip():
            res = subprocess.run(
                custom_cmd.strip(),
                shell=True,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(package_dir),
            )
        else:
            cli = shutil.which("cbc") or shutil.which("codebuddy")
            if not cli:
                return False, "No CLI agent found (set SPEC_CHECKER_AGENT_CMD or install cbc/codebuddy)"
            cmd = [cli, "-p", prompt, "--model", model, "--output-format", "json"]
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(package_dir),
            )

        if res.returncode != 0:
            err = res.stderr.strip() or res.stdout.strip()
            return False, f"CLI agent failed with exit code {res.returncode}: {err}"

        audit_path = package_dir / "traceability_audit.json"
        if not audit_path.is_file():
            return False, f"CLI agent did not generate {audit_path.name}"
        return True, ""
    except Exception as exc:
        return False, f"CLI agent execution error: {exc}"


def validate_semantic_traceability(
    package_dir: Union[Path, str],
    spec_reqs: Optional[List[str]] = None,
    verify_evidence: bool = False,
    run_agent: bool = False,
) -> Tuple[bool, str]:
    """Validate semantic traceability receipt for a specification package."""
    pkg = Path(package_dir)
    audit_path = pkg / "traceability_audit.json"

    if run_agent and not audit_path.is_file():
        ok, err = run_cli_semantic_audit(pkg, spec_reqs or [], verify_evidence)
        if not ok:
            return False, err

    if not audit_path.is_file():
        return False, f"Missing semantic traceability audit receipt: {audit_path.name}"

    try:
        data = json.loads(audit_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, f"Invalid JSON in {audit_path.name}: {exc}"

    if not isinstance(data, dict):
        return False, f"{audit_path.name} must be a JSON object"

    auditor_model = str(data.get("auditor_model") or "").strip()
    if not auditor_model or "flash" in auditor_model.lower():
        return (
            False,
            f"Semantic traceability audit must use an Opus/high-reasoning model, not flash (got '{auditor_model}')",
        )

    if str(data.get("verdict") or "").strip().upper() != "PASS":
        return False, f"Semantic traceability audit verdict is '{data.get('verdict')}' (expected 'PASS')"

    expected_spec_hash = compute_spec_package_hash(pkg, include_verification=False)
    if data.get("spec_hash") != expected_spec_hash:
        return False, "Stale traceability_audit.json: spec_hash does not match current spec files"

    if verify_evidence:
        expected_ev_hash = compute_spec_package_hash(pkg, include_verification=True)
        if data.get("evidence_hash") != expected_ev_hash:
            return False, "Stale traceability_audit.json: evidence_hash does not match verification.md"

    if spec_reqs is None:
        spec_file = pkg / "spec.md"
        if not spec_file.is_file():
            return False, "Missing required specification file: spec.md"
        from spec_checker import extract_declared_requirement_ids

        spec_reqs = extract_declared_requirement_ids(spec_file.read_text(encoding="utf-8"))

    reqs_eval = data.get("requirements_evaluated")
    if not isinstance(reqs_eval, dict):
        return False, f"Missing or invalid 'requirements_evaluated' object in {audit_path.name}"

    for req_id in spec_reqs:
        entry = reqs_eval.get(req_id)
        if not isinstance(entry, dict):
            return (
                False,
                f"Requirement '{req_id}' failed semantic traceability verification in traceability_audit.json",
            )
        if entry.get("design_aligned") is not True or not str(entry.get("design_rationale") or "").strip():
            return (
                False,
                f"Requirement '{req_id}' failed semantic traceability verification in traceability_audit.json",
            )
        if entry.get("tasks_actionable") is not True or not str(entry.get("tasks_rationale") or "").strip():
            return (
                False,
                f"Requirement '{req_id}' failed semantic traceability verification in traceability_audit.json",
            )
        if entry.get("decisions_consistent") is not True:
            return (
                False,
                f"Requirement '{req_id}' failed semantic traceability verification in traceability_audit.json",
            )
        if verify_evidence:
            if (
                entry.get("evidence_verified") is not True
                or not str(entry.get("evidence_rationale") or "").strip()
            ):
                return (
                    False,
                    f"Requirement '{req_id}' failed semantic traceability verification in traceability_audit.json",
                )

    return True, ""
