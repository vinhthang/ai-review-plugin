#!/usr/bin/env python3
"""Automated Markdown Reviewer via Microsoft Edge CDP / AppleScript bridge.

Connects to an active gemini.google.com tab in Microsoft Edge, injects
the bundled review prompt, triggers generation, and captures the resulting
review into the specified output file.

Bridge modes:
- cdp: Direct WebSocket connection via Chrome DevTools Protocol (zero-focus background).
- applescript: Background AppleScript execution on Microsoft Edge tabs.
- auto: Tries CDP first if debug port is active, falls back to AppleScript.

Prerequisite in Microsoft Edge (for AppleScript fallback):
    Top menu -> View -> Developer -> Allow JavaScript from Apple Events (Enable once)
"""

import argparse
import base64
import json
import os
import socket
import struct
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from review.runners.cdp_client import CDPClient
except ImportError:
    try:
        from scripts.review.runners.cdp_client import CDPClient
    except ImportError:
        from .cdp_client import CDPClient

DEFAULT_SKILL = "@software-architect-reviewer"
DEFAULT_TIMEOUT = 240
DEFAULT_OUT = "design_review.md"
DEFAULT_CDP_PORT = int(os.environ.get("EDGE_DEBUG_PORT", 9222))


def run_edge_js(
    js_code: str,
    mode: str = "auto",
    port: int = DEFAULT_CDP_PORT,
    open_tab: bool = False,
) -> str:
    """Executes a JavaScript snippet directly on the Gemini tab in Microsoft Edge via CDP or AppleScript."""
    if mode in ("auto", "cdp") and CDPClient.is_available(port):
        tab = CDPClient.find_gemini_tab(port=port)
        if not tab and open_tab:
            tab = CDPClient.open_gemini_tab(port=port)
            if tab:
                time.sleep(2)
                tab = CDPClient.find_gemini_tab(port=port) or tab

        if tab:
            try:
                return CDPClient.execute_js(tab, js_code, port=port)
            except (ConnectionError, TimeoutError, OSError):
                if mode == "cdp":
                    raise
        elif mode == "cdp":
            raise RuntimeError(f"No open Gemini tab found in Edge via CDP on port {port}.")

    if mode == "cdp":
        raise RuntimeError(f"Edge CDP port {port} is not available.")

    if mode in ("auto", "applescript"):
        script = """
        on run argv
            set jsCode to item 1 of argv
            tell application "Microsoft Edge"
                repeat with w in windows
                    repeat with t in tabs of w
                        if (URL of t contains "gemini.google.com") and (URL of t contains "/app") then
                            with timeout of 60 seconds
                                set res to (execute t javascript jsCode)
                                return res
                            end timeout
                        end if
                    end repeat
                end repeat
                return "NO_GEMINI_TAB_FOUND"
            end tell
        end run
        """
        res = subprocess.run(["osascript", "-e", script, js_code], capture_output=True, text=True)
        if res.returncode != 0:
            err = res.stderr.strip()
            if "Allow JavaScript from Apple Events" in err:
                print("\n[Action Required in Edge]", file=sys.stderr)
                print("Please enable: Edge Menu Bar -> View -> Developer -> Allow JavaScript from Apple Events\n", file=sys.stderr)
            elif "-1712" in err or "AppleEvent timed out" in err:
                print("\n[AppleEvent Timeout]", file=sys.stderr)
                print("AppleScript execution timed out. The Edge tab or renderer may be unresponsive or sleeping.\n", file=sys.stderr)
            raise RuntimeError(f"AppleScript error: {err}")
        out = res.stdout.strip()
        if out == "NO_GEMINI_TAB_FOUND":
            raise RuntimeError("No open tab with gemini.google.com found in Edge.")
        return out

    raise ValueError(f"Unsupported execution mode: {mode}")


