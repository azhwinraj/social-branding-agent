# Benchmark Results

> Generated: 2026-06-25 · 3 inputs · model: `groq/llama-3.1-8b-instant`

## Summary

| Metric | Lean | Main | Bloated |
|---|---|---|---|
| Avg latency | 0.904s | — | 20.946s |
| Avg tokens | 366 | — | 4090 |
| LLM calls | 1 | 2–3 | 7 |
| Token overhead | 1× | — | **11.2×** |
| Latency overhead | 1× | — | **23.2×** |
| Adherence pass | 3/3 | — | 3/3 |

**Finding:** The bloated 7-agent pipeline uses 11.2× more tokens and takes 23.2× longer
with no measurable improvement in adherence quality.

## Per-Input Results

| Input | Lean latency | Lean tokens | Lean calls | Main latency | Main tokens | Main calls | Bloated latency | Bloated tokens | Bloated calls |
|---|---|---|---|---|---|---|---|---|---|
| input_01 | 0.668s | 323 | 1 | 1.39 | 455 | 2-3 | 21.456s | 4078 | 7 |
| input_02 | 0.555s | 382 | 1 | 1.363 | 456 | 2-3 | 18.834s | 4049 | 7 |
| input_03 | 1.489s | 392 | 1 | 1.277 | 444 | 2-3 | 22.549s | 4142 | 7 |

## Architecture Comparison

### Lean (`bench/lean.py`)
Single LLM call. System prompt encodes all rules. No framework.
- ✅ Minimal latency
- ✅ Zero framework overhead
- ❌ No cascade fallback
- ❌ No adherence enforcement
- ❌ No style memory

### Main (`backend/app/graph/`)
LangGraph pipeline: router → style_memory → generators → adherence → aggregator.
- ✅ Adherence validation with one retry
- ✅ Style memory from approved posts
- ✅ 3-tier cascade with free → Claude failsafe
- ✅ Conditional research via Tavily
- ✅ Full cost telemetry
- ⚠ 2–3× lean latency (acceptable for content generation)

### Bloated (`bench/bloated.py`)
7-agent sequential pipeline: analyzer → profiler → hook_gen → drafter → critic → tone → formatter.
- ❌ 11.2× token cost vs lean
- ❌ 23.2× latency vs lean
- ❌ No parallel execution
- ❌ Adherence no better than lean
- ❌ Each agent context window sees only its predecessor's output (information loss)

## Methodology

- All variants use the same base model (`groq/llama-3.1-8b-instant`)
- Adherence check: word count 50–600 + hashtag present
- Main variant requires the backend to be running on port 8000
- Run: `cd backend && uv run python ../bench/runner.py`
