from __future__ import annotations

import litellm
from sqlalchemy.orm import Session

from app.db.models import LlmCall

CASCADES: dict[str, list[str]] = {
    "router": [
        "groq/llama-3.1-8b-instant",
    ],
    "linkedin": [
        "groq/llama-3.3-70b-versatile",
        "groq/llama-3.1-70b-versatile",
        "anthropic/claude-haiku-4-5-20251001",
    ],
    "x": [
        "groq/llama-3.3-70b-versatile",
        "groq/llama-3.1-70b-versatile",
        "anthropic/claude-haiku-4-5-20251001",
    ],
    "medium": [
        "groq/llama-3.3-70b-versatile",
        "groq/llama-3.1-70b-versatile",
        "anthropic/claude-haiku-4-5-20251001",
    ],
}


async def call(
    node: str,
    cascade_key: str,
    messages: list[dict[str, str]],
    run_id: str,
    db: Session,
) -> tuple[str, dict]:
    last_error: Exception | None = None

    for model in CASCADES[cascade_key]:
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
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "cost_usd": cost,
            }
        except Exception as e:
            last_error = e

    raise RuntimeError(f"All tiers failed for {cascade_key}: {last_error}")
