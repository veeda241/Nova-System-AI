# Nova architecture

Nova is a terminal agent built on the five primitives OpenJarvis uses to describe a
local-first personal AI: **Intelligence, Engine, Agents, Tools & Memory, Learning**. Each
primitive is one directory (or one module) in `src/nova/`, so you can read a layer without
reading the whole repo.

```text
you (PowerShell)
  |
  v
nova/cli/app.py ---- argv -> subcommand -> globals (--engine/--mode/--json/--quiet)
  |
  +-- nova ask  --> intelligence + engine only (no tools)
  +-- nova go   --> agents/react.py  <---------------- ReAct loop
  +-- nova chat --> REPL around both
                    |
        +-----------+------------+
        v                        v
  engine/  (ollama>groq>     tools/  (21 tools, each with a risk label)
           gemini>openai)         |
        |                         v
        v                   security.py  PermissionGate
   intelligence.py                 |
   (persona + JSON action         v
    grammar + parser)      tools/files.py sandbox, tools/shell.py subprocess
                                 |
                                 v
              memory/ (JSON facts + SQLite notes)   learning/ (JSONL traces)
```

## 1. Intelligence — `src/nova/intelligence.py`

The prompt contract. `PERSONA` says Nova acts through tools and never invents results.
`ACTION_GRAMMAR` requires exactly one JSON object per reply:

```json
{"thought": "why", "action": "write_file", "args": {"path": "notes.md", "content": "..."}}
{"thought": "why", "action": "final", "args": {"message": "the answer"}}
```

`extract_json()` tolerates code fences and chatty prose by scanning for the first complete
object; `normalise_action()` accepts the shapes small models actually produce (`tool`,
`reasoning`, a bare `message`); `parse_reply()` returns `(action, args, thought, error)`.
A reply with no JSON at all is treated as the final answer, not retried forever.

`validate_python()` is a real AST check (syntax errors with line numbers, top-level
function names, `eval`/`exec`/`compile`/`__import__` usage) used by `nova validate`.

## 2. Engine — `src/nova/engine/`

`Engine` (in `base.py`) is the contract: `probe`, `complete`, `list_models`,
`available_reason`, `is_local`, `priority`. Four implementations:

| engine   | priority | transport                        | needs              |
|----------|----------|----------------------------------|--------------------|
| `ollama` | 1        | `POST /api/chat`, `/api/tags`    | local server       |
| `groq`   | 2        | OpenAI-style chat completions    | `GROQ_API_KEY`     |
| `gemini` | 3        | `generateContent` + systemInstruction | `GEMINI_API_KEY` |
| `openai` | 4        | chat completions                 | `OPENAI_API_KEY`   |

`Registry.select("auto")` walks priorities and returns the first engine that probes OK.
`Registry.complete()` retries a **transient** failure 3 times with linear backoff
(`_attempt`, pause 4s → 8s) before failing over to the next engine; `is_transient()` matches
429/5xx/"high demand"/"rate limit"/"timed out". A 401 or a bad model name is not retried.

`scrub()` rewrites `?key=`, `Bearer`, `AIza…`, `sk-…`, `gsk_…` in every error string, so a
key can never leak into output or logs. 404s add a hint to run `nova engine models`.

## 3. Agents — `src/nova/agents/`

`ReactAgent.run()` (`react.py:66`) is the loop: build messages → one model call → parse one
action → execute it → append the real observation → repeat, up to `max_steps` (default 12,
`--max-steps`). `_messages()` re-sends system prompt + memory block + transcript every step;
`history_block()` keeps the last 8 exchanges, `_short()`/`format_observation()` cap tool
output at ~1.4 KB so a 3B local model can still reason over it.

Three failure paths return early: no engine (before any tool runs), the model never
producing valid JSON (after 3 bad replies), and the step budget. Denials are collected in
`AgentOutcome.denials` and reported instead of retried.

