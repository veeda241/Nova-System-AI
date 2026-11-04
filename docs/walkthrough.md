# Nova walkthrough: one command, start to finish

Read this after [architecture.md](architecture.md). It follows a single
`nova go "write notes.md summarising this workspace"` from the PowerShell prompt to the
bytes on disk, in the order you would actually read the source. Every reference is a real
file and line in this repo.

## Step 0 — how the process starts

Two entry points, one implementation:

- the `nova` console script → `nova.cli.app:main` ([`pyproject.toml`](../pyproject.toml), `[project.scripts]`)
- `python -m nova` → `src/nova/__main__.py:8`, which calls the same `main()`

`main()` is at [src/nova/cli/app.py:636](../src/nova/cli/app.py#L636). It does exactly five
things: force UTF-8 output, build the parser, normalise the args, apply globals, dispatch.
Nothing else happens before you understand the flow.

```python
ui.force_utf8()
parser = build_parser()
args = normalise(parser.parse_args(argv))
apply_globals(args)
handler = DISPATCH.get(command, cmd_chat if command is None else None)
```

`DISPATCH` ([:617](../src/nova/cli/app.py#L617)) maps the subcommand name to a `cmd_*`
function. A bare `nova` with no subcommand falls through to `cmd_chat`, which is why the
tool "opens the interactive shell" without any special-casing in the parser.

Exit codes are part of the contract because scripts and tests depend on them:
`0` success, `1` agent stopped / action failed, `2` unknown command (help printed),
`3` no engine usable, `130` Ctrl-C.

## Step 1 — parsing without surprises

`_global_parser()` ([:26](../src/nova/cli/app.py#L26)) declares `--engine --mode --yolo
--workspace --max-steps --json --quiet` with `default=argparse.SUPPRESS`, and every
subparser is built with `parents=[global_]`. SUPPRESS matters: without it the subparser's
own default (`None`/`False`) overwrites the value you passed *before* the subcommand, so
`nova --json doctor` would silently lose `--json`.

`normalise()` ([:91](../src/nova/cli/app.py#L91)) then guarantees the attribute exists on
the namespace at all (`getattr(args, flag, None)`), so downstream code never raises
`AttributeError` for a flag that belongs to a different subcommand.

`apply_globals()` ([:102](../src/nova/cli/app.py#L102)) loads `.env`, optionally moves the
sandbox root, and calls `config.override()` for `engine`/`approval_mode`/`max_steps`.

> This is the fix for a real bug: these flags used to be written into
> `.nova/settings.json`, so one `nova go --mode yolo` left the user permanently in yolo.
> Overrides now live in `config.OVERRIDES`
> ([src/nova/config.py:101](../src/nova/config.py#L101)) for the lifetime of the process
> only. `config.get()` reads overrides first, then the saved file, then `DEFAULTS`.

## Step 2 — the gate is built before the agent

`make_gate()` ([:112](../src/nova/cli/app.py#L112)) returns
`PermissionGate(mode=default_mode(args.mode))`. `default_mode()`
([src/nova/security.py:120](../src/nova/security.py#L120)) resolves precedence:

1. `--mode` / `--yolo` on this command line
2. `NOVA_YOLO=1` in the environment
3. `approval_mode` in `.nova/settings.json`
4. `ask`

The gate is created in the CLI, not inside the agent, and is then passed down. That is what
lets `nova tools call write_file` and the ReAct loop share one policy object — and what
lets the REPL flip modes mid-session (`/mode yolo` mutates `agent.gate.mode`).

## Step 3 — `nova go` hands off to the agent

`cmd_go()` ([:145](../src/nova/cli/app.py#L145)) is only formatting:

```python
agent = ReactAgent(gate=make_gate(args), max_steps=args.max_steps, verbose=not args.quiet and not args.json)
outcome = agent.run(" ".join(args.goal))
```

`--first-step` just sets `agent.max_steps = 1` — a cheap way to see what the model *would*
do without letting it touch anything. `cmd_ask()`
([:130](../src/nova/cli/app.py#L130)) takes the other branch: `agents.answer()`
([src/nova/agents/__init__.py:25](../src/nova/agents/__init__.py#L25)), one completion, no
tools, no gate.

## Step 4 — the loop

`ReactAgent.run()` ([src/nova/agents/react.py:67](../src/nova/agents/react.py#L67)).

First it opens a trace session (`self.log.new_session()`) and selects an engine. If *no*
engine probes successfully it returns immediately, before any tool exists:

```python
return AgentOutcome(False, f"no engine available:\n{exc}", ...)
```

Then, for each step up to `max_steps`:

| line | what happens |
|------|--------------|
| [:207](../src/nova/agents/react.py#L207) `_messages()` | build `[system, user]` from tools block + memory block + workspace + transcript |
| — | `self.engines.complete(messages, temperature=0.2, preferred=...)` |
| [:96](../src/nova/intelligence.py#L96) `parse_reply()` | text → `(action, args, thought, error)` |
| — | bad JSON? append a correction to the transcript and retry (max 2) |
| — | `action == "final"`? report and return |
| [:225](../src/nova/agents/react.py#L225) `_observe()` | execute the tool through the gate, compact the result |

Two details that matter for reliability:

**The transcript is rebuilt from scratch each step.** `_messages()` is called inside the
loop, so the model sees the real observations, not what it hoped would happen.
`history_block()` ([intelligence.py:42](../src/nova/intelligence.py#L42)) keeps the last 8
exchanges and truncates each observation to 300 chars in that view.

**Parse failures are recovered, not retried blindly.** `extract_json()`
([:52](../src/nova/intelligence.py#L52)) strips code fences, tries `json.loads`, then falls
back to scanning every `{` with `raw_decode` until it finds a dict containing `action` or
`thought`. `normalise_action()`
([:77](../src/nova/intelligence.py#L77)) accepts the shapes small models actually emit —
`tool` instead of `action`, `reasoning` instead of `thought`, a bare `message`. If there is
genuinely no JSON, `fallback_to_final=True` treats the prose as the answer instead of
looping. Only a *malformed* action costs a retry, and after two the run stops with
`error="bad_protocol"`.

## Step 5 — the engine call

`Registry.complete()` ([src/nova/engine/__init__.py:68](../src/nova/engine/__init__.py#L68))
puts the currently active engine first, then walks the rest by priority. For each candidate:
`probe()` (cheap: `/api/tags`, `/v1/models` or "is a key set"), then `_attempt()`
([:93](../src/nova/engine/__init__.py#L93)) — 3 tries with linear backoff (4 s, 8 s) but
**only** when `is_transient()`
([engine/base.py:36](../src/nova/engine/base.py#L36)) recognises 429/5xx/"high demand"/
"rate limit"/"timed out". A 401 or an unknown model fails over immediately; hammering a
key you don't have is never retried.

Every exception passes through `scrub()`
([engine/base.py:20](../src/nova/engine/base.py#L20)), which rewrites `?key=`, `Bearer`,
`AIza…`, `sk-…`, `gsk_…`, `hf_…` before the string reaches a terminal, a trace row or a test.

## Step 6 — the gate decides

`_observe()` ([react.py:225](../src/nova/agents/react.py#L225)) first checks the tool name
against the registry, so a hallucinated tool becomes an observation ("UNKNOWN TOOL ... Available: ...")
rather than a crash. Then:

```python
result, reason = self.tools.call_gated(tool_name, args, self.gate)
```

`call_gated()` ([src/nova/tools/__init__.py:117](../src/nova/tools/__init__.py#L117)) is the
*only* path the agent has to a handler, and it deliberately cannot be bypassed: it builds a
human-readable summary, calls `gate.review()`, and returns a `denied` result **without ever
calling the handler** when the decision is no.

`review()` ([src/nova/security.py:63](../src/nova/security.py#L63)) decides in this order:

1. `HARD_BLOCKS` ([security.py:18](../src/nova/security.py#L18)) — regex over the command /
   path text. `rm -rf /`, `format c: /q`, `del /f /s C:\`, `mkfs`, fork bombs,
   `shutdown /f /t 0`, `curl … | sh`. These fire even in `yolo`; there is no mode that means "yes, really".
2. an earlier `[a]` always-grant for that tool name in this session, as long as the risk is
   still above `auto_risk`.
3. `needs_approval()` ([:54](../src/nova/security.py#L54)) — risk at or below `auto_risk`
   (default `read`) → auto-approved, and mode `yolo` → auto-approved. Reads never prompt.
4. mode `deny` → refuse.
5. no TTY → refuse with a reason that names `--yolo`
   ([:85](../src/nova/security.py#L85)). `_prompt()`
   ([:88](../src/nova/security.py#L88)) also catches `EOFError`/`KeyboardInterrupt` and
   marks the gate non-interactive, so a piped run can neither hang nor approve itself.

Back in `_observe()`, a denial is rendered as `DENIED (reason): ...` and recorded in
`AgentOutcome.denials`. The ACTION_GRAMMAR tells the model not to retry a blocked step —
the honest outcome is a report of what was blocked.

## Step 7 — the tool runs in a sandbox

`Registry.call()` ([:91](../src/nova/tools/__init__.py#L91)) checks availability
(`requires` → `importlib.util.find_spec`, so a missing `psutil` produces *"needs `pip install
psutil`"*, not an ImportError), checks required args, calls the handler, and stamps `_ms`
and `_tool` on the result. All exceptions become `{"ok": False, "error": ...}` — the loop
never dies because a tool did.

For `write_file`, `files.write_file()`
([src/nova/tools/files.py:140](../src/nova/tools/files.py#L140)) is reached through the two
functions every file tool calls first:

```python
located = resolve(path)   # files.py:41 — absolute path, inside?, exists?, rel
_guard(located, args)     # files.py:56 — refuse escape *before* touching the disk
```

`resolve()` never raises; `_guard()` raises `SandboxError` when `inside` is false and
`allow_outside` is not set. Ordering is the security property: if existence were checked
first, an attacker-model could map your filesystem by which errors it got back.
`require_exists()` ([:65](../src/nova/tools/files.py#L65)) is only for read/move/delete
paths that must exist.

`tools/shell.py` has the same discipline from the other side: `run_command()`
([:44](../src/nova/tools/shell.py#L44)) clamps the timeout to 1..600 s, runs with
`cwd=str(config.WORKSPACE)`, and kills the child on timeout with a message that says so.

## Step 8 — the observation goes back into the loop

`format_observation()` ([react.py:265](../src/nova/agents/react.py#L265)) prefers the one
field that carries the payload (`content`, `stdout`, `output`, `text`, `tree`), caps it at
1400 chars and appends `[+N chars]` so the model knows it is looking at an excerpt. That
marker is what stops a small model from "summarising" a file it only saw half of. The facts
before the body are ordered numbers-first (`lines=7, size=146, … content=…`) because a 3B
model answering "how many lines" reads the head of the line and stops there.

## Step 8b — what stops the loop from spinning

A weak model does not fail by crashing; it fails by asking the same question of the same
tool until the budget runs out. Three guards in `run()` spend steps on that, and all three
write a trace row so `nova traces session <id>` shows what was refused:

| guard | fires when | observation the model gets |
|-------|-----------|----------------------------|
| `_signature()` ([react.py:260](../src/nova/agents/react.py#L260)) | the same tool with the same arguments has already been called twice | `REPEAT BLOCKED` — and the handler is never reached |
| the failure counter | the same tool failed twice for the *same* reason (the denial text is part of the key) | `TOOL BLOCKED` — that tool is closed for the rest of the run |
| `STEPS LEFT: n` in `_messages()` | three steps remain | says an observation starting `OK` already holds the data, so answer instead of looking again |

If the budget still runs out, `_salvage()`
([react.py:177](../src/nova/agents/react.py#L177)) makes one last tool-free call that asks
for an answer from the transcript. You get the answer, still labelled `ok: false,
error: "max_steps"` — the run did not verify anything, and pretending otherwise would be the
one failure mode worth hiding. If the model used that call to ask for another tool, the
reply is discarded rather than dressed up as a result.

## Step 9 — everything is written down

Two sinks, both append-only, both off by design from git:

- `TraceLog.record()` ([src/nova/learning/__init__.py:27](../src/nova/learning/__init__.py#L27))
  — one JSONL line per event in `.nova/traces.jsonl`. `_shrink()`
  ([:81](../src/nova/learning/__init__.py#L81)) bounds every field so a 200 KB tool result
  cannot bloat the log. `stats()` ([:58](../src/nova/learning/__init__.py#L58)) is what
  `nova traces stats` prints: success rate, per-tool latency, slowest tool, top errors.
- `MemoryStore.log_task()`
  ([src/nova/memory/store.py:66](../src/nova/memory/store.py#L66)) — via `_finish()`
  (react.py:254](../src/nova/agents/react.py#L254)), one compact row in `.nova/memory.json` with goal, ok, summary, tool list,
  steps, engine.

That row is what the *next* run injects as `RECENT TASKS` through `context_block()`
([src/nova/memory/__init__.py:11](../src/nova/memory/__init__.py#L11)), so memory closes the
loop without any model training. `nova skills add` is how you turn a good trace into a
deterministic replay: `skills.run()`
([src/nova/skills.py:92](../src/nova/skills.py#L92)) walks the stored steps through the same
`call_gated()` and stops at the first failure with `failed_at`.

## Step 10 — what you actually see

Back in `cmd_go()`: the final text, then `steps=… engine=… tools=…`, then a warning with the
count of blocked actions. With `--json` you get `AgentOutcome.as_dict()`
([react.py:30](../src/nova/agents/react.py#L30)) instead, which is the shape the tests and
any wrapper script should rely on.

Rendering goes through `cli/ui.py`: `force_utf8()` ([:21](../src/nova/cli/ui.py#L21)) stops
`UnicodeEncodeError` on a Windows codepage, and `kv()`
([:94](../src/nova/cli/ui.py#L94)) sizes table columns with `_fit()`
([:80](../src/nova/cli/ui.py#L80)) so `nova doctor` fits an 80-column terminal and falls
back to plain text when `rich` isn't installed.

## Reading order if you want the short version

1. [src/nova/cli/app.py:636](../src/nova/cli/app.py#L636) `main` — dispatch and exit codes
2. [src/nova/cli/app.py:145](../src/nova/cli/app.py#L145) `cmd_go` — how an agent is built
3. [src/nova/agents/react.py:67](../src/nova/agents/react.py#L67) `run` — the loop
4. [src/nova/intelligence.py:96](../src/nova/intelligence.py#L96) `parse_reply` — the protocol
5. [src/nova/engine/__init__.py:68](../src/nova/engine/__init__.py#L68) `complete` — failover
6. [src/nova/tools/__init__.py:117](../src/nova/tools/__init__.py#L117) `call_gated` — the chokepoint
7. [src/nova/security.py:63](../src/nova/security.py#L63) `review` — the ladder
8. [src/nova/tools/files.py:56](../src/nova/tools/files.py#L56) `_guard` — the sandbox
9. [src/nova/learning/__init__.py:27](../src/nova/learning/__init__.py#L27) `record` — the audit trail
