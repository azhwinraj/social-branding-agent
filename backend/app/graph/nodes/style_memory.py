from __future__ import annotations

import json
import logging
import math

from app.db.models import StyleExample
from app.db.session import SessionLocal
from app.graph.state import AgentState
from app.llm.embed import embed
from app.llm.prompts import load

log = logging.getLogger(__name__)

# Minimum same-type examples required before the type-filtered path is used.
# Below this threshold we fall back to platform-wide retrieval.
_MIN_TYPE_MATCHES = 2


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(x * x for x in b))
    return dot / mag if mag else 0.0


def _top_k(query_vec: list[float], rows: list, k: int) -> list[str]:
    """Return the k most semantically similar content strings."""
    scored = sorted(
        [(_cosine(query_vec, json.loads(row.embedding)), row.content) for row in rows],
        reverse=True,
    )
    return [content for _, content in scored[:k]]


def _retrieve_for_platform(
    db,
    platform: str,
    post_type: str,
    query_vec: list[float] | None,
) -> list[str] | None:
    """
    Three-path retrieval for one platform.

    Path 1 — type-filtered (best quality):
        Same platform AND same post_type, ≥ _MIN_TYPE_MATCHES examples.
    Path 2 — platform-only cold-start:
        Same platform, any post_type. Used when type-matched pool is too small.
    Path 3 — default voice rubric:
        No approved posts for this platform at all, or embedding unavailable.
        Loads a static rubric file as a single synthetic example.
    """
    if query_vec is not None:
        # Path 1 — type-filtered
        if post_type:
            type_rows = (
                db.query(StyleExample)
                .filter(
                    StyleExample.platform == platform,
                    StyleExample.post_type == post_type,
                    StyleExample.embedding.isnot(None),
                )
                .all()
            )
            if len(type_rows) >= _MIN_TYPE_MATCHES:
                log.debug(
                    "style_memory: type-filtered path %s/%s (%d candidates)",
                    platform, post_type, len(type_rows),
                )
                return _top_k(query_vec, type_rows, 3)

        # Path 2 — platform-only fallback
        any_rows = (
            db.query(StyleExample)
            .filter(
                StyleExample.platform == platform,
                StyleExample.embedding.isnot(None),
            )
            .all()
        )
        if any_rows:
            log.info(
                "style_memory: platform-only fallback for %s "
                "(post_type=%r had %d type-matched, need %d)",
                platform,
                post_type,
                len(type_rows) if post_type else 0,
                _MIN_TYPE_MATCHES,
            )
            return _top_k(query_vec, any_rows, 3)

    # Path 3 — default voice rubric
    try:
        rubric = load(f"default_voice/{platform}.md")
        log.info("style_memory: default voice rubric for %s (no approved posts)", platform)
        return [rubric]
    except FileNotFoundError:
        log.warning("style_memory: no rubric file found for platform %r", platform)
        return None


async def style_memory(state: AgentState) -> dict:
    # Attempt to embed once; failure degrades to Path 3 (rubric) for all platforms.
    query_vec: list[float] | None = None
    try:
        query_vec = await embed(state.context_input)
    except Exception as exc:
        log.warning("style_memory: embedding failed (%s) — will use rubric fallback", exc)

    examples: dict[str, list[str]] = {}
    with SessionLocal() as db:
        for platform in state.platforms:
            post_type = state.post_types.get(platform, "")
            result = _retrieve_for_platform(db, platform, post_type, query_vec)
            if result:
                examples[platform] = result

    return {"style_examples": examples} if examples else {}
