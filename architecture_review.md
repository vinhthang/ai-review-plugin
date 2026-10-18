This architectural and security review evaluates 0002_orchestrator_paradigm_shift.md, spec.md, design.md, and decisions.md (2026-10-14-argon-web-reviewer) using Spec-Driven Development verification principles.

While refactoring the engine dispatch into a pluggable registry (REQ-036) is a solid structural improvement, the design for the AppleScript-driven Edge automation runner (REQ-037) and the hybrid response parser (REQ-039) introduces critical failure modes, false-approval gating risks, and cross-document contradictions.

1. Logical Completeness, Unhandled Edge Cases, & Failure Modes

[Critical/Blocker] False-"Approved" Gate Bypass in Markdown Fallback (REQ-039 / design.md §3.4):

Analysis: In design.md §3.4, if the raw response from Gemini is not valid JSON and lacks a json fence, MarkdownFallback runs a regex scan for [Critical], [Warning], and [Suggestion] to synthesize { "issues": [...] }. Under AC-039.5, review_status is set to "approved" when no P0/P1 issues are present. If the Gemini web interface returns an inline UI error banner (e.g., "Something went wrong", "You've reached your usage limit for Gemini"), a safety refusal, or an unformatted prose critique that omits bracketed tags, the regex scan will yield zero matches ({"issues": []}), and the orchestrator will falsely mark a broken or rejected review as "approved".

Remediation: Require an explicit positive-acknowledgment sentinel or structural heading in the Markdown fallback (e.g., verifying the presence of an explicit [Review Status: APPROVED] token or mandatory section headers) before allowing an empty issues array to resolve to review_status = "approved". If neither valid JSON nor any recognized review structure/tags are found, the parser must raise a FatalReviewError (design.md §4.4) rather than returning an empty issue list.

[Critical/Blocker] Stale DOM Extraction Race Condition (REQ-037 / design.md §3.2):

Analysis: design.md §3.2 states that edge_applescript_runner.py injects the prompt, clicks send, and immediately "Polls stop button presence (isStreaming) and character length stability (stable_checks >= 2)." When reusing an existing gemini.google.com tab that already contains a previous conversation turn, there is a 200ms–1,500ms network/UI latency between clicking the Send button and the "Stop generating" button appearing in the DOM. Polling immediately after clicking Send will observe isStreaming == false and a stable character length on the previous response element, causing the runner to immediately extract the stale response from the prior run.

Remediation: Before clicking Send, record the current count of model response containers in the DOM (e.g., initial_response_count). After clicking Send, enter a pre-stream wait phase that blocks until current_response_count > initial_response_count (or isStreaming == true) before transitioning to the completion-stability polling loop.

[Critical/Blocker] Premature Submit via execCommand('insertText') on @skill Mention (REQ-037 / AC-038.4):

Analysis: design.md §3.2 specifies injecting the prompt into Quill (.ql-editor) using document.execCommand('insertText', false, text) with @software-architect-reviewer prepended. In Gemini Web's Quill editor, typing @software-architect-reviewer triggers an asynchronous floating autocomplete popover (mat-option / mention menu). If the prompt contains newlines or if the script programmatically clicks Send before explicitly selecting/resolving the mention item from the popup menu, Gemini either treats @software-architect-reviewer as literal plain text (never invoking the Gem/extension) or intercepts the Enter key inside the autocomplete menu.

Remediation: Separate the @skill invocation from the bulk payload injection in edge_applescript_runner.py: first type the @<skill> prefix, wait for and click the matching autocomplete DOM node (or dispatch a Tab/Enter key event on the active menu item), verify the chip/pill element is rendered in .ql-editor, and only then inject the body text.

[Warning] Non-Deterministic Severity Mapping in AC-039.2 and AC-039.3:

Analysis: AC-039.2 states: "If the response contains markdown severity tags ([Critical/Blocker], [Critical], [Blocker]), map them to severity P0 or P1." AC-039.3 states: "If the response contains [Warning], map to severity P1 or P2." A deterministic regex parser cannot arbitrarily choose between P0 or P1, and the distinction between P1 and P2 for [Warning] is critical because AC-039.5 gates approval on P0/P1 ("approved" when no P0/P1 issues, "rejected" otherwise). Whether [Warning] maps to P1 or P2 changes the gate outcome from Rejected to Approved.