def bundle_markdown_files(
    paths: list[str],
    skill_name: str | None = None,
    json_prompt: bool = False,
    prompt_text: str | None = None,
) -> str:
    """Bundle target files and instructions into a structured prompt."""
    parts = []
    if skill_name:
        tag = skill_name.strip()
        if not (tag.startswith("@") or tag.startswith("/")):
            tag = f"@{tag}"
        parts.append(f"{tag}\n")

    if prompt_text:
        parts.append(prompt_text.strip() + "\n")

    if paths:
        parts.append("# ARCHITECTURAL DESIGN DOCUMENTS FOR REVIEW\n")
        for p in paths:
            path = Path(p)
            if not path.is_file():
                print(f"Warning: File not found: {p}", file=sys.stderr)
                continue
            content = path.read_text(encoding="utf-8")
            parts.append(f"## File: {path.name} (`{path.resolve()}`)\n")
            parts.append("```markdown\n" + content + "\n```\n")

    if json_prompt:
        parts.append("\n# INSTRUCTIONS FOR REVIEWER:\n")
        parts.append("Perform a thorough, strict architectural and security review of the provided documents.")
        parts.append("Evaluate against:")
        parts.append("1. Logical completeness, unhandled edge cases, and failure modes.")
        parts.append("2. Interface boundaries, data consistency, and module decoupling.")
        parts.append("3. Security: authentication, authorization, data-at-rest/in-transit risks.")
        parts.append("4. Operational reliability, scalability limits, and rollback feasibility.")
        parts.append("\nOutput your findings STRICTLY as a valid JSON object adhering to this schema:")
        parts.append('```json\n{\n  "issues": [\n    {\n      "severity": "P0" | "P1" | "P2",\n      "description": "..."\n    }\n  ]\n}\n```')
        parts.append("Use P0 or P1 for critical/blocking defects, and P2 for suggestions or minor issues.")
        parts.append('If no issues are found, return `{"issues": []}`.')
        parts.append("Do NOT include conversational preamble or markdown explanations outside the JSON.")
    elif not prompt_text:
        parts.append("\n# INSTRUCTIONS FOR REVIEWER:\n")
        parts.append("Perform a thorough, strict architectural and security review of the provided design documents.")
        parts.append("Evaluate against:")
        parts.append("1. Logical completeness, unhandled edge cases, and failure modes.")
        parts.append("2. Interface boundaries, data consistency, and module decoupling.")
        parts.append("3. Security: authentication, authorization, data-at-rest/in-transit risks.")
        parts.append("4. Operational reliability, scalability limits, and rollback feasibility.")
        parts.append("Output your review with explicit severity tags: [Critical/Blocker], [Warning], and [Suggestion].")

    return "\n".join(parts)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Automate design review via active Edge tab using CDP or AppleScript.")
    parser.add_argument("files", nargs="+", help="Markdown files to review")
    parser.add_argument("--skill", default=DEFAULT_SKILL, help=f"Skill mention tag (default: {DEFAULT_SKILL})")
    parser.add_argument("--out", default=DEFAULT_OUT, help=f"Output file path (default: {DEFAULT_OUT})")
    parser.add_argument("--timeout", default=DEFAULT_TIMEOUT, type=int, help=f"Max wait time in seconds (default: {DEFAULT_TIMEOUT})")
    parser.add_argument("--json-prompt", action="store_true", help="Request structured JSON output adhering to schema")
    parser.add_argument("--prompt", help="Optional additional review prompt text")
    parser.add_argument("--schema", help="Optional path to review JSON schema")
    parser.add_argument("--mode", choices=["auto", "cdp", "applescript"], default="auto", help="Bridge mode (default: auto)")
    parser.add_argument("--port", type=int, default=DEFAULT_CDP_PORT, help=f"CDP debug port (default: {DEFAULT_CDP_PORT})")
    parser.add_argument("--open-tab", action="store_true", help="Automatically open Gemini tab if missing")
    args = parser.parse_args(argv)

    payload = bundle_markdown_files(
        args.files,
        skill_name=args.skill,
        json_prompt=args.json_prompt,
        prompt_text=args.prompt,
    )

    try:
        current_url = run_edge_js("window.location.href", mode=args.mode, port=args.port, open_tab=args.open_tab)
        print(f"Connected to Gemini tab in Edge: {current_url}")
    except Exception as e:
        print(f"Error communicating with Microsoft Edge: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Injecting prompt with skill {args.skill} ({len(payload)} chars)...")
    payload_json = json.dumps(payload)
    inject_js = f"""
    (() => {{
        const text = {payload_json};
        const el = document.querySelector('div.ql-editor') || 
                   document.querySelector('div[contenteditable="true"]') || 
                   document.querySelector('textarea');
        if (!el) return 'INPUT_NOT_FOUND';
        if (el.tagName.toLowerCase() === 'textarea') {{
            el.value = text;
            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
        }} else {{
            el.innerHTML = '';
            const p = document.createElement('p');
            p.textContent = text;
            el.appendChild(p);
            el.dispatchEvent(new InputEvent('input', {{
                bubbles: true,
                cancelable: true,
                inputType: 'insertText',
                data: text
            }}));
        }}
        return 'OK';
    }})()
    """
    res = run_edge_js(inject_js, mode=args.mode, port=args.port, open_tab=args.open_tab)
    if res != "OK":
        print(f"Failed to inject text into input field: {res}", file=sys.stderr)
        sys.exit(1)

    dismiss_popover_js = """
    (() => {
        document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true}));
        return 'OK';
    })()
    """
    try:
        run_edge_js(dismiss_popover_js, mode=args.mode, port=args.port, open_tab=args.open_tab)
    except Exception:
        pass

    time.sleep(1)

    count_js = "document.querySelectorAll('message-content, model-response, .model-response-text, .response-container').length"
    try:
        initial_count = int(run_edge_js(count_js, mode=args.mode, port=args.port, open_tab=args.open_tab) or "0")
    except Exception:
        initial_count = 0

    print("Clicking Send button...")
    click_send_js = """
    (() => {
        let btn = document.querySelector("button[aria-label*='Send'], button[aria-label*='Gửi'], button.send-button");
        if (!btn) {
            const icon = document.querySelector("mat-icon[data-mat-icon-name='send'], mat-icon[fonticon='send'], mat-icon[svgicon='send']");
            if (icon) btn = icon.closest('button');
        }
        if (btn) {
            btn.click();
            return 'CLICKED: ' + (btn.getAttribute('aria-label') || 'send');
        }
        return 'BTN_NOT_FOUND';
    })()
    """
    res = run_edge_js(click_send_js, mode=args.mode, port=args.port, open_tab=args.open_tab)
    print(f"Send status: {res}")

    print("Waiting for generation stream to start...")
    check_stream_js = """
    (() => {
        const stopBtn = document.querySelector("button[aria-label*='Stop'], button[aria-label*='Dừng'], .stop-button");
        const msgs = document.querySelectorAll('message-content, model-response, .model-response-text, .response-container');
        const text = msgs.length > 0 ? msgs[msgs.length - 1].innerText : '';
        return JSON.stringify({
            isStreaming: !!stopBtn,
            count: msgs.length,
            textLen: text.length
        });
    })()
    """
    wait_start = time.time()
    while time.time() - wait_start < 30:
        time.sleep(1)
        try:
            state = json.loads(run_edge_js(check_stream_js, mode=args.mode, port=args.port, open_tab=args.open_tab))
            current_count = state.get("count", 0)
            is_streaming = state.get("isStreaming", False)
            if current_count > initial_count or is_streaming:
                break
        except Exception:
            continue

    print("Waiting for Gemini Argon generation to stream and finish...")

    start_time = time.time()
    last_len = 0
    stable_checks = 0

    while time.time() - start_time < args.timeout:
        time.sleep(2)
        try:
            state = json.loads(run_edge_js(check_stream_js, mode=args.mode, port=args.port, open_tab=args.open_tab))
        except Exception:
            continue

        is_streaming = state.get("isStreaming", False)
        curr_len = state.get("textLen", 0)

        if curr_len > 100:
            if not is_streaming and curr_len == last_len:
                stable_checks += 1
                if stable_checks >= 2:
                    print(f"Generation complete (response size: {curr_len} characters).")
                    break
            else:
                stable_checks = 0

        last_len = curr_len
    else:
        print(f"Warning: Reached timeout ({args.timeout}s) waiting for generation to finish.", file=sys.stderr)

    print("Extracting generated review...")
    extract_js = """
    (() => {
        const elements = document.querySelectorAll('message-content, model-response, .model-response-text, .response-container');
        if (elements.length === 0) return 'NO_RESPONSE_FOUND';
        return elements[elements.length - 1].innerText;
    })()
    """
    review_output = run_edge_js(extract_js, mode=args.mode, port=args.port, open_tab=args.open_tab)
    if review_output == "NO_RESPONSE_FOUND" or not review_output:
        print("Error: Could not extract response from DOM.", file=sys.stderr)
        sys.exit(1)

    out_file = Path(args.out)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(review_output, encoding="utf-8")
    print(f"\n[Success] Review written to {out_file.resolve()}\n")
    print(review_output[:1200] + ("\n... [remaining review in file] ..." if len(review_output) > 1200 else ""))


if __name__ == "__main__":
    main()
