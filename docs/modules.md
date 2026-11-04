# Nova module map

One entry per file. Each says what the module owns, the names you should actually look for,
and the failure mode it was written to prevent. Paths are relative to the repo root.

```text
src/nova/{__init__,__main__,config,intelligence,security,server,skills,voice}.py
src/nova/cli/{app,ui}.py
src/nova/engine/{base,llamacpp,ollama,huggingface,groq,gemini,openai}.py
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

**`src/nova/config.py`** (131 lines) — every path, the `.env` reader and the settings file.
`_find_home()` (:28) walks up from the cwd looking for a project marker, so `nova` behaves
the same whether you launch it from the repo root or a subdirectory; `NOVA_HOME` (:35) and
`NOVA_WORKSPACE` (:37) let a caller relocate state, which is exactly how the tests get an
isolated sandbox and how the container gets its own. `load_env()` (:58) reads `.env` from
three candidate locations and never overwrites a variable that already exists — your real
shell environment wins over a stale file. Settings resolve through `get()` (:107) in a fixed
order — `OVERRIDES` (:55) from a flag, then the environment for the keys named in
`ENV_SETTINGS` (:45) (`LLAMA_CPP_URL`, `LLAMA_CPP_MODEL`, `LLAMA_CPP_MAX_TOKENS`,
`OLLAMA_URL`, `OLLAMA_MODEL`, `HF_MODEL`, `HF_MAX_TOKENS`), then `.nova/settings.json` (:38),
then `DEFAULTS` (:10) — so a setup script or a platform can pin an endpoint without rewriting
anyone's saved preferences. `api_key_present()` (:124) and
`mask()` (:128) exist so nothing downstream has to handle a raw secret to report whether one
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

**`src/nova/engine/base.py`** (127 lines) — the `Engine` ABC (`probe`, `complete`,
`list_models`, `is_local`, `priority`) plus the shared HTTP layer. `scrub()` (:20) rewrites
`?key=`, `Bearer`, `AIza…`, `sk-…`, `gsk_…`, and `EngineError.__str__` (:16) applies it
automatically, so a leak would have to bypass the exception type itself.
`is_transient()` (:36) + `TRANSIENT_MARKERS` (:33) encode the retry policy: 429/5xx/
"high demand"/"rate limit"/"timed out"/"cannot reach" are worth another attempt; everything
else is a configuration error and switching is better than waiting. `post_json()` (:85) turns
every transport exception into a scrubbed `EngineError` and appends an actionable hint per
status code (404 → `nova engine models`, 401 → check `.env`, 429 → wait or switch).

**`src/nova/engine/llamacpp.py`** (81) — local priority 1: the Hugging Face GGUF that runs on
this machine rather than on someone's router. `probe()` (:39) separates the three states a
local server can be in — nothing listening (`START_HINT` (:16) names the `llama-server -hf
<repo>:<QUANT>` command that fixes it), listening but `no free slot` (weights still loading or
the context is busy, checked with `_listening()` (:56) so a half-started server is not reported
as absent), and ready — and on ready it adopts the served model id from `/v1/models`, so
`llama_model` is only needed when the server hosts several models. `complete()` (:63) posts the
OpenAI shape to `/v1/chat/completions` with `max_tokens` from config, and an empty reply says
which `finish_reason` came back instead of pretending the model answered.

**`src/nova/engine/ollama.py`** (60 lines) — local priority 2. `probe()` (:30) distinguishes
the two different problems you can have with Ollama and says which: daemon unreachable vs
running with no model pulled (message names the exact `ollama pull` command). `_pick()` (:41)
prefers llama/mistral/gemma/qwen families when no model is configured, so a fresh install
finds something sane on its own. `complete()` (:48) uses `/api/chat` non-streaming with the
temperature the agent asked for.

**`src/nova/engine/huggingface.py`** (92) — priority 3, and the reason Nova is not tied to
the laptop it was installed on: `POST https://router.huggingface.co/v1/chat/completions` with
`Authorization: Bearer HF_TOKEN`, OpenAI-shaped body and response, so no SDK and no local
weights. Model ids carry a provider policy suffix (`:fastest` default, `:cheapest`,
`:preferred`, or an exact provider) because the router serves one id through many hosts.
`probe()` (:36) fails before any socket opens when `HF_TOKEN` is missing and names the exact
fine-grained permission the token needs. `list_models()` (:43) reads `/v1/models` and, when
the router serves more than `MODEL_LIST_LIMIT` (:20) ids, sets `list_note` — which
`Registry.models()` passes through and `nova engine models hf` prints as a warning instead of
silently truncating the list. `_explain()` (:77) translates router status codes into actions:
401/403 → the token permission, 402 → "free Hugging Face accounts hold no Inference
Providers credit" plus `nova engine use ollama`, 404 → pick an id from
`nova engine models hf`, 429 → try `:cheapest`. An account with no credit is a billing fact,
so it is reported as one rather than retried or hidden behind a placeholder answer.