Remediation: Define a strict, bijective 1:1 mapping in REQ-039 and design.md (e.g., [Critical]/[Blocker]/[Critical/Blocker] 
→
→ P0, [Warning] 
→
→ P1 (or P2 if warnings are non-blocking), [Suggestion] 
→
→ P2).

[Warning] Greedy/Multi-Block Regex Extraction on Code Fences (design.md §3.4):

Analysis: design.md §3.4 specifies extracting fenced JSON via ```json\s*(.*?)\s*```. Because the prompt includes the target design documents—and those design documents or the reviewer's remediation examples frequently contain their own json blocks—a naive re.search will match the first illustrative JSON snippet rather than the canonical ReviewEnvelope block, or fail if the LLM nests triple backticks inside a JSON string field.

Remediation: Iterate over all json matches in reverse order (or scan for the outermost { ... } containing "issues"), and validate that the parsed object conforms to the expected schema before halting search.

2. Interface Boundaries, Data Consistency, & Module Decoupling

[Warning] Violation of Open/Closed Principle in resolve_engine() (REQ-036 vs. design.md §3.1):

Analysis: REQ-036 (AC-036.3) and ADR-037 mandate a pluggable registry so future engines can be added without modifying core dispatch logic. However, design.md §3.1 states that resolve_engine(cli_engine, session_id) checks hardcoded prefixes (workbuddy: 
→
→ workbuddy, codex: 
→
→ codex, argon-web: 
→
→ argon-web) while ADR-037 states adapters define supported_prefixes. Furthermore, design.md §3.1 calls get_supported_engines() whereas ADR-037 calls get_registered_engines().

Remediation: Align the method names across spec.md, design.md, and decisions.md. Delegate prefix resolution dynamically by iterating over ENGINE_REGISTRY.values() and checking adapter.supported_prefixes rather than hardcoding prefix branches inside resolve_engine().

[Warning] Architectural Conflict Between Stateless Orchestrator (0002_orchestrator_paradigm_shift.md), Non-Goals (spec.md §3), and Session Binding (REQ-038):

Analysis: 0002_orchestrator_paradigm_shift.md declares peer_review.py completely stateless, and spec.md §3 explicitly states: "Argon Web Reviewer operates as a stateless single-turn review pass; multi-turn prompt negotiation is out of scope." Yet AC-038.3 and design.md §3.3 require ArgonWebAdapter to preserve and bind prior_session_id (argon-web:<uuid>), while edge_applescript_runner.py (AC-037.2) does not accept a --session-id argument and simply dumps text into whichever gemini.google.com tab happens to be active.

