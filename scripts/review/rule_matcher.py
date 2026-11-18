#!/usr/bin/env python3
"""Rule matcher and language-specific checklist resolver (REQ-048, REQ-049).

Ports glob matching, brace expansion, Objective-C/MATLAB sniffing, and rule
deduplication from alibaba/open-code-review into pure Python standard library.
"""

import json
import logging
import os
import re
import sys
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

OBJC_SNIFF_PREFIXES: Tuple[str, ...] = (
    "#import",
    "#include",
    "#pragma",
    "#if",
    "#define",
    "@import",
    "@interface",
    "@implementation",
    "@class",
    "@protocol",
    "//",
    "/*",
)

_REGEX_CACHE: Dict[str, re.Pattern] = {}


def extract_diff_paths(target_content: str, target_path: Optional[str] = None) -> List[str]:
    """Extract modified file paths from unified diff text or fallback target path.

    Scans for unified diff headers ('+++ b/<path>' and 'diff --git a/... b/<path>'),
    filtering out '/dev/null' or 'dev/null', stripping quotes and leading prefixes,
    and preserving first-seen order without duplicates.
    """
    paths: List[str] = []
    seen: Set[str] = set()

    def add_path(p: str) -> None:
        p = p.split("\t", 1)[0].strip().strip("'\"").replace("\\", "/")
        if not p:
            return
        if p.startswith("b/"):
            p = p[2:]
        elif p.startswith("a/"):
            p = p[2:]
        # Skip dev/null entries (deletions / creations)
        if p in ("/dev/null", "dev/null", "b/dev/null", "a/dev/null"):
            return
        if p.startswith("./"):
            p = p[2:]
        if p and p not in seen:
            seen.add(p)
            paths.append(p)

    for raw_line in target_content.splitlines():
        # Check diff --git a/... b/... (raw line must start with exact prefix, no strip)
        if raw_line.startswith("diff --git "):
            line_str = raw_line.rstrip("\r\n")
            m = re.match(r'^diff\s+--git\s+(?:"?a/.*?"?|/dev/null)\s+(?:"?b/(.*?)"?|/dev/null|b/dev/null)$', line_str)
            if m and m.group(1):
                add_path(m.group(1))
            else:
                parts = line_str.split()
                if len(parts) >= 4:
                    b_part = parts[-1].strip("'\"")
                    add_path(b_part)
            continue

        # Check +++ b/... (must start with +++ b/ or +++ /dev/null, raw column 1)
        if raw_line.startswith("+++ b/") or raw_line.startswith("+++ /dev/null"):
            line_str = raw_line.rstrip("\r\n")
            m = re.match(r'^\+\+\+\s+(?:"?b/(.*?)"?|/dev/null|b/dev/null)', line_str)
            if m and m.group(1):
                add_path(m.group(1))
            else:
                parts = line_str.split(maxsplit=1)
                if len(parts) == 2:
                    add_path(parts[1])
            continue

        # Check --- a/... (raw column 1)
        if raw_line.startswith("--- a/") or raw_line.startswith("--- /dev/null"):
            line_str = raw_line.rstrip("\r\n")
            m = re.match(r'^---\s+(?:"?a/(.*?)"?|/dev/null|a/dev/null)', line_str)
            if m and m.group(1):
                add_path(m.group(1))
            continue

    # Fallback to single target_path if diff produced no paths
    if not paths and target_path:
        base = os.path.basename(target_path)
        if base != "target.file" and not base.startswith("review_"):
            add_path(target_path)

    return paths


def expand_braces(pattern: str) -> List[str]:
    """Recursively expand {a,b,c} brace alternatives in glob pattern with depth awareness."""
    start = pattern.find("{")
    if start == -1:
        return [pattern]

    depth = 0
    end = -1
    options: List[str] = []
    current_option: List[str] = []

    for i in range(start, len(pattern)):
        char = pattern[i]
        if char == "{":
            depth += 1
            if depth > 1:
                current_option.append(char)
        elif char == "}":
            depth -= 1
            if depth == 0:
                options.append("".join(current_option))
                end = i
                break
            else:
                current_option.append(char)
        elif char == "," and depth == 1:
            options.append("".join(current_option))
            current_option = []
        else:
            current_option.append(char)

    if end == -1 or depth != 0:
        return [pattern]

    prefix = pattern[:start]
    suffix = pattern[end + 1 :]

    expanded: List[str] = []
    for opt in options:
        expanded.extend(expand_braces(prefix + opt + suffix))
    return expanded


