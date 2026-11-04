# NOVA 3.0 - a CLI agentic OS

Nova is a command-line agent that runs goals on your machine: it thinks one step at a
time, calls a real tool, reads the real result, and stops when the goal is done. There is
no GUI, no web dashboard, no "self-training" - one binary command, `nova`.

The layout follows the five primitives Stanford's OpenJarvis uses for a local-first
personal agent: **Intelligence, Engine, Agents, Tools & Memory, Learning**.

```text
nova go "summarise the files in my workspace and write notes/audit.md"
```

## Install

```powershell
python -m pip install -e .
```

That registers a `nova` command. If a `nova` launcher from another project is already on
your PATH (check with `Get-Command nova`), either uninstall it or run Nova as
`python -m nova ...` - the two install into the same Scripts folder.

Requirements: Python 3.10+, `requests`. Optional extras (`rich`, `system`, `voice`, `dev`):

```powershell
python -m pip install -e ".[rich,system]"
```

| extra    | gives you                                        |
|----------|--------------------------------------------------|
| `rich`   | tables, colours, box-drawing (plain text otherwise) |
| `system` | `psutil` for `top_processes` and system stats     |
| `voice`  | `pyttsx3` / `edge-tts` / `whisper` speech in/out  |
| `dev`    | `pytest` for the test suite                       |

## Point it at a model

Engines are tried local-first, then hosted; a dead engine fails over to the next one, and
rate-limits or 5xx responses are retried with backoff before the switch.

| engine  | priority | needs                        |
|---------|----------|------------------------------|
| `ollama`| 1        | `ollama serve` running + one pulled model |
| `hf`    | 2        | `HF_TOKEN` + Inference Providers credit |
| `groq`  | 3        | `GROQ_API_KEY`               |
| `gemini`| 4        | `GEMINI_API_KEY`             |
| `openai`| 5        | `OPENAI_API_KEY`             |

```powershell
Copy-Item .env.example .env
notepad .env
nova doctor
```

`nova doctor` prints per-engine readiness, which tools are missing dependencies, and where
state lives. Exit code `3` means no engine is reachable. Keys are read from the environment
or `.env` (`GEMINI_API_KEY` / `GOOGLE_API_KEY`, `GROQ_API_KEY`, `OPENAI_API_KEY`, `HF_TOKEN`;
plus `NOVA_HOME`, `NOVA_WORKSPACE`, `OLLAMA_URL`, `OLLAMA_MODEL`, `HF_MODEL`,
`HF_MAX_TOKENS`, `NOVA_YOLO`) and never written to logs; error strings are scrubbed of
`?key=`, `Bearer`, `AIza…`, `sk-…`, `gsk_…` and `hf_…` before they reach your terminal.

```powershell
nova engine list
nova engine models gemini          # what your key actually allows
nova config set gemini_model gemini-2.5-flash
nova engine test explain recursion in three lines
```

### Fully local, no API key

