# Social Branding Agent

A desktop AI agent that drafts platform-specific posts for LinkedIn, X, and Medium from a single context input, using a cost-optimized multi-provider LLM cascade with vector-based style memory and approval-gated scheduling.

This is the file Claude Code reads at the start of every session. It is the source of truth for how this repo works. Keep it short. Move detailed workflows to `.claude/skills/` and specialized expertise to `.claude/agents/`.

---

## Stack at a glance

- **Shell:** Tauri 2.0 (Rust)
- **Frontend:** SvelteKit 2.x + TypeScript
- **Backend:** FastAPI (Python 3.12)
- **Orchestration:** LangGraph 1.0
- **LLM gateway:** LiteLLM
- **Database:** SQLite + sqlite-vec + SQLAlchemy 2.0
- **Scheduling:** APScheduler
- **Phone push:** ntfy.sh

---

## Key commands

### Backend (run from `backend/`)
```bash
uv sync                                     # install deps
uv run uvicorn app.main:app --reload        # dev server (port 8000)
uv run pytest                               # run tests
uv run ruff check . && uv run ruff format .  # lint
uv run mypy app/                            # types
uv run alembic upgrade head                 # apply migrations
uv run alembic revision --autogenerate -m "msg"  # new migration
```

### Frontend (run from `frontend/`)
```bash
npm install
npm run dev                                 # dev server (port 5173)
npm run build                               # production build
npm run check                               # svelte-check + tsc
```

### Tauri (run from repo root)
```bash
cargo tauri dev                             # dev mode with hot reload
cargo tauri build                           # production build
```

### Bench
```bash
uv run python bench/runner.py --inputs bench/inputs/ --output bench/results/
```

---

## Folder structure (canonical)
social-branding-agent/

├── src-tauri/              # Rust shell (~30 lines, mostly boilerplate)

├── frontend/               # SvelteKit

├── backend/

│   └── app/

│       ├── main.py         # FastAPI entry

│       ├── api/            # HTTP routes

│       ├── graph/          # LangGraph nodes + state

│       ├── llm/            # LiteLLM cascade + prompts

│       ├── db/             # SQLAlchemy models + sqlite-vec

│       ├── scheduler/      # APScheduler + notifiers

│       ├── research/       # Tavily client

│       └── evals/          # Adherence rules + LLM judge

├── bench/                  # Side experiment (lean vs bloated vs main)

└── docs/                   # ARCHITECTURE.md, COST_MODEL.md, etc.

See `docs/ARCHITECTURE.md` for the full system diagram.

---

## How the agent works (one paragraph)

The user submits a context (text + optional images) via the SvelteKit frontend. FastAPI invokes a LangGraph state machine. A router node (Llama 3.1 8B on Groq free tier) decides which platforms to target and whether research is needed. If research is needed, the Tavily node runs. A style-memory node embeds the context via Gemini embedding-001 and retrieves the top-3 most similar past approved posts per platform from sqlite-vec. Three platform generator nodes (LinkedIn / X / Medium) run in parallel — each uses a 3-tier model cascade (free → free → Claude failsafe). An adherence validator runs platform-specific rules and regenerates once on failure. The aggregator persists drafts with full cost/token telemetry and surfaces them in the UI for human approval. Approved drafts can be scheduled; APScheduler triggers desktop + ntfy.sh phone notifications at the scheduled time.

---

## Critical conventions

### LLM call discipline
- **All LLM calls go through `app.llm.cascade.call(...)`.** Never call `litellm.completion(...)` directly outside this module.
- Every call must log to `llm_calls` table — the cascade module does this automatically. If you bypass it, telemetry breaks and the stats page lies.
- Model identifiers are in `app/llm/cascade.py:CASCADES`. Don't hardcode model strings in node files.

### Prompts as files, never as strings
- All system prompts live in `app/llm/prompts/*.md`.
- Loaded via `app.llm.prompts.load("linkedin_gen.md")`. Cached in memory.
- Prompts are version-controlled, diffable, and reviewable. No f-strings buried in Python.

### LangGraph node pattern
- Every node is a function `(state: AgentState) -> dict` returning **only the keys it updates**, not the whole state.
- Parallel nodes (the 3 generators) write to `drafts` which uses the `add` reducer.
- New nodes go in `app/graph/nodes/`. See `.claude/agents/langgraph-node-writer.md` for the full pattern.

### Database
- All migrations via Alembic. **Never edit schema directly in `models.py` without generating a migration.**
- sqlite-vec extension is loaded in `db/vec.py:setup_connection()`. If a query fails with "no such module: vec0", that setup didn't run.

