from __future__ import annotations

from app.db.session import SessionLocal
from app.graph.nodes.generators._base import _user_message
from app.graph.state import AgentState
from app.llm.cascade import call
from app.llm.prompts import load


async def _x(state: AgentState) -> dict:
    if "x" not in state.platforms:
        return {}
    messages = [
        {"role": "system", "content": load("x_gen.md")},
        {"role": "user", "content": _user_message(
            state.context_input,
            state.research_results,
            state.style_examples.get("x", []),
        )},
    ]
    with SessionLocal() as db:
        content, meta = await call(
            "x_gen", "x", messages, state.run_id, db, state.quality_mode
        )
    return {"platform": "x", "content": content, **meta}