Nova prefers `ollama` (priority 1), so a machine with no keys at all is the normal
configuration, not the fallback. One script does the whole setup - it checks Ollama is
installed, starts the daemon if it isn't running, asks before downloading a model (~2 GB),
switches the config to local and smoke-tests it:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/local_setup.ps1
```

After that `nova ask`, `nova go` and `nova chat` work offline. `Config/Modelfile.nova` is
there if you want a purpose-built persona model:

```powershell
ollama create nova -f Config/Modelfile.nova
nova config set ollama_model nova
```

To check the install without a model at all, `scripts/smoke.ps1 -Quick` runs 12 offline CLI
checks (sandbox refusal, hard blocks, deny-on-pipe, skills replay, JSON output) plus the full
test suite when you drop `-Quick`.

### Any laptop, no model download

`hf` talks to Hugging Face's Inference Providers router, so the weights live on someone
else's hardware: a token is the whole install, and the same goal runs on a laptop that could
never hold a 3 GB model. Create a **fine-grained** token at
[huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) with the
*"Make calls to Inference Providers"* permission, then:

```powershell
Set-Item -Path env:HF_TOKEN -Value (Get-Clipboard)   # copy the token in the browser first
nova engine use hf
nova engine models hf          # the ids the router actually serves
nova go "summarise study-plan.md"
```

That variable lives in one shell. To keep it, put `HF_TOKEN=hf_...` in `.env` - Nova reads
it from disk only if the real environment does not already define it, and never logs it.

`nova engine models hf` is a real list, not a guess - the router only serves models with a
provider behind them, and the default id carries a policy suffix (`:fastest`, `:cheapest`,
`:preferred` or `:provider`) that picks which one answers.

One thing this cannot work around: **Inference Providers is metered, and a free Hugging Face
account has no included credit** (PRO adds $2/month, more is purchased pay-as-you-go). Nova
says so in those terms instead of hiding it - a `402` comes back as "this account has no
Inference Providers credit" plus the two ways forward, one of which is `nova engine use
ollama`. If you want hosted and free, `groq` has a no-cost tier and takes a key from
[console.groq.com/keys](https://console.groq.com/keys).

## Command surface

| command | what it does |
|---------|--------------|
| `nova` / `nova chat` | interactive shell - type a question for a direct answer, an instruction to run a goal, `/help` for slash commands |
| `nova ask <question>` | one question, no tools, no agent loop |
| `nova go <goal>` | ReAct agent: think, one tool call, observe, repeat until `final` |
| `nova go <goal> --first-step` | print step 1 only, then stop |
| `nova tools list \| show <name> \| schema <name> \| call <name> k=v` | inspect or invoke the registry directly |
| `nova engine list \| use <name> \| models [name] \| test <prompt>` | engine control |
| `nova memory show \| set <k> <v> \| get <k> \| del <k> \| search <text> \| note <cat> <k> <v> \| notes <cat> \| history \| stats` | facts, structured notes, task history |
| `nova skills list \| show <name> \| run <name> key=value \| add \| rm` | replayable deterministic step sequences, run without a model |
| `nova traces stats \| recent [n] \| session <id>` | what the agent actually did, step by step |
| `nova doctor` | engines, tools, voice and state report |
| `nova voice status \| on \| off \| say <text> \| listen` | optional speech, honest errors when a dependency is missing |
| `nova config show \| set <key> <value> \| paths` | settings and file locations |
| `nova validate <file.py>` | AST check: syntax errors, function names, risky calls |

Global flags work before or after the subcommand: `--engine`, `--mode`, `--yolo`,
`--workspace`, `--max-steps`, `--json`, `--quiet`. `--json` on any command prints
parseable output; `NOVA_YOLO=1` grants approval for a whole shell session.

```powershell
nova go "create a python package skeleton in demo/ with a test" --yolo --max-steps 15
nova tools call list_dir path=. recursive=true
nova skills run workspace_audit --json
nova traces recent 20
```

### Point it at a real folder

The sandbox *is* the workspace, so give Nova a folder by re-rooting it there rather than by
letting paths escape. Plan first, then let it act:

```powershell
nova go "sort the files into folders by file type" --workspace "$env:USERPROFILE\Downloads" --first-step
nova go "sort the files into folders by file type" --workspace "$env:USERPROFILE\Downloads"
```

The first line only prints step 1, so nothing moves. `list_dir` leads with `by_ext=pdf=9,
docx=7, …` and the plain file names, which is what lets the agent create `pdf/` and move
`report1.pdf` instead of a name it invented. In `ask` mode every `make_dir` and `move_path`
prompts, which on 28 files is a lot of keystrokes - run it on a copy first, or add `--yolo`
once the plan looks right.

## Permission model

Every tool carries a risk label, and the agent cannot skip the gate:

| risk | examples | default in `ask` mode |
|------|----------|-----------------------|
| `read` | `read_file`, `list_dir`, `search_content`, `system_info` | runs immediately |
| `write` | `write_file`, `make_dir`, `move_path`, `remember_fact` | prompts |
| `exec` | `run_command`, `run_python`, `run_python_file` | prompts |
| `destructive` | `delete_path` | prompts |

Modes: `ask` prompts per call (`y` once / `a` for the session / `n` deny), `yolo` approves
everything except the hard blocks, `deny` refuses anything above `read`.

Hard blocks survive `yolo`: recursive delete of a drive or filesystem root, `mkfs`,
`format c: /q`, `del /f /s C:\`, fork bombs, `shutdown /f /t`, and `curl … | sh`.

File tools are sandboxed to `workspace/`. A path that escapes the sandbox is refused unless
you pass `allow_outside=true` **and** approve the prompt. When stdin is not a terminal the
gate refuses rather than guessing, and says so: re-run with `--yolo`.

## Memory, traces and skills

- `memory` keeps key/value facts and task history in `.nova/memory.json`; structured notes
  and code snippets go to a SQLite knowledge base at `.nova/knowledge.db`.
- Before each goal the agent gets a context block of known facts, recent tasks and notes
  that match the request, so "remember I prefer tabs" changes later behaviour.
- `traces` writes one JSONL row per step (`.nova/traces.jsonl`): thought, tool,
  arguments, decision, duration, error. `nova traces stats` aggregates success rate, slowest
  tool and top errors. **Nova does not fine-tune a model from traces** - nothing in this
  repo trains anything, and the old modules that claimed to were removed.
- `skills` are named step sequences that run the same tools deterministically, offline, with
  no model call. `nova skills add` records a sequence you repeat.

## What is deliberately not here

v2 of this repo shipped a PyQt6 HUD, a Flask "remote access" server, a Bluetooth terminal,
mouse/keyboard "human action simulation", a `training_engine.py` that logged fake loss
curves, and a `self_optimization.py` that rewrote its own prompts. None of it worked as
described, so it was deleted rather than ported. Voice is the only non-text modality left
and it is opt-in, dependency-gated, and reports exactly which package is missing.

This also means Nova cannot open apps, click, type into other programs, or install
software. It edits files in its sandbox and runs commands you approve.

## Layout

| path | layer |
|------|-------|
| `src/nova/intelligence.py` | persona, action grammar, JSON reply parsing, Python AST validation |
| `src/nova/engine/` | `ollama`, `groq`, `gemini`, `openai` backends, priority failover, key scrubbing |
| `src/nova/agents/react.py` | the think-act-observe loop, step budget, tool transcript |
| `src/nova/tools/` | sandboxed files, shell/python execution, system info - 21 registered tools |
| `src/nova/memory/` | JSON fact store + SQLite knowledge base |
| `src/nova/learning/` | JSONL trace log and aggregate stats |
| `src/nova/security.py` | risk labels, modes, hard blocks, prompts |
| `src/nova/skills.py`, `src/nova/voice.py`, `src/nova/config.py` | replayable sequences, optional speech, paths and settings |
| `src/nova/cli/` | argument parsing and terminal rendering |
| `docs/` | [architecture](docs/architecture.md), [walkthrough](docs/walkthrough.md), [module map](docs/modules.md) |
| `scripts/` | [local_setup.ps1](scripts/local_setup.ps1), [smoke.ps1](scripts/smoke.ps1) |
| `tests/` | offline suite, subprocess CLI checks against `src/` |
| `workspace/`, `.nova/` | the sandbox and all runtime state - both gitignored |
| `Config/Modelfile.nova` | Ollama model definition if you want a local Nova persona |

## Reading the code

Three documents exist so you can understand the project without spelunking:

- **[docs/architecture.md](docs/architecture.md)** — the five primitives, the data flow, the
  permission ladder, what lives on disk and how to add a tool or an engine.
- **[docs/walkthrough.md](docs/walkthrough.md)** — one `nova go` followed step by step from
  `main()` through parsing, the gate, the sandbox and the trace log, with file:line links.
- **[docs/modules.md](docs/modules.md)** — one paragraph per file: what it owns and the
  failure mode it prevents.

Start at `src/nova/cli/app.py:636` (`main`) and `src/nova/agents/react.py:67` (`run`). The
package is a `src/` layout, so run it without installing with
`$env:PYTHONPATH = "src"` before any `python -m nova ...`.

## Tests

```powershell
python -m pytest
```

72 tests cover the gate (hard blocks, sandbox escape, session grants, non-TTY refusal),
the engine registry (failover, transient retry, key scrubbing), the reply parser,
memory, skills and the CLI end to end as a subprocess. They run offline: no API key is
required, and the CLI tests strip key variables from the child environment.
