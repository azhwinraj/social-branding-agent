"""
Bloated implementation: 7-agent pipeline (the anti-pattern).
Each stage is a separate LLM call. This is what NOT to build.
Catalogued here to demonstrate the cost and latency overhead of agent sprawl.
"""
from __future__ import annotations

import asyncio
import time
import litellm

_MODEL = "groq/llama-3.1-8b-instant"

_AGENTS = [
    ("context_analyzer",   "Analyze this social media context and extract key themes. Be brief."),
    ("audience_profiler",  "Based on this context, describe the target LinkedIn audience in 2 sentences."),
    ("hook_generator",     "Write 3 possible opening hooks for a LinkedIn post about this context."),
    ("draft_generator",    "Write a full LinkedIn post draft based on this context. 150-300 words."),
    ("critic",             "Critique this LinkedIn post draft. List 3 specific weaknesses."),
    ("tone_checker",       "Check the tone of this LinkedIn post. Is it authentic? Score 1-10 and explain."),
    ("final_formatter",    "Reformat and finalize this LinkedIn post. Add 2-3 hashtags at the end."),
]


async def _call(system: str, user: str) -> tuple[str, int, int, float]:
    resp = await litellm.acompletion(
        model=_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    content = resp.choices[0].message.content or ""
    try:
        cost = litellm.completion_cost(completion_response=resp)
    except Exception:
        cost = 0.0
    return content, resp.usage.prompt_tokens, resp.usage.completion_tokens, cost


async def generate(context: str) -> dict:
    t0 = time.perf_counter()
    total_prompt = total_completion = 0
    total_cost = 0.0
    current_input = context

    for _name, system in _AGENTS:
        content, pt, ct, cost = await _call(system, current_input)
        total_prompt += pt
        total_completion += ct
        total_cost += cost
        current_input = content  # each agent feeds into the next
        await asyncio.sleep(2.0)  # avoid TPM rate limit on free tier

    latency = time.perf_counter() - t0
    return {
        "content": current_input,
        "latency_s": round(latency, 3),
        "prompt_tokens": total_prompt,
        "completion_tokens": total_completion,
        "total_tokens": total_prompt + total_completion,
        "cost_usd": total_cost,
        "llm_calls": len(_AGENTS),
    }