**`src/nova/engine/groq.py`** (42) and **`openai.py`** (42) — OpenAI-compatible chat
completions, priorities 4 and 6. They exist as thin siblings so a third Open-shaped provider
is a copy-and-edit, not a new abstraction.

**`src/nova/engine/gemini.py`** (58) — priority 5, and the one that does *not* speak the
OpenAI shape: `complete()` (:36) maps the message list onto `generateContent` with a
`systemInstruction` part and `role: user/model` alternation. Reads `GEMINI_API_KEY` or
`GOOGLE_API_KEY` (:19). `list_models()` (:26) is why `nova engine models gemini` works — the
other cloud engines don't offer a listing that reflects what your key can actually use.

**`src/nova/engine/__init__.py`** (148) — the registry. `FACTORIES` (:19) is the one place a
new engine is added. `select()` (:47) returns the first engine that probes; `complete()` (:70)
pins the active engine first, retries transient failures via `_attempt()` (:95, 3 tries,
linear 4 s/8 s backoff), then fails over; `models()` (:108) and `status()` (:116) feed
`nova engine models` and `nova doctor`. `exhausted_message()` (:66) builds the per-engine
"why not" list rather than a generic failure.

## Agents

**`src/nova/agents/__init__.py`** (53) — the two ways Nova answers. `answer()` (:25) is
single-shot, memory-aware, tool-free (`nova ask`), and explicitly tells the model it is not
calling tools this turn so it doesn't emit a JSON action at you. `looks_like_action()` (:47)
+ `ACTION_CUES` (:14) drive the REPL's routing decision — an imperative verb starts an agent
run and a plain question stays in `answer()`. `POLITE_PREFIXES` (:22) are stripped before
matching, because "can you arrange my downloads" is an instruction wearing a question's
clothes; without that strip the model answers "I have no access to your files" while the
tools it never reached do have access. A trailing `?` only wins on a line that was not
polite-prefixed.

**`src/nova/agents/react.py`** (283) — the loop, described step by step in
[walkthrough.md](walkthrough.md). `AgentOutcome` (:19) is the machine-readable result
(`as_dict()` at :30 is what `--json` prints and tests assert on). `run()` (:67) enforces
three early exits — no engine, no valid protocol after retries, step budget — so a stuck
model cannot spend your time forever. `_messages()` (:207) rebuilds the prompt every step
from real observations, and in the last three steps adds `STEPS LEFT: n` telling the model an
observation that starts `OK` already holds the data; `_observe()` (:225) is the only place a
tool is executed, it routes through `call_gated()`, and a denial there names the read-only
tools that still work instead of advice the model cannot act on; `_signature()` (:260) is the
anti-loop memory — the same call twice gets one more try, the third is answered with
`REPEAT BLOCKED` without touching the handler, and a tool that fails twice for the *same*
reason is closed for the run with `TOOL BLOCKED`; `_salvage()` (:177) spends one tool-free
call on an answer from the transcript when the budget runs out, and throws it away if the
model used it to ask for another tool; `format_observation()` (:265) leads with the numeric
fields (`lines=7, size=146 …`), compacts the body to ~1.4 KB and appends an explicit
`[+N chars]` marker so a small model knows it is holding an excerpt.