### Cost tracking
- Cost is computed by LiteLLM and stored on every `llm_calls` row.
- Don't display "$0.00" anywhere — show 6 decimal places (`{cost:.6f}`) since individual calls are sub-cent.
- The stats page aggregates per platform / per model / per day.

### Async everywhere in the backend
- All FastAPI routes are `async def`.
- All LLM calls use `litellm.acompletion(...)`, not `completion(...)`.
- The parallel fan-out uses `asyncio.gather(...)` inside the LangGraph node, NOT LangGraph's `Send` API (we want a flat parallel structure, not nested supervisors).

---

## What NOT to do

- **Do not** add a critic/judge agent to the main generation flow. The architecture deliberately stops at adherence rules. We are not building a 7-agent system; that's the anti-pattern catalogued in `bench/bloated/`.
- **Do not** call Claude as the primary model in any generator. Claude is failsafe (Tier 3), used only when free tiers fail or in polish mode.
- **Do not** embed images or large blobs in SQLite. Filesystem only (`~/.social-branding-agent/images/`). The DB stays small and backupable.
- **Do not** add LangSmith or any observability code inside nodes — it's wired at the graph-builder level via callbacks.
- **Do not** introduce new dependencies without checking if the same job can be done with stdlib + an existing dep. The point of this repo is lean.
- **Do not** widen the model cascade beyond 3 tiers per node. The cascade exists to fail gracefully, not to provide infinite quality escalation.
- **Do not** add Tamil/Hindi translation in v1. It was evaluated and explicitly dropped — X engagement data does not support it for AI/tech content.
- **Do not** auto-post in v1. Drafts → human approval → reminder → user posts manually. Auto-posting is v2 via MCP servers.
- **Do not** put secrets in CLAUDE.md, prompts, or chat. Use `.env` only.

---

## Build phases (current status: <UPDATE EACH SESSION>)

The repo is built in phases. Each phase has a single PR (or short PR sequence) and a definition of done. Do not start phase N+1 before phase N is merged.

| Phase | Goal | DoD |
|---|---|---|
| A | Foundation: Tauri + Svelte + FastAPI skeleton, SQLite ready, LangSmith trace working | Run `cargo tauri dev`, click button, see backend response. LangSmith shows the trace. |
| B | LLM gateway + single-platform (LinkedIn, Tier 1 only) | Submit context, see LinkedIn draft with token count and cost in 5s. |
| C | Multi-platform fan-out + adherence rules | All three platforms generate in parallel; failing drafts get one regenerate attempt. |
| D | Style memory (sqlite-vec + Gemini embedding) | After 5 approved posts, 6th draft visibly matches voice. Embeddings populated in DB. |
| E | Research (Tavily, conditional) + image pass-through | "What's new in MCP this month?" triggers research; image upload attaches metadata. |
| F | Scheduling + desktop + ntfy.sh phone push | Schedule post 2 min ahead; phone buzzes on time. |
| G | Polish mode + full 3-tier cascade | Same input in all 3 quality modes produces measurably different cost + quality. |
| H | Stats dashboard + observability polish | Two weeks of usage; stats match billing dashboards. |
| I | Side benchmark (lean + bloated) + BENCHMARKS.md | `python bench/runner.py` produces results.json and updated BENCHMARKS.md. |
| J | Packaging + open-source readiness | Someone downloads `.dmg` / `.exe` / `.AppImage`, adds API keys in Settings, uses the app. |

Deferred (post-v1): K (vision analysis), V2 (MCP auto-post via linkedin-mcp + x-mcp).

---

## Git conventions

- **Branches:** `feat/<slug>`, `fix/<slug>`, `chore/<slug>`, `docs/<slug>`.
- **Commits:** Conventional Commits (`feat(graph): add style memory node`).
- **PRs:** Use `.github/pull_request_template.md`. Self-review checklist must pass.
- **One logical change per PR.** Squash-merge to keep history clean.
- **Never `--no-verify`.** Hooks exist for a reason.

---

## When in doubt

- Architecture questions → `docs/ARCHITECTURE.md`
- Cost / model routing questions → `docs/COST_MODEL.md`
- Adding a new LangGraph node → `.claude/agents/langgraph-node-writer.md`
- Adding a new platform (future) → `.claude/skills/add-platform-generator/SKILL.md`
- Bench methodology → `bench/BENCHMARKS.md`
- The original design decisions → conversation history with Claude on the chat side (this CLAUDE.md is the distilled version)