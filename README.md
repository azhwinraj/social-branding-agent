# Social Branding Agent

> A web-based AI agent that drafts platform-specific posts for LinkedIn, X, and Medium from a single context input.

Runs entirely on your machine. Open-source. Free Groq models by default, Claude Haiku for polish mode.

![Status: v1 complete](https://img.shields.io/badge/status-v1%20complete-green)
![License: MIT](https://img.shields.io/badge/license-MIT-blue)

## What it does

- **One context in, three drafts out.** Paste a thought, get LinkedIn / X / Medium drafts shaped for each platform.
- **Three quality modes.** Fast (Llama 8B, free), Balanced (Llama 70B, free), Polish (Claude Haiku, ~$0.001/run).
- **Style memory.** Approving past drafts embeds them; future drafts sound like you, not like ChatGPT.
- **Conditional research.** When a post needs current info, Tavily fetches it and grounds the draft in it. Override with Auto / On / Off.
- **Adherence validation.** Platform rules enforced (X char count, LinkedIn hook, Medium structure) with one auto-retry on failure.
- **Scheduled reminders.** Set a time, get a desktop toast + phone push via ntfy.sh when it's time to post.
- **Full cost telemetry.** Every LLM call logged with tokens and cost. Stats dashboard included.

## What it does NOT do (by design)

- Auto-post. Drafts → human approval → reminder → you post manually. Auto-posting is v2.
- Agent sprawl. One orchestrator, one parallel fan-out, no critics/judges. See [BENCHMARKS.md](bench/BENCHMARKS.md) — the 7-agent alternative costs 11× more tokens with no quality gain.
- Tamil/Hindi translation. Evaluated and dropped for v1.

## Architecture

```
SvelteKit frontend (port 5173)
       |
FastAPI backend (port 8000)
       |
LangGraph pipeline:
  router → [research] → style_memory → generators (parallel) → adherence → aggregator
                                           |          |          |
                                        linkedin     x        medium
       |
SQLite + sqlite-vec  ·  APScheduler  ·  ntfy.sh
```

Full diagram: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | SvelteKit 2.x + TypeScript |
| Backend | FastAPI + Python 3.12 |
| Orchestration | LangGraph 1.0 |
| LLM gateway | LiteLLM (cascade) |
| Database | SQLite + sqlite-vec |
| Scheduling | APScheduler |
| Phone push | ntfy.sh |
| Launcher | `launch.ps1` (Windows) |

## Prerequisites

- Python 3.12+ and [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Node.js 18+
- Windows (for `launch.ps1`; backend + frontend run on any OS)

## Setup

```powershell
git clone https://github.com/azhwinraj/social-branding-agent
cd social-branding-agent

# Copy and fill in API keys
cp .env.example .env
# Edit .env — minimum required: GROQ_API_KEY

# Install backend dependencies
cd backend
uv sync
uv run alembic upgrade head
cd ..

# Install frontend dependencies
cd frontend
npm install
cd ..
```

## Run

```powershell
.\launch.ps1
```

Opens two terminal windows (backend + frontend) and launches the browser at `http://localhost:5173`.

To stop: close both terminal windows.

## API keys

| Key | Where to get | Required? |
|---|---|---|
| `GROQ_API_KEY` | [console.groq.com](https://console.groq.com) | Yes — free tier |
| `GEMINI_API_KEY` | [aistudio.google.com](https://aistudio.google.com) | For style memory embeddings |
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) | For polish mode only |
| `TAVILY_API_KEY` | [tavily.com](https://tavily.com) | For research mode |
| `LANGCHAIN_API_KEY` | [smith.langchain.com](https://smith.langchain.com) | Optional — tracing |
| `NTFY_TOPIC` | Pick any string, subscribe in [ntfy app](https://ntfy.sh) | For phone push |

## Benchmark

The lean vs bloated experiment (see [`bench/`](bench/)) shows:

| | Lean (1 call) | Main (2–3 calls) | Bloated (7 calls) |
|---|---|---|---|
| Avg latency | 0.9s | 1.4s | 20.9s |
| Avg tokens | 366 | 452 | 4090 |
| Adherence pass | 3/3 | 3/3 | 3/3 |
| Token overhead | 1× | 1.2× | **11.2×** |

Run it yourself: `cd backend && uv run python ../bench/runner.py`

## Roadmap

- [x] v1.0 — Draft generation, style memory, research, reminders, stats (phases A–J)
- [ ] v1.5 — Vision analysis (extract context from uploaded images, Phase K)
- [ ] v2.0 — Auto-posting via `linkedin-mcp` and `x-mcp`

## License

MIT. See [`LICENSE`](LICENSE).

## Built with

[LangGraph](https://github.com/langchain-ai/langgraph) · [LiteLLM](https://github.com/BerriAI/litellm) · [SvelteKit](https://kit.svelte.dev) · [sqlite-vec](https://github.com/asg017/sqlite-vec) · [ntfy.sh](https://ntfy.sh)