## Tools

**`src/nova/tools/__init__.py`** (183) — the registry and the chokepoint. `Tool` (:20)
carries `name, description, handler, params, risk, requires, example`; `available` (:30) is a
`find_spec` check, so a missing optional dependency becomes "needs `pip install psutil`"
instead of an ImportError deep in a run. `OPTIONAL_PARAMS` (:16) is the single list of args a
handler can do without, and `Tool.required` (:34) is params-minus-that-list — the skill
importer and the call path ask the same question, so they cannot disagree about what a step
owes. `prompt_block()` (:95) renders only the *available*
tools into the system prompt — a tool the model can't use shouldn't be advertised to it.
`call()` (:99) validates required args, times the handler, converts every exception into
`{"ok": False, "error": ...}`, and stamps `_ms`/`_tool`. `call_gated()` (:125) is the only
entry the agent and skills use: gate first, handler second, and a denial returns before the
handler is ever touched. `build_registry()` (:155) declares the 15 filesystem/host/exec tools
and `_memory_tools()` (:141) adds 6 memory tools — 21 total, each labelled
`read`/`write`/`exec`/`destructive`.

**`src/nova/tools/files.py`** (246) — the sandbox. `resolve()` (:41) computes
`{path, inside, exists, rel}` and never raises; `_guard()` (:56) refuses anything outside
`config.WORKSPACE` unless `allow_outside=true`, and it runs *before* any existence probe so
the error text cannot be used to map your disk. `require_exists()` (:65) is separate for the
same reason. On top of those three: `list_dir` (:89, capped, recursive option), `read_file`
(:123, byte-capped and reporting `lines`), `write_file` (:140, append mode), `make_dir` (:153),
`move_path` (:160), `delete_path` (:172, refuses the workspace root itself),
`find_files` (:186), `search_content` (:202), `workspace_info` (:234).

`list_dir` answers "what is in here" twice: `_histogram()` (:73) folds the entries into
`by_ext=pdf=9, docx=7, …` and a space-joined `names` field, both placed *ahead* of the
`entries` list. That ordering is the point — `format_observation()` clips to ~1.4 KB, so a
200-file folder used to reach the model as a clipped list of dicts. It then invents a name
(`report.pdf` when the file is `report1.pdf`), the move fails, and it retries the same
invented name. Counts and names now survive the clip.

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

**`src/nova/skills.py`** (284) — named, replayable step sequences stored in
`.nova/skills.json`. `add()` (:92) saves `[{"action","args"}]` steps; `run()` (:122) fills
`{param}` placeholders (`_fill()`, :177), executes each step through the same
`call_gated()` the agent uses — so a skill cannot out-privilege the current mode — and stops
at the first failure with `failed_at` plus per-step detail. A `think` step (`MODEL_STEP` :16,
`think()` :160) is the one step that is not deterministic: it makes a single model call and its
answer is threaded into later steps through `output_key` (`_thread()` :187, clipped at
`STEP_OUTPUT_LIMIT` = 1500 so a small local context still holds the chain). A seeded skill means
`nova skills run workspace_audit` still works with **no engine at all**, which is why the offline
smoke test can prove the tool layer end to end.