def _glob_to_regex(pattern: str) -> str:
    """Convert a doublestar glob pattern to an equivalent regular expression."""
    p = pattern.replace("\\", "/").strip().lower()
    if p.startswith("./"):
        p = p[2:]
    if p.startswith("/"):
        p = p[1:]

    if p == "**":
        return r"^.*$"

    leading_doublestar = False
    if p.startswith("**/"):
        leading_doublestar = True
        p = p[3:]

    trailing_doublestar = False
    if p.endswith("/**"):
        trailing_doublestar = True
        p = p[:-3]

    # Split internal /**/
    segments = p.split("/**/")
    regex_segments: List[str] = []
    for seg in segments:
        sub_parts = seg.split("*")
        escaped_sub: List[str] = []
        for part in sub_parts:
            q_parts = part.split("?")
            escaped_q = [re.escape(qp) for qp in q_parts]
            escaped_sub.append(r"[^/]".join(escaped_q))
        regex_segments.append(r"[^/]*".join(escaped_sub))

    core = r"(?:/|/.+/)" .join(regex_segments)
    prefix = r"(?:.+/)?" if leading_doublestar else ""
    suffix = r"(?:/.*)?" if trailing_doublestar else ""
    return f"^{prefix}{core}{suffix}$"


def match_doublestar(pattern: str, path: str) -> bool:
    """Match a normalized relative path against a glob pattern case-insensitively."""
    path_norm = path.replace("\\", "/").strip().lower()
    if path_norm.startswith("./"):
        path_norm = path_norm[2:]
    if path_norm.startswith("/"):
        path_norm = path_norm[1:]

    regex_str = _REGEX_CACHE.get(pattern)
    if regex_str is None:
        regex_str = _glob_to_regex(pattern)
        _REGEX_CACHE[pattern] = re.compile(regex_str)

    compiled = _REGEX_CACHE[pattern]
    return bool(compiled.match(path_norm))


def sniffs_as_objc(path: str, diff_text: str = "") -> bool:
    """Return True if a .m file sniffs as Objective-C rather than MATLAB.

    Examines the first non-blank content/added line in the diff (or file on disk),
    checking for Objective-C keywords (#import, #include, @interface, //, /*, etc.).
    """
    norm_path = path.replace("\\", "/").strip().lower()
    if not norm_path.endswith(".m"):
        return False

    lines: List[str] = []
    if diff_text:
        all_lines = diff_text.splitlines()
        has_diff_headers = any(l.startswith("diff --git ") for l in all_lines)
        section_lines: List[str] = []
        in_section = False
        target_norm = norm_path[2:] if norm_path.startswith("./") else norm_path

        for line in all_lines:
            if line.startswith("diff --git "):
                if in_section:
                    break
                parts = line.rstrip("\r\n").split()
                matched = False
                if len(parts) >= 4:
                    b_part = parts[-1].strip("'\"")
                    if b_part.startswith("b/"):
                        b_part = b_part[2:]
                    b_part = b_part.split("\t", 1)[0].replace("\\", "/").lower()
                    if b_part.startswith("./"):
                        b_part = b_part[2:]
                    if b_part == target_norm or b_part.endswith("/" + target_norm):
                        matched = True
                if matched:
                    in_section = True
                    section_lines = [line]
                continue

            if line.startswith("+++ b/"):
                p = line[6:].rstrip("\r\n").split("\t", 1)[0].strip("'\"").replace("\\", "/").lower()
                if p.startswith("./"):
                    p = p[2:]
                if p == target_norm or p.endswith("/" + target_norm):
                    in_section = True
                    section_lines = [line]
                continue

            if in_section:
                section_lines.append(line)

        if section_lines:
            lines = section_lines
        elif has_diff_headers:
            lines = []
        else:
            lines = all_lines

    for line in lines:
        l_strip = line.strip()
        if not l_strip:
            continue
        # Skip diff headers / hunk indicators
        if (
            l_strip.startswith("diff --git")
            or l_strip.startswith("index ")
            or l_strip.startswith("--- ")
            or l_strip.startswith("+++ ")
            or l_strip.startswith("@@ ")
            or l_strip.startswith("new file")
            or l_strip.startswith("deleted file")
            or l_strip.startswith("old mode")
            or l_strip.startswith("new mode")
            or l_strip.startswith("similarity index")
            or l_strip.startswith("rename ")
        ):
            continue

        # Content line: strip leading '+' or ' ' in diff hunks
        content = line
        if content.startswith(("+", " ")):
            content = content[1:]
        elif content.startswith("-"):
            # Skip deletions when sniffing added/current code
            continue

        content = content.strip()
        if not content:
            continue

        return any(content.startswith(p) for p in OBJC_SNIFF_PREFIXES)

    # Fallback: check file on disk if available
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for disk_line in f:
                    content = disk_line.strip()
                    if content:
                        return any(content.startswith(p) for p in OBJC_SNIFF_PREFIXES)
        except Exception as exc:
            logger.debug("Failed reading file %s for sniffing: %s", path, exc)

    return False


