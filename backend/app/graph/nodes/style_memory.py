from __future__ import annotations

import json
import math

from app.db.models import StyleExample
from app.db.session import SessionLocal
from app.graph.state import AgentState
from app.llm.embed import embed


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(x * x for x in b))
    return dot / mag if mag else 0.0


async def style_memory(state: AgentState) -> dict:
    with SessionLocal() as db:
        total = db.query(StyleExample).filter(StyleExample.embedding.isnot(None)).count()

    if total == 0:
        return {}

    try:
        query_vec = await embed(state.context_input)
    except Exception:
        return {}

    examples: dict[str, list[str]] = {}

    with SessionLocal() as db:
        for platform in state.platforms:
            rows = (
                db.query(StyleExample)
                .filter(
                    StyleExample.platform == platform,
                    StyleExample.embedding.isnot(None),
                )
                .all()
            )
            if not rows:
                continue

            scored = sorted(
                [(
                    _cosine(query_vec, json.loads(row.embedding)),
                    row.content,
                ) for row in rows],
                reverse=True,
            )
            examples[platform] = [content for _, content in scored[:3]]

    return {"style_examples": examples}