`parse_pack()` (:207) turns an OpenJarvis TOML pack (`[skill]` + `[[skill.steps]]`) into either
runnable Nova steps or the exact reasons it cannot run. `TOOL_ALIASES` (:20) maps the eight
names that do have a Nova equivalent and `ARG_ALIASES` (:30) renames their arguments;
`NO_NOVA_EQUIVALENT` (:34) refuses the four that do not (`web_search`, `http_request`,
`pdf_extract`, `memory_index`) rather than quietly dropping the step; `POSIX_ONLY` (:42) catches
shell steps that cmd.exe cannot run; and a step that is never given a `Tool.required` argument is
refused too. `_placeholders()` (:202) subtracts the declared `output_key`s from the `{...}` names,
so only genuine inputs surface as `params`. `import_pack()` (:265) writes a pack only when
`problems` is empty — a half-imported skill is worse than a refused one — and `import_dir()` (:276)
reports `imported` plus `refused {name: [reasons]}` for a whole folder.

## HTTP surface

**`src/nova/server.py`** (214) — `nova serve`, and the only face of Nova a stranger can reach.
Stdlib `ThreadingHTTPServer`, no framework, `GET /health` + `POST /agent`. What matters here is
what the agent behind `POST /agent` is *not* allowed to do, and it is not allowed by
construction rather than by policy:

- `read_only_gate()` (:45) builds `PermissionGate(mode="deny", auto_risk=READ,
  interactive=False)`, so step 4 of `review()` refuses anything above `read` and there is no
  terminal to ask in. A network caller cannot make Nova write, move, delete or execute.
- `ServedRegistry` (:50) subclasses the real registry and strips `allow_outside` from every
  call before `super().call_gated()`. That argument is the gate-approved escape hatch on the
  CLI (`--workspace ~/Downloads` uses it), and it is accepted through `**args`, so removing it
  at the signature would not have removed it. Without this override, a "read-only" agent could
  read any file the process user can see.
- `build_server()` (:179) raises `ServerConfigError` (:32) when the bind address is not in
  `LOCAL_HOSTS` (:29) and `NOVA_API_TOKEN` (:36) is unset — the server refuses to come up open
  instead of coming up and hoping nobody looks. `authorized()` (:100) compares the bearer
  token with `hmac.compare_digest`, and `cmd_serve()` (cli/app.py:511) turns the config error
  into exit 2 with the fix in the message.
- `agent_request()` (:84) caps the goal at `MAX_GOAL_CHARS` and the steps at `MAX_STEPS` (:28)
  and `_read_body()` caps the payload at `MAX_BODY_BYTES` (:26), because one HTTP request that
  starts 500 model calls is a denial of service against yourself on a paid plan.
- `health()` (:69) reports configuration, not engine liveness. A platform that polls
  `/health` and sees a failure recycles the instance — and an instance that is still
  downloading 2.5 GB of GGUF weights *is* slow, which is not the same as broken.

## CLI

