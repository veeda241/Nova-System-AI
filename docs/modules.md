# Nova module map

One entry per file. Each says what the module owns, the names you should actually look for,
and the failure mode it was written to prevent. Paths are relative to the repo root.

```text
src/nova/{__init__,__main__,config,intelligence,security,skills,voice}.py
src/nova/cli/{app,ui}.py
src/nova/engine/{base,ollama,groq,gemini,openai}.py
src/nova/agents/{__init__,react}.py
src/nova/tools/{__init__,files,shell,system}.py
src/nova/memory/{__init__,store,kb}.py
src/nova/learning/__init__.py
```

## Package root

**`src/nova/__init__.py`** — version banner only: `__version__ = "3.0.0"`, which `nova
--version` and the chat banner print. Keeping it in one place is what lets `pyproject.toml`
and the CLI agree on the version string.

**`src/nova/__main__.py`** — 8 lines that make `python -m nova` work without installing
anything, by delegating to `cli.app.main`. The tests use this as their launch path, which
is how the suite runs against the source tree instead of an installed copy.

## Configuration

**`src/nova/config.py`** (113 lines) — every path, the `.env` reader and the settings file.
`_find_home()` (:23) walks up from the cwd looking for a project marker, so `nova` behaves
the same whether you launch it from the repo root or a subdirectory; `NOVA_HOME` (:30) and
`NOVA_WORKSPACE` (:32) let a caller relocate state, which is exactly how the tests get an
isolated sandbox. `load_env()` (:45) reads `.env` from three candidate locations and never
overwrites a variable that already exists — your real shell environment wins over a stale
file. Settings are `DEFAULTS` (:10) → `.nova/settings.json` (:80) → process `OVERRIDES`
(:100); `override()` is what `--engine/--mode/--max-steps` write to, so a flag changes this
run without silently rewriting the user's saved preferences. `api_key_present()` (:106) and
`mask()` (:110) exist so nothing downstream has to handle a raw secret to report whether one
is set.

## Intelligence (the prompt contract)

**`src/nova/intelligence.py`** (132 lines) — the only module that defines what Nova *promises*
to do. `PERSONA` (:13) forbids inventing results; `ACTION_GRAMMAR` (:18) demands exactly one
JSON object per reply. `build_system_prompt()` (:33) assembles persona + grammar + the live
tool block + workspace + memory. `history_block()` (:42) renders the transcript. The parsing
trio is where the robustness lives: `extract_json()` (:52) tolerates fences and prose,
`normalise_action()` (:77) accepts the variants small models emit (`tool`, `reasoning`, bare
`message`), and `parse_reply()` (:96) returns `(action, args, thought, error)` with a prose
fallback so a chatty model produces an answer rather than an infinite retry loop.
`validate_python()` (:107) is a real `ast.parse` check — line-accurate syntax errors,
top-level function names, `eval`/`exec`/`compile`/`__import__` usage — with no model in the
loop, which is why `nova validate` can be trusted.

## Engine (model transport)

**`src/nova/engine/base.py`** (125 lines) — the `Engine` ABC (`probe`, `complete`,
`list_models`, `is_local`, `priority`) plus the shared HTTP layer. `scrub()` (:20) rewrites
`?key=`, `Bearer`, `AIza…`, `sk-…`, `gsk_…`, and `EngineError.__str__` (:16) applies it
automatically, so a leak would have to bypass the exception type itself.
`is_transient()` (:35) + `TRANSIENT_MARKERS` (:32) encode the retry policy: 429/5xx/
"high demand"/"rate limit"/"timed out"/"cannot reach" are worth another attempt; everything
else is a configuration error and switching is better than waiting. `post_json()` (:83) turns
every transport exception into a scrubbed `EngineError` and appends an actionable hint per
status code (404 → `nova engine models`, 401 → check `.env`, 429 → wait or switch).

**`src/nova/engine/ollama.py`** (60 lines) — local priority 1. `probe()` (:30) distinguishes
the two different problems you can have with Ollama and says which: daemon unreachable vs
running with no model pulled (message names the exact `ollama pull` command). `_pick()` (:41)
prefers llama/mistral/gemma/qwen families when no model is configured, so a fresh install
finds something sane on its own. `complete()` (:48) uses `/api/chat` non-streaming with the
temperature the agent asked for.