Remediation: If argon-web:<uuid> is strictly a synthetic identifier to satisfy the existing ReviewEngineAdapter interface contract so the calling AI Agent can sticky-route retries to argon-web, state this explicitly in design.md §3.3. Otherwise, if tab/conversation affinity is expected, pass the conversation URL slug ([gemini.google.com/app/](https://gemini.google.com/app/)<id>) to the runner.

[Warning] Multi-File CLI Contract Mismatch (AC-037.2 vs. design.md §3.3):

Analysis: AC-037.2 defines the runner CLI signature as accepting multiple files (<files...> --out <output_path>), whereas design.md §3.3 defines build_command(...) as passing a single target_file alongside an undocumented --json-prompt flag that is absent from AC-037.2. In code or design review modes (such as this very prompt, which bundles 0002_orchestrator_paradigm_shift.md, spec.md, design.md, and decisions.md), passing only a single target_file breaks multi-document reviews.

Remediation: Formalize the exact CLI flags of edge_applescript_runner.py in both spec.md and design.md, ensuring build_command passes all target files (*target_files) or a pre-rendered prompt file path (--prompt-file <path>).

3. Security: Authentication, Authorization, & Data-at-Rest/In-Transit Risks

[Critical/Blocker] Process-Table Exposure & ARG_MAX Exhaustion via osascript CLI Arguments (design.md §3.2):

Analysis: design.md §3.2 specifies executing JS via subprocess.run(["osascript", "-e", script, js_code]) where js_code contains the serialized review prompt and target files. Passing full design documents or code diffs as command-line arguments exposes potentially sensitive source code to any local user polling ps aux / proc_pidinfo, and will crash with OSError: [Errno 7] Argument list too long once the prompt/diff approaches macOS ARG_MAX (1 MB) or AppleScript string literal limits.

Remediation: Do not pass the prompt or JS payload via CLI argv. Write the payload to a temporary file with 0o600 permissions (or pipe it via stdin into osascript -) and read it inside the AppleScript/JS boundary, or pass the payload via a local loopback clipboard/file mechanism.

[Warning] DOM-Based Prompt Injection & Unescaped Payload Termination (design.md §5):

Analysis: design.md §5 mentions an "Untrusted Target Prompt Guard" instructing Gemini to treat the input document as passive data. However, if the target Markdown file itself contains the closing delimiter tag (e.g., </untrusted_document>) or contains @ mentions and slash commands, injecting it raw into .ql-editor can break out of the prompt guard or trigger unintended Gemini extensions in the user's logged-in browser session.

Remediation: Sanitize or escape closing boundary tags and leading @ symbols within the target document payload before injecting it into the DOM, or use randomized per-run boundary nonces (e.g., <document_payload_${UUID}>).

[Warning] Cross-Tab Targeting & Consumer Account Data Leakage:

Analysis: AC-037.3 states the runner "queries the active Microsoft Edge tab matching gemini.google.com via osascript." If the developer has multiple Edge windows/profiles open (e.g., a personal Google account and a corporate Google Workspace account), an AppleScript loop scanning every window and every tab whose URL contains "gemini.google.com" may inject proprietary repository specs into a personal consumer Gemini tab (where chat history is logged and reviewed by human annotators).

Remediation: Allow specifying or validating the expected window/tab or URL pattern, and log the exact tab URL/title matched before injecting the payload.

4. Operational Reliability, Scalability Limits, & Rollback Feasibility

[Warning] Concurrent Subagent Collision on Single Browser Tab (0002_orchestrator_paradigm_shift.md & REQ-037):

Analysis: 0002_orchestrator_paradigm_shift.md removes all fcntl file locks from peer_review.py. However, edge_applescript_runner.py mutates a single shared stateful resource: the active gemini.google.com DOM in Microsoft Edge. If an AI agent spawns two parallel review subagents (or a user runs a standalone CLI review while an background audit is running), both processes will simultaneously call execCommand('insertText') into the same .ql-editor node, interleaving their prompts and corrupting both reviews.

Remediation: While peer_review.py itself can remain stateless regarding retry counters, edge_applescript_runner.py must enforce a lightweight mutex (or atomic lockfile /tmp/argon_edge_runner.lock) around the browser tab interaction, or explicitly open/target an isolated tab per invocation and close it upon extraction.

[Warning] Chromium Background Tab Throttling & DOM Virtualization:

Analysis: AC-037.3 requires the runner to operate "without GUI focus." When Microsoft Edge is minimized, occluded by another fullscreen app, or when gemini.google.com is in a background tab, Chromium's Intensive Wake Up Throttling and requestAnimationFrame suspension can stall Angular/Quill DOM rendering and streaming updates, causing the 240s polling loop to time out or extract an unrendered response. Additionally, for massive prompts (>50KB), document.execCommand('insertText') on a contenteditable div synchronously blocks the renderer main thread and can freeze the tab.

Remediation: Instead of simulating character-by-character insertText for massive payloads, use a synthetic ClipboardEvent('paste') with DataTransfer in the injected JS (which Quill handles asynchronously in bulk without freezing the DOM), and ensure the polling script triggers a layout read or targets an active tab in its own unminimized window.

[Suggestion] Missing Cleanup / Rollback of In-Browser State on Timeout (design.md §4.3):

Analysis: design.md §4.3 states that on a 240s timeout, the runner performs a "Clean termination of polling loop with timeout diagnostic." However, if the Python process exits while Gemini is still streaming in the browser tab, a subsequent retry triggered by the AI agent (0002_orchestrator_paradigm_shift.md) will attach to the same tab while it is still mid-stream from attempt #1.

Remediation: On timeout or SIGINT/SIGTERM, edge_applescript_runner.py should attempt to click the "Stop generating" button in the Gemini DOM and clear any leftover draft text in .ql-editor before exiting.