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
| `llama` | 1        | `llama-server` running with a GGUF loaded |
| `ollama`| 2        | `ollama serve` running + one pulled model |
| `hf`    | 3        | `HF_TOKEN` + Inference Providers credit |
| `groq`  | 4        | `GROQ_API_KEY`               |
| `gemini`| 5        | `GEMINI_API_KEY`             |
| `openai`| 6        | `OPENAI_API_KEY`             |

```powershell
Copy-Item .env.example .env
notepad .env
nova doctor
```

`nova doctor` prints per-engine readiness, which tools are missing dependencies, and where
state lives. Exit code `3` means no engine is reachable. Keys are read from the environment
or `.env` (`GEMINI_API_KEY` / `GOOGLE_API_KEY`, `GROQ_API_KEY`, `OPENAI_API_KEY`, `HF_TOKEN`;
plus `NOVA_HOME`, `NOVA_WORKSPACE`, `LLAMA_CPP_URL`, `LLAMA_CPP_MODEL`, `LLAMA_CPP_MAX_TOKENS`,
`OLLAMA_URL`, `OLLAMA_MODEL`, `HF_MODEL`,
`HF_MAX_TOKENS`, `NOVA_YOLO`) and never written to logs; error strings are scrubbed of
`?key=`, `Bearer`, `AIza…`, `sk-…`, `gsk_…` and `hf_…` before they reach your terminal.

```powershell
nova engine list
nova engine models gemini          # what your key actually allows
nova config set gemini_model gemini-2.5-flash
nova engine test explain recursion in three lines
```

### Run a GGUF from Hugging Face on your own hardware

Priority 1 is a local `llama-server` holding one GGUF file: the weights come off the Hugging Face
Hub, then inference is yours - no key, no quota, nothing metered. Three commands, each on one line:

```powershell
Invoke-WebRequest -Uri https://github.com/ggml-org/llama.cpp/releases/download/b12098/llama-b12098-bin-win-cpu-x64.zip -OutFile llama.zip
Expand-Archive llama.zip -DestinationPath llama.cpp
.\llama.cpp\llama-server.exe -hf unsloth/Qwen3-4B-Instruct-2507-GGUF:Q4_K_M --host 127.0.0.1 --port 8080
```

Then, in a second window:

```powershell
nova engine use llama
nova ask what is in my workspace
```

`Q4_K_M` of a 4B model is 2.5 GB - the quant picked for 6 GB of VRAM with 16 GB of RAM. Swap in any
other GGUF with `--model path\to\file.gguf`, or grab the CUDA build
(`llama-b12098-bin-win-cuda-12.4-x64.zip`) for GPU offload on NVIDIA. The build number in the URL
comes from the llama.cpp releases page and changes with every release; Nova reads the model id the
server is actually hosting, so nothing else needs configuring.

### Fully local, no API key

Nova prefers the local engines (`llama`, then `ollama`), so a machine with no keys at all is the
normal configuration, not the fallback. One script does the whole Ollama setup - it checks Ollama is
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
| `nova skills list \| show <name> \| run <name> key=value \| add \| import <file.toml\|dir> \| rm` | replayable step sequences, with one optional model step |
| `nova traces stats \| recent [n] \| session <id>` | what the agent actually did, step by step |
| `nova doctor` | engines, tools, voice and state report |
| `nova voice status \| on \| off \| say <text> \| listen` | optional speech, honest errors when a dependency is missing |
| `nova config show \| set <key> <value> \| paths` | settings and file locations |
| `nova validate <file.py>` | AST check: syntax errors, function names, risky calls |
| `nova serve [--host H] [--port P]` | HTTP API: `POST /agent` and `GET /health`, read-only agent |

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

## Serve it over HTTP

`nova serve` is the same agent behind `nova go` with a network face: stdlib `http.server`,
two endpoints, no new dependency.

| endpoint | what it does |
|----------|--------------|
| `GET /health` | service, version, the engine selected so far, whether a token is required. Unauthenticated, so a platform health check can reach it - and it reports *configuration*, not engine liveness, because a slow model must not fail a health check and get the instance recycled. |
| `POST /agent` | `{"goal": "...", "max_steps": 5}` returns the agent's own dict: `ok`, `final`, `steps`, `engine`, `tools_used`, `denials`, `trace_session`, `ms` |

Two differences from the CLI, both deliberate:

- **Nothing above `read` runs.** The gate is pinned to `deny`, so `write_file`, `run_command`
  and `delete_path` come back inside `denials` instead of touching the disk. There is no
  terminal to type `y` into, so the server never pretends one exists.
- **`allow_outside` is stripped.** Locally that flag is how you point Nova at `~/Downloads`;
  over HTTP it would be a way to read any file on the host. `ServedRegistry` drops the
  argument before the tool sees it, which makes the workspace a wall rather than a default.

`NOVA_API_TOKEN` switches on `Authorization: Bearer <token>` for `/agent`. With no token set
the server binds loopback only, and `nova serve --host 0.0.0.0` refuses to start rather than
come up open.

```powershell
$env:NOVA_API_TOKEN = "a-long-random-string"
python -B -m nova serve --port 8000
Invoke-RestMethod -Uri http://127.0.0.1:8000/health
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/agent -Headers @{Authorization = "Bearer $env:NOVA_API_TOKEN"} -ContentType "application/json" -Body '{"goal":"list the files in the workspace","max_steps":5}'
```

The answer is only as good as the model behind it: that call returns
`"There is 1 file in the workspace: study-plan.md."` because the agent called `list_dir`
first, and `tools_used` in the payload is how you check it did.

### Docker and Render

`Dockerfile` and `render.yaml` build **one image** that carries Nova and the CPU-only
llama.cpp binaries (23 MB), so the same deploy works with or without a local brain:

| `NOVA_GGUF` | the brain | what it needs |
|-------------|-----------|---------------|
| empty (the `render.yaml` default) | a hosted key — `GROQ_API_KEY` or `GEMINI_API_KEY` | runs on Render's `free` plan: 0.1 CPU / 512 MB, $0 |
| set, e.g. `unsloth/Qwen3-4B-Instruct-2507-GGUF:Q4_K_M` | `llama-server` starts inside the container and Nova talks to it on `127.0.0.1:8080` | ~2.5 GB of weights plus KV cache resident in RAM, so a paid plan: `1c-2g` ($25/mo) with a 1B model, `2c-4g` ($85/mo) with the 4B |

A GGUF cannot run on the free plan, and that is not a tuning problem — the weights have to be
in RAM before the first token, and Render's filesystem is ephemeral, so a spin-down discards
the download and the next boot pays it again. `free` also spins down after 15 idle minutes
(~1 min cold start) and the workspace gets 750 instance-hours a month, which one always-on
service fits inside and two do not. Render has **no GPU instances**, so a container GGUF is
CPU inference: the same 3-step goal that took 24 s on this laptop's 16 cores takes several
times that on one shared vCPU.

```powershell
docker build -t nova .
docker run -e NOVA_API_TOKEN=local-test -p 8000:10000 nova
Invoke-RestMethod -Uri http://127.0.0.1:8000/health
```

Rendering happens on Render's side: the Blueprint reads `render.yaml`, clones the repo and
builds this Dockerfile, so `main` has to be pushed to GitHub first. `NOVA_API_TOKEN` is
generated by Render; the engine key is marked `sync: false`, so Render prompts you for it once
in the dashboard and it never lands in the repo.

Pointing Nova at Hugging Face's hosted router is *not* a free path: Inference Providers is
metered and a free HF account carries no credit, so a `402` comes back named as such.

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
- `skills` are named step sequences that replay the same tools deterministically with no model
  call. A `think` step is the exception: it asks the engine once and passes its answer to the
  next step, which is how a skill does judgement ("is this lint report a bug or a style nit")
  that a fixed step list cannot. `nova skills add` records a sequence you repeat, and
  `nova skills import <folder>` reads OpenJarvis TOML packs - Nova imports the ones it can
  actually run and refuses the rest with the step number and the missing tool named.

## What is deliberately not here

v2 of this repo shipped a PyQt6 HUD, a Flask "remote access" server, a Bluetooth terminal,
mouse/keyboard "human action simulation", a `training_engine.py` that logged fake loss
curves, and a `self_optimization.py` that rewrote its own prompts. None of it worked as
described, so it was deleted rather than ported. Voice is the only non-text modality left
and it is opt-in, dependency-gated, and reports exactly which package is missing.

This also means Nova cannot open apps, click, type into other programs, or install
software. It edits files in its sandbox and runs commands you approve.

The HTTP server is new in 3.0 and is not a return of that Flask app: it is two endpoints, it
cannot write or execute, and it refuses to bind a public address without a token. Everything
it claims to do is covered in `tests/test_server.py`.

## Layout

| path | layer |
|------|-------|
| `src/nova/intelligence.py` | persona, action grammar, JSON reply parsing, Python AST validation |
| `src/nova/engine/` | `llama` (local GGUF), `ollama`, `hf`, `groq`, `gemini`, `openai` backends, priority failover, key scrubbing |
| `src/nova/agents/react.py` | the think-act-observe loop, step budget, tool transcript |
| `src/nova/tools/` | sandboxed files, shell/python execution, system info - 21 registered tools |
| `src/nova/memory/` | JSON fact store + SQLite knowledge base |
| `src/nova/learning/` | JSONL trace log and aggregate stats |
| `src/nova/security.py` | risk labels, modes, hard blocks, prompts |
| `src/nova/server.py` | `nova serve`: stdlib HTTP, `GET /health` + `POST /agent`, read-only gate |
| `src/nova/skills.py`, `src/nova/voice.py`, `src/nova/config.py` | replayable sequences, optional speech, paths and settings |
| `src/nova/cli/` | argument parsing and terminal rendering |
| `docs/` | [architecture](docs/architecture.md), [walkthrough](docs/walkthrough.md), [module map](docs/modules.md) |
| `scripts/` | [local_setup.ps1](scripts/local_setup.ps1), [smoke.ps1](scripts/smoke.ps1), [docker-entrypoint.sh](scripts/docker-entrypoint.sh) |
| `Dockerfile`, `render.yaml` | the `nova serve` image (Nova + CPU llama.cpp) and the Render Blueprint that deploys it |
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

Start at `src/nova/cli/app.py:662` (`main`) and `src/nova/agents/react.py:67` (`run`). The
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