**`src/nova/engine/groq.py`** (42) and **`openai.py`** (42) — OpenAI-compatible chat
completions, priorities 2 and 4. They exist as thin siblings so a third Open-shaped provider
is a copy-and-edit, not a new abstraction.

**`src/nova/engine/gemini.py`** (58) — priority 3, and the one that does *not* speak the
OpenAI shape: `complete()` (:36) maps the message list onto `generateContent` with a
`systemInstruction` part and `role: user/model` alternation. Reads `GEMINI_API_KEY` or
`GOOGLE_API_KEY` (:19). `list_models()` (:26) is why `nova engine models gemini` works — the
other cloud engines don't offer a listing that reflects what your key can actually use.

**`src/nova/engine/__init__.py`** (141) — the registry. `FACTORIES` (:17) is the one place a
new engine is added. `select()` (:43) returns the first engine that probes; `complete()` (:66)
pins the active engine first, retries transient failures via `_attempt()` (:91, 3 tries,
linear 4 s/8 s backoff), then fails over; `models()` (:104) and `status()` (:111) feed
`nova engine models` and `nova doctor`. `exhausted_message()` (:62) builds the per-engine
"why not" list rather than a generic failure.

## Agents

**`src/nova/agents/__init__.py`** (47) — the two ways Nova answers. `answer()` (:21) is
single-shot, memory-aware, tool-free (`nova ask`), and explicitly tells the model it is not
calling tools this turn so it doesn't emit a JSON action at you. `looks_like_action()` (:43)
+ `ACTION_CUES` (:14) drive the REPL's routing decision — imperative verbs start an agent
run, a question stays in `answer()`, and anything ending in `?` is a question regardless.

**`src/nova/agents/react.py`** (186) — the loop, described step by step in
[walkthrough.md](walkthrough.md). `AgentOutcome` (:18) is the machine-readable result
(`as_dict()` at :29 is what `--json` prints and tests assert on). `run()` (:66) enforces
three early exits — no engine, no valid protocol after retries, step budget — so a stuck
model cannot spend your time forever. `_messages()` (:140) rebuilds the prompt every step
from real observations; `_observe()` (:150) is the only place a tool is executed, and it
routes through `call_gated()`; `format_observation()` (:179) compacts results to ~1.4 KB with
an explicit `[+N chars]` marker so a small model knows it is holding an excerpt.

## Tools

**`src/nova/tools/__init__.py`** (175) — the registry and the chokepoint. `Tool` (:16)
carries `name, description, handler, params, risk, requires, example`; `available` (:26) is a
`find_spec` check, so a missing optional dependency becomes "needs `pip install psutil`"
instead of an ImportError deep in a run. `prompt_block()` (:87) renders only the *available*
tools into the system prompt — a tool the model can't use shouldn't be advertised to it.
`call()` (:91) validates required args, times the handler, converts every exception into
`{"ok": False, "error": ...}`, and stamps `_ms`/`_tool`. `call_gated()` (:117) is the only
entry the agent and skills use: gate first, handler second, and a denial returns before the
handler is ever touched. `build_registry()` (:147) declares the 15 filesystem/host/exec tools
and `_memory_tools()` (:133) adds 6 memory tools — 21 total, each labelled
`read`/`write`/`exec`/`destructive`.

**`src/nova/tools/files.py`** (203) — the sandbox. `resolve()` (:26) computes
`{path, inside, exists, rel}` and never raises; `_guard()` (:41) refuses anything outside
`config.WORKSPACE` unless `allow_outside=true`, and it runs *before* any existence probe so
the error text cannot be used to map your disk. `require_exists()` (:50) is separate for the
same reason. On top of those three: `list_dir` (:55, capped, recursive option), `read_file`
(:80, byte-capped), `write_file` (:97, append mode), `make_dir` (:110), `move_path` (:117),
`delete_path` (:129, refuses the workspace root itself), `find_files` (:143),
`search_content` (:159), `workspace_info` (:191).

