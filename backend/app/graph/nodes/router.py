from __future__ import annotations

import json
import logging
import re

from app.db.session import SessionLocal
from app.graph.state import AgentState
from app.llm.cascade import call
from app.llm.post_types import ALLOWED_TYPES, DEFAULT_TYPE
from app.llm.prompts import load

log = logging.getLogger(__name__)


def _clean_json(text: str) -> str:
    """Strip markdown fences and leading/trailing whitespace."""
    return re.sub(r"```(?:json)?\n?", "", text).strip().rstrip("```").strip()


def _parse(text: str, platforms: list[str]) -> tuple[bool, dict[str, str], str]:
    """
    Parse router JSON. Returns (needs_research, post_types, reasoning).
    Falls back gracefully: unknown types → DEFAULT_TYPE, parse errors → safe defaults.
    """
    try:
        data = json.loads(_clean_json(text))
    except Exception:
        log.warning("router: JSON parse failed, using safe defaults. raw=%r", text[:200])
        return False, {p: DEFAULT_TYPE[p] for p in platforms if p in DEFAULT_TYPE}, ""

    needs_research = bool(data.get("needs_research", False))
    reasoning = data.get("reasoning", "")

    raw_types: dict = data.get("post_types", {})
    post_types: dict[str, str] = {}
    for platform in platforms:
        if platform not in ALLOWED_TYPES:
            continue
        inferred = raw_types.get(platform, "")
        if inferred in ALLOWED_TYPES[platform]:
            post_types[platform] = inferred
        else:
            fallback = DEFAULT_TYPE[platform]
            log.warning(
                "router: invalid post_type %r for %s, falling back to %r",
                inferred,
                platform,
                fallback,
            )
            post_types[platform] = fallback

    return needs_research, post_types, reasoning


async def router(state: AgentState) -> dict:
    # Research override short-circuits the LLM call but we still need post_types.
    # We only skip research classification, not type classification.
    platforms_str = ", ".join(state.platforms)
    user_message = f"Platforms: {platforms_str}\n\nContext:\n{state.context_input}"

    messages = [
        {"role": "system", "content": load("router.md")},
        {"role": "user", "content": user_message},
    ]

    try:
        with SessionLocal() as db:
            content, _ = await call("router", "router", messages, state.run_id, db)
        needs_research, post_types, reasoning = _parse(content, state.platforms)
    except Exception as exc:
        log.warning("router: LLM call failed (%s), using safe defaults", exc)
        needs_research = False
        post_types = {p: DEFAULT_TYPE[p] for p in state.platforms if p in DEFAULT_TYPE}
        reasoning = ""

    # Honor explicit research override from the user without discarding type inference.
    if state.research_override is not None:
        needs_research = state.research_override

    return {
        "needs_research": needs_research,
        "post_types": post_types,
        "router_reasoning": reasoning,
    }