**`src/nova/cli/app.py`** (683) — the command surface. `_global_parser()` (:26) with
`SUPPRESS` defaults, `build_parser()` (:39) for subcommands, `normalise()` (:95),
`apply_globals()` (:106), `make_gate()` (:116), one `cmd_*` per subcommand, `DISPATCH` (:645)
and `main()` (:662) with fixed exit codes. `cmd_doctor()` (:421) is the diagnostic surface:
engines, dependency state, env files found, sandbox root. `cmd_skills()` (:319) replays a skill
and `import`s a TOML pack or folder, returning exit 1 with the refusal reasons rather than
importing a skill that cannot run. `cmd_serve()` (:511) delegates to `server.serve()` and only
handles the refusal message. `cmd_chat()` (:533) is the REPL,
`_slash()` (:580) its commands, and `HELP_TEXT` (:521) the in-shell reference.

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
| `test_engine.py` | priority selection, failover, transient retry vs permanent failure, forced engine, status, `scrub`, actionable messages, `HF_TOKEN` gate, router 402/401 wording, GGUF server states (absent vs busy vs ready) and the OpenAI-shaped local call, env and flag precedence for engine settings |
| `test_agent_loop.py` | the ReAct loop against a scripted engine: repeat blocked on the third identical call, different args not treated as a repeat, a tool closed after two same-reason failures, budget pressure in the prompt, `final` termination, unknown tool as observation, observation shape, salvage answer when steps run out |
| `test_tools_gate.py` | sandbox round-trips, escape refusal, flag-and-approval pairing, deny/yolo/non-interactive, hard blocks, session grants, read tools never prompt, shell capture, destructive labels, unknown tool/missing args |
| `test_memory_skills.py` | fact and knowledge round-trips, context block feeding the prompt, skills running without an LLM, missing params, gate denial mid-skill, a `think` step fed by the previous step's output, dead-engine failure reported in the skill's own words, threading clip, TOML pack parsing, whole-pack refusal, directory import, trace aggregation and dirty-file tolerance |
| `test_server.py` | a real socket on an ephemeral port with a scripted engine: health shape and what it advertises, a read tool answered over HTTP, a write goal denied and the file proven absent on disk, `allow_outside` stripped (secret never in the response, sandbox refusal visible in the next prompt), step budget honoured, wrong token 401 before the agent runs, missing goal / non-JSON body / `max_steps` above the cap each a 400, unknown path 404, public bind without a token raises and names `NOVA_API_TOKEN`, loopback default needs no token, `read_only_gate` decisions per risk, and the served registry vs the local one on the same escape attempt |
| `test_cli.py` | subprocess runs against `python -m nova` with keys stripped: help/version/tables, write requiring yolo, `NOVA_YOLO`, session flags not persisting, escape blocked, hard block, doctor honesty with no engine, memory + skills + traces JSON, `skills import` accepting a pack and refusing one Nova cannot complete, `serve --host 0.0.0.0` with no token exiting 2, validate, REPL `quit` |

## Non-code directories

**`docs/`** — [architecture.md](architecture.md) (layers and data flow),
[walkthrough.md](walkthrough.md) (one command end to end), this map.

**`scripts/`** — `local_setup.ps1` (start/verify Ollama, pull a model, switch config to
`engine=ollama`, smoke-test it), `smoke.ps1` (12 offline CLI checks with expected exit
codes, then the full pytest run unless `-Quick`) and `docker-entrypoint.sh` (container start:
if `NOVA_GGUF` is set it launches `llama-server -hf …` in the background, then `exec nova
serve` — `exec` so the API is PID 1 and the platform's stop signal reaches it). The PowerShell
scripts are single-line-runnable and neither installs anything without asking; the shell
script is LF-forced by `.gitattributes`, because a CRLF shebang line does not execute in Linux.

**`Dockerfile` / `render.yaml` / `.dockerignore`** — the deploy path. The image is
`python:3.11-slim` plus the pinned CPU `llama-server` binary unpacked into `/opt/llama.cpp`
(`ADD <url>` unpacks the tar for us, `ld.so.conf.d` + `ldconfig` make its shared libraries
findable), Nova installed from the source tree, a non-root `nova` user owning `/app/workspace`
and `/app/.nova`, and no build keys in any layer — `.dockerignore` excludes `.env`, `.nova`,
`workspace/` and `tests/` so a real `GEMINI_API_KEY` cannot be baked into a published image.
`render.yaml` is the blueprint: `runtime: docker`, `plan: 2c-4g` (the cheapest tier that can
hold a 4B Q4 GGUF plus its context — Render has no GPU instances and the free tier is 0.1 CPU
/ 512 MB, which cannot load weights at all), `healthCheckPath: /health`, and
`NOVA_API_TOKEN` generated rather than stored in the repo.

**`Config/Modelfile.nova`** — an Ollama model definition that bakes the persona and the
one-JSON-object rule into a local model. It deliberately does *not* list tools: the registry
generates that block at runtime, so a frozen list could only go stale or invite the model to
invent actions.

**`workspace/`** — the default sandbox, gitignored. **`.nova/`** — settings, memory,
knowledge DB, traces, log; gitignored, and the reason you can delete it at any time to start
over.
