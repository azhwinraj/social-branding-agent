"""Lean implementation: single LLM call, no graph, no framework overhead."""
from __future__ import annotations

import time
import litellm

_SYSTEM = """You are a ghostwriter for a senior AI/ML engineer.
Write a LinkedIn post based on the user's context.
Open with a punchy hook. 150-300 words. Short paragraphs. End with a question or CTA.
2-3 hashtags at the end only. No preamble."""

_MODEL = "groq/llama-3.1-8b-instant"


async def generate(context: str) -> dict:
    t0 = time.perf_counter()
    resp = await litellm.acompletion(
        model=_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": context},
        ],
    )
    latency = time.perf_counter() - t0
    content = resp.choices[0].message.content or ""
    usage = resp.usage
    try:
        cost = litellm.completion_cost(completion_response=resp)
    except Exception:
        cost = 0.0

    return {
        "content": content,
        "latency_s": round(latency, 3),
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
        "total_tokens": usage.prompt_tokens + usage.completion_tokens,
        "cost_usd": cost,
        "llm_calls": 1,
    }