def _get_default_rules_dir() -> str:
    """Return default directory containing system_rules.json and rule_docs/."""
    return os.path.join(os.path.dirname(__file__), "rules")


def resolve_rules_for_paths(
    paths: List[str],
    diff_text: str = "",
    rules_dir: Optional[str] = None,
) -> List[Tuple[str, str]]:
    """Resolve and deduplicate rule documents for given file paths.

    Returns a list of (rule_filename, rule_text) tuples preserving first-seen order.
    """
    base_dir = rules_dir or _get_default_rules_dir()
    system_rules_path = os.path.join(base_dir, "system_rules.json")
    rule_docs_dir = os.path.join(base_dir, "rule_docs")

    if not os.path.isfile(system_rules_path):
        sys.stderr.write(f"Warning: system_rules.json not found at {system_rules_path}\n")
        return []

    try:
        with open(system_rules_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as exc:
        sys.stderr.write(f"Warning: Failed reading system_rules.json: {exc}\n")
        return []

    default_rule = config.get("default_rule", "default.md")
    path_rule_map: Dict[str, str] = config.get("path_rule_map", {})

    target_paths = paths if paths else ["default"]
    matched_rule_names: List[str] = []
    seen_rule_names: Set[str] = set()

    for path in target_paths:
        matched_rule = None
        # Disambiguate Objective-C vs MATLAB for .m files
        if sniffs_as_objc(path, diff_text):
            matched_rule = "objc.md"
        else:
            # Check ordered path_rule_map
            for pattern, rule_file in path_rule_map.items():
                expanded = expand_braces(pattern)
                if any(match_doublestar(exp, path) for exp in expanded):
                    matched_rule = rule_file
                    break

        if not matched_rule:
            matched_rule = default_rule

        if matched_rule not in seen_rule_names:
            seen_rule_names.add(matched_rule)
            matched_rule_names.append(matched_rule)

    resolved: List[Tuple[str, str]] = []
    for rule_name in matched_rule_names:
        rule_file_path = os.path.join(rule_docs_dir, rule_name)
        if not os.path.isfile(rule_file_path):
            sys.stderr.write(f"Warning: Rule doc not found: {rule_file_path}\n")
            continue
        try:
            with open(rule_file_path, "r", encoding="utf-8") as rf:
                content = rf.read()
            resolved.append((rule_name, content))
        except Exception as exc:
            sys.stderr.write(f"Warning: Failed reading rule doc {rule_file_path}: {exc}\n")

    return resolved


def build_language_rules_context(
    target_content: str,
    target_path: Optional[str] = None,
    max_chars: int = 60_000,
    rules_dir: Optional[str] = None,
) -> str:
    """Extract diff paths, resolve language rules, and build <language_review_rules> context."""
    paths = extract_diff_paths(target_content, target_path)
    rules = resolve_rules_for_paths(paths, diff_text=target_content, rules_dir=rules_dir)
    if not rules:
        return ""

    header = "<language_review_rules>\n"
    footer = "</language_review_rules>"
    available_chars = max_chars - len(header) - len(footer)
    if available_chars <= 0:
        return ""

    body_parts: List[str] = []
    current_len = 0
    for name, content in rules:
        part = f"--- Rule: {name} ---\n{content.strip()}\n"
        if current_len + len(part) <= available_chars:
            body_parts.append(part)
            current_len += len(part)
        else:
            remaining = available_chars - current_len
            if remaining > 50:
                body_parts.append(part[:remaining].rstrip() + "\n")
            break

    if not body_parts:
        return ""

    return header + "".join(body_parts) + footer