**`src/nova/tools/shell.py`** (61) — three `exec`-risk tools behind one `_run()` (:14) that
clamps the timeout to 1..600 s, captures stdout/stderr separately, and reports a kill on
timeout as `timed out after {n}s (killed)` rather than a partial success. `run_command()`
(:44) uses `shell=True` because agents need pipes and `&&`, which is precisely why it is
`exec` risk and gated; `run_python` (:50) and `run_python_file` (:56) spawn `python -B` with
`PYTHONWARNINGS=ignore` so warnings don't pollute observations.

**`src/nova/tools/system.py`** (78) — read-only host facts. `system_info()` (:13) returns
plain `platform`/`os` data and adds psutil fields only when psutil is importable, setting
`psutil: false` rather than lying; `top_processes()` (:44) returns an explicit error naming
`pip install psutil` instead of an empty list; `environment()` (:60) reports which API keys
are set (booleans only) and which optional libs exist — this is what the `engine_status` tool
hands to the agent.

## Security

**`src/nova/security.py`** (127) — the gate. `RISK_ORDER` (:16) is the ladder
`read(0) → write(1) → exec(2) → destructive(3)`. `HARD_BLOCKS` (:18) is a regex list checked
against `summarize()` (:107) output, and it is evaluated before mode is ever consulted, so
`yolo` cannot delete a drive root, `mkfs`, fork-bomb, `shutdown /f /t 0` or pipe `curl` into
a shell. `review()` (:63) is the ordered decision (see walkthrough). `interactive` (:45) is
captured once from `sys.stdin.isatty()`, and `_prompt()` (:88) marks the gate
non-interactive on `EOFError`, so a piped or CI run denies instead of hanging — and note the
Windows quirk: `isatty()` is True even for `stdin=DEVNULL`, which is why the EOF path exists
at all. `default_mode()` (:120) resolves `--mode` → `NOVA_YOLO=1` → saved settings → `ask`.

## Memory

**`src/nova/memory/store.py`** (104) — durable facts and task history in one JSON file.
`_load()` (:17) returns an empty structure on a corrupt or missing file rather than raising,
so one bad write never bricks the agent; `recall()` (:38) returns similar keys when you guess
a name wrong; `log_task()` (:66) appends a compact per-run record capped at the last 500;
`stats()` (:85) computes the success rate the CLI prints.

**`src/nova/memory/kb.py`** (119) — structured knowledge in SQLite: `knowledge(category,key)`
unique rows and `snippets`. Values are JSON-encoded on the way in (`store()`, :44) and
`_decode()`d (:105) on the way out, so a dict round-trips without a schema migration.
`search()` (:65) is a deliberate `LIKE` scan — no FTS5 dependency, honest about being a
substring search.

**`src/nova/memory/__init__.py`** (32) — `context_block()` (:11) is the entire interface to
the model: KNOWN FACTS (12 keys, 120 chars each), RECENT TASKS (3), RELATED NOTES (4 hits for
the current goal), capped at 1200 chars. That cap is a design decision — memory that grows
unbounded eventually leaves no room for the transcript, and the agent silently gets worse.

## Learning

**`src/nova/learning/__init__.py`** (96) — `TraceLog`. `new_session()` (:24) makes a sortable
`YYYYMMDD-HHMMSS-xxxxxx` id; `record()` (:27) appends one JSONL row per event and `ensure_dirs()`
first so logging can't fail on a fresh install; `_shrink()` (:81) truncates any string field
over 800 chars; `read()` (:42) skips unparseable lines instead of dying on a half-written row;
`stats()` (:58) aggregates sessions, tool success rate, average and worst latency, most-used
tools, top errors and engines used. The module docstring states what this is *not*: Nova does
not fine-tune from traces, and no code pretends otherwise.

## Skills

