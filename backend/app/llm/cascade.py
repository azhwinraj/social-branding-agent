from __future__ import annotations

import litellm
from sqlalchemy.orm import Session

from app.db.models import LlmCall

# Router always uses the fast small model — routing doesn't need quality escalation.
_ROUTER = ["groq/llama-3.1-8b-instant"]

# Per-platform tiers by quality mode.
# fast    → small free model only (speed + zero cost)
# balanced → large free model with two fallbacks (current default)
# polish  → Claude Haiku as Tier 1 (quality first, cost secondary)
_PLATFORM_TIERS: dict[str, list[str]] = {
    "fast": [
        "groq/llama-3.1-8b-instant",
        "groq/llama-3.3-70b-versatile",       # fallback if 8B fails
    ],
    "balanced": [
        "groq/llama-3.3-70b-versatile",
        "groq/llama-3.1-70b-versatile",
        "anthropic/claude-haiku-4-5-20251001", # failsafe
    ],
    "polish": [
        "anthropic/claude-haiku-4-5-20251001", # Claude as Tier 1 in polish mode
        "groq/llama-3.3-70b-versatile",        # fallback if Anthropic key missing
    ],
}

CASCADES: dict[str, dict[str, list[str]]] = {
    "router":  {"fast": _ROUTER, "balanced": _ROUTER, "polish": _ROUTER},
    "linkedin": _PLATFORM_TIERS,
    "x":        _PLATFORM_TIERS,
    "medium":   _PLATFORM_TIERS,
}


async def call(
    node: str,
    cascade_key: str,
    messages: list[dict[str, str]],
    run_id: str,
    db: Session,
    mode: str = "balanced",
) -> tuple[str, dict]:
    tiers = CASCADES[cascade_key][mode]
    last_error: Exception | None = None

    for tier_index, model in enumerate(tiers):
        try:
            resp = await litellm.acompletion(model=model, messages=messages)
            content: str = resp.choices[0].message.content or ""
            usage = resp.usage

            try:
                cost = litellm.completion_cost(completion_response=resp)
            except Exception:
                cost = 0.0

            db.add(LlmCall(
                node=node,
                model=model,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                cost_usd=cost,
                run_id=run_id,
            ))
            db.commit()

            return content, {
                "model": model,
                "tier": tier_index,
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "cost_usd": cost,
            }
        except Exception as e:
            last_error = e

    raise RuntimeError(f"All tiers failed for {cascade_key}/{mode}: {last_error}")
