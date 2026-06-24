# Social Branding Agent

> A desktop AI agent that drafts platform-specific posts for LinkedIn, X, and Medium from a single context input.

Runs locally. Open-source. Built on free LLM tiers by default, with cost-optimized cascade to Claude for polish mode.

![Status: in development](https://img.shields.io/badge/status-WIP-yellow)
![License: MIT](https://img.shields.io/badge/license-MIT-blue)

## What it does

- **One context in, three drafts out.** Paste a thought, get LinkedIn / X / Medium drafts shaped for each platform.
- **Selective platforms.** Generate for one, two, or all three per post.
- **Style memory.** Embeds your approved past posts; new drafts sound like you, not like ChatGPT.
- **Conditional research.** When a post needs current information, Tavily fetches and the agent grounds the draft in it.
- **Cost-optimized cascade.** Free Llama / GPT-OSS / Gemini for primary generation. Claude Sonnet as a polish/failsafe layer only.
- **Scheduled reminders.** Approve a draft, set a time. Desktop notification + phone push via ntfy.sh when it's time to post.
- **Adherence validation.** Platform-specific rules (X char count, LinkedIn hook line, Medium structure) enforced before drafts surface.
- **Full cost telemetry.** Every LLM call logged with tokens and dollar cost. Stats dashboard included.

## What it does NOT do (by design)

- Auto-post. Drafts go through human approval. Auto-posting is planned for v2 via separate MCP servers.
- Multi-agent sprawl. One orchestrator, one parallel fan-out, no critics/judges/synthesizers. See [`BENCHMARKS.md`](BENCHMARKS.md) for the comparison.
- Tamil/Hindi translation. Evaluated and dropped for v1 — engagement data didn't support it for AI/tech content on X.

## Architecture
┌─ Tauri (Rust shell) ──────────────────────────────────────┐

│  ┌─ SvelteKit frontend ───────────────────────────────┐  │

│  │  /compose  /drafts  /queue  /history  /stats       │  │

│  └────────────────────────────────────────────────────┘  │

│  ┌─ FastAPI backend ──────────────────────────────────┐  │

│  │  LangGraph: router → research → style → fan-out    │  │

│  │              → adherence → aggregator              │  │

│  │  LiteLLM gateway (cascade: free → free → Claude)   │  │

│  │  APScheduler + ntfy.sh client                      │  │

│  └────────────────────────────────────────────────────┘  │

│  SQLite + sqlite-vec (single-file persistence)            │

└────────────────────────────────────────────────────────────┘

Full diagram: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Tech stack

| Layer | Technology |
|---|---|
| Desktop shell | Tauri 2.0 |
| Frontend | SvelteKit 2.x |
| Backend | FastAPI |
| Orchestration | LangGraph 1.0 |
| LLM gateway | LiteLLM |
| Database | SQLite + sqlite-vec |
| Scheduling | APScheduler |
| Phone push | ntfy.sh |

## Models used

| Stage | Primary (free) | Fallback (free) | Failsafe (paid) |
|---|---|---|---|
| Router | Groq Llama 3.1 8B | Gemini 2.5 Flash | — |
| LinkedIn | Groq Llama 3.3 70B | Groq GPT-OSS 120B | Claude Sonnet 4.6 |
| X | Groq Llama 3.3 70B | Gemini 2.5 Flash | Claude Haiku 4.5 |
| Medium | Groq GPT-OSS 120B | Groq Llama 3.3 70B | Claude Sonnet 4.6 |
| Embeddings | Gemini embedding-001 | — | — |
| Research | Tavily Search API | — | — |

**Real-world monthly cost:** ~$0 to $2 for personal use. Free tiers cover the majority; Claude usage drains the $20/month Pro Agent SDK credit (if you have one) or pay-as-you-go.

## Getting started

### Prerequisites

- Rust toolchain ([install](https://rustup.rs/))
- Node 20+
- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- API keys (free tiers): Groq, Google AI Studio, Tavily. Optional: Anthropic for polish mode.

### Setup

```bash
git clone https://github.com/ashwinraj/social-branding-agent
cd social-branding-agent

cp .env.example .env
# Edit .env and add your API keys

# Backend
cd backend
uv sync
uv run alembic upgrade head

# Frontend
cd ../frontend
npm install

# Run in dev mode (from repo root)
cd ..
cargo tauri dev
```

### Configuration

All settings configurable in-app via Settings page. Or via `.env` for power users.

## Benchmark experiment

This repo includes a side-by-side comparison of three multi-agent architectures on identical inputs:

- **Main (`backend/app/graph/`)** — LangGraph fan-out with provider cascade
- **`bench/lean/`** — ~250 lines of custom asyncio, no framework
- **`bench/bloated/`** — anti-pattern with 7 agents and critics

Run all three on the same inputs:

```bash
uv run python bench/runner.py
```

Results documented in [`BENCHMARKS.md`](BENCHMARKS.md). The bloated variant costs ~8× more and scores no higher on quality.

## Roadmap

- [ ] v1.0 — Draft generation, style memory, reminders (phases A-J)
- [ ] v1.5 — Vision analysis (extract context from uploaded images)
- [ ] v2.0 — Auto-posting via `linkedin-mcp` and `x-mcp` (separate repos)
- [ ] v2.5 — Engagement learning loop (correlate draft features with real performance)

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Conventional commits, PR template required, CI must pass.

## License

MIT. See [`LICENSE`](LICENSE).

## Acknowledgments

Built with [LangGraph](https://github.com/langchain-ai/langgraph), [LiteLLM](https://github.com/BerriAI/litellm), [Tauri](https://tauri.app), [SvelteKit](https://kit.svelte.dev), and [sqlite-vec](https://github.com/asg017/sqlite-vec). Phone notifications via [ntfy.sh](https://ntfy.sh).