**`src/nova/skills.py`** (128) — deterministic, replayable step sequences stored in
`.nova/skills.json`. `add()` (:62) saves `[{"action","args"}]` steps; `run()` (:92) fills
`{param}` placeholders (`_fill()`, :114), executes each step through the same
`call_gated()` the agent uses — so a skill cannot out-privilege the current mode — and stops
at the first failure with `failed_at` plus per-step detail. A seeded skill means
`nova skills run workspace_audit` works with **no engine at all**, which is why the offline
smoke test can prove the tool layer end to end.

## CLI

**`src/nova/cli/app.py`** (654) — the command surface. `_global_parser()` (:26) with
`SUPPRESS` defaults, `build_parser()` (:39) for subcommands, `normalise()` (:91),
`apply_globals()` (:102), `make_gate()` (:112), one `cmd_*` per subcommand, `DISPATCH` (:617)
and `main()` (:633) with fixed exit codes. `cmd_doctor()` (:403) is the diagnostic surface:
engines, dependency state, env files found, sandbox root. `cmd_chat()` (:505) is the REPL,
`_slash()` (:552) its commands, and `HELP_TEXT` (:493) the in-shell reference.

**`src/nova/cli/ui.py`** (161) — all printing. `force_utf8()` (:21) prevents
`UnicodeEncodeError` on Windows codepages. `_fit()` (:80) allocates table column widths
against the real terminal budget, respecting per-column floors down to the header width, and
`kv()` (:94) renders with `rich` when present or a plain fixed-width fallback when not — same
numbers either way. `result()` (:129) handles `--json` so machine output is never polluted by
colour codes or wrapping.

## Optional extras

**`src/nova/voice.py`** (124) — off by default and honest when absent. `providers()` (:14)
probes pyttsx3 / edge-tts / soprano for TTS and whisper / speech_recognition for STT;
`say()` (:60) reports the *exact* missing piece — including the case where edge-tts can
synthesise but no player exists, and the case where whisper is installed but `sounddevice`
isn't. Nothing here is required by any other module.

## Tests

`tests/conftest.py` inserts `src/` on `sys.path` and provides the `sandbox` fixture that
points every state path, `config.OVERRIDES`, and each module-level singleton (`_store`, `_db`,
`_log`, `_registry`) at a throwaway `tmp_path` — that is why the suite is order-independent and
writes nothing into your real `.nova/`.

| file | covers |
|------|--------|
| `test_intelligence.py` | JSON extraction, fenced/embedded/flat replies, prose fallback, prompt assembly, AST validation |
| `test_engine.py` | priority selection, failover, transient retry vs permanent failure, forced engine, status, `scrub`, actionable messages |
| `test_tools_gate.py` | sandbox round-trips, escape refusal, flag-and-approval pairing, deny/yolo/non-interactive, hard blocks, session grants, read tools never prompt, shell capture, destructive labels, unknown tool/missing args |
| `test_memory_skills.py` | fact and knowledge round-trips, context block feeding the prompt, skills running without an LLM, missing params, gate denial mid-skill, trace aggregation and dirty-file tolerance |
| `test_cli.py` | subprocess runs against `python -m nova` with keys stripped: help/version/tables, write requiring yolo, `NOVA_YOLO`, session flags not persisting, escape blocked, hard block, doctor honesty with no engine, memory + skills + traces JSON, validate, REPL `quit` |

## Non-code directories

**`docs/`** — [architecture.md](architecture.md) (layers and data flow),
[walkthrough.md](walkthrough.md) (one command end to end), this map.

**`scripts/`** — `local_setup.ps1` (start/verify Ollama, pull a model, switch config to
`engine=ollama`, smoke-test it) and `smoke.ps1` (12 offline CLI checks with expected exit
codes, then the full pytest run unless `-Quick`). Both are single-line-runnable from
PowerShell and neither installs anything without asking.

**`Config/Modelfile.nova`** — an Ollama model definition that bakes the persona and the
one-JSON-object rule into a local model. It deliberately does *not* list tools: the registry
generates that block at runtime, so a frozen list could only go stale or invite the model to
invent actions.

**`workspace/`** — the default sandbox, gitignored. **`.nova/`** — settings, memory,
knowledge DB, traces, log; gitignored, and the reason you can delete it at any time to start
over.
