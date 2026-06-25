from __future__ import annotations

from app.db.session import SessionLocal
from app.graph.nodes.generators._base import _user_message
from app.graph.state import AgentState
from app.llm.cascade import call
from app.llm.prompts import load


async def _medium(state: AgentState) -> dict:
    if "medium" not in state.platforms:
        return {}
    messages = [
        {"role": "system", "content": load("medium_gen.md")},
        {"role": "user", "content": _user_message(
            state.context_input,
            state.research_results,
            state.style_examples.get("medium", []),
        )},
    ]
    with SessionLocal() as db:
        content, meta = await call(
            "medium_gen", "medium", messages, state.run_id, db, state.quality_mode
        )
    return {"platform": "medium", "content": content, **meta}