`agents/__init__.py` also holds `answer()` (single-shot, tool-free, memory-aware) and
`looks_like_action()`, which is how the REPL decides whether your line is a question or a
goal.

## 4. Tools & Memory — `src/nova/tools/`, `src/nova/memory/`

A `Tool` (`tools/__init__.py:17`) carries `name, description, handler, params, risk,
requires, example`; `Registry.prompt_block()` renders them into the system prompt and
`call_gated()` is the only path the agent uses (`tools/__init__.py:117`).

- `tools/files.py` — everything goes through `resolve()` (`:26`) then `_guard()` (`:41`):
  a path outside `workspace/` is refused unless `allow_outside=true` **and** the gate is
  approved, and the escape check runs before any existence probe so the sandbox cannot
  leak which paths exist.
- `tools/shell.py` — `run_command` uses `shell=True` inside the workspace cwd with a clamped
  timeout (1..600 s); `run_python`/`run_python_file` spawn `python -B`. All three are `exec`
  risk, so they prompt in `ask` mode.
- `tools/system.py` — read-only host info; `top_processes` reports honestly when `psutil` is
  missing instead of returning an empty list.
- `memory/store.py` — JSON facts + task history (`.nova/memory.json`).
- `memory/kb.py` — SQLite `knowledge(category,key,value)` and `snippets` tables.
- `memory/__init__.py:11` `context_block()` builds the ≤1200-char "KNOWN FACTS / RECENT
  TASKS / RELATED NOTES" block that is prepended to the system prompt.

## 5. Learning — `src/nova/learning/`

`TraceLog` appends one JSONL row per event (`session_open`, `llm_response`, `tool_call`,
`tool_result`, `error`, `session_close`) to `.nova/traces.jsonl`, and `stats()` aggregates
success rate, average tool latency, slowest tool, most-used tools, top errors and engines
used. Traces are for inspection and for writing skills — **Nova does not fine-tune a model
from them**, and the modules that claimed otherwise were deleted in v3.

## Permission model (`src/nova/security.py`)

Risks ladder up: `read(0) → write(1) → exec(2) → destructive(3)`. `review()` (`:63`) decides
in this order:

1. **hard block** (`HARD_BLOCKS`, `:18`) — drive/root recursive delete, `mkfs`,
   `format c: /q`, `del /f /s C:\`, fork bomb, `shutdown /f /t`, `curl … | sh`. These fire
   even in `yolo`.
2. session grant for that tool name (`a` at the prompt) — reused for the rest of the run.
3. `needs_approval` (`:54`) is false → auto-approved: risk at or below `auto_risk`
   (default `read`), or mode `yolo`. Reads never prompt.
4. mode `deny` → refuse.
5. no TTY → refuse with a message naming `--yolo`, rather than guessing or hanging.

Modes come from `--mode` / `--yolo`, then `NOVA_YOLO=1`, then `approval_mode` in
`.nova/settings.json`.

## State on disk

| path | what it holds | tracked by git |
|------|---------------|----------------|
| `.nova/settings.json` | engine, models, `max_steps`, `approval_mode`, `voice` | no |
| `.nova/memory.json` | facts + task history | no |
| `.nova/knowledge.db` | SQLite notes and snippets | no |
| `.nova/traces.jsonl` | per-step trace log | no |
| `workspace/` | the only place file tools act by default | no |
| `.env` | API keys | no |

`NOVA_HOME` is the repo root (or whatever you export); `NOVA_WORKSPACE` overrides the
sandbox root, which is how the tests point Nova at a throwaway directory.

## Extending

**New tool:** write the function, then add one `Tool(...)` with a `risk` label and a
`requires` note to `build_registry()` in `src/nova/tools/__init__.py:147`. It appears in
`nova tools list`, in the agent's prompt block, and behind the gate automatically.

**New engine:** subclass `Engine` in `src/nova/engine/`, set `priority`, register it in
`FACTORIES` (`engine/__init__.py:17`). Raise `EngineError` with a specific message — it is
scrubbed and classified for retry for free.
