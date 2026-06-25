from __future__ import annotations

from app.db.session import SessionLocal
from app.graph.nodes.generators._base import _user_message
from app.graph.state import AgentState
from app.llm.cascade import call
from app.llm.post_types import ALLOWED_TYPES, DEFAULT_TYPE
from app.llm.prompts import load


async def _linkedin(state: AgentState) -> dict:
    if "linkedin" not in state.platforms:
        return {}

    post_type = state.post_types.get("linkedin", "")
    if post_type not in ALLOWED_TYPES["linkedin"]:
        post_type = DEFAULT_TYPE["linkedin"]

    messages = [
        {"role": "system", "content": load(f"linkedin/{post_type}.md")},
        {"role": "user", "content": _user_message(
            state.context_input,
            state.research_results,
            state.style_examples.get("linkedin", []),
        )},
    ]
    with SessionLocal() as db:
        content, meta = await call(
            "linkedin_gen", "linkedin", messages, state.run_id, db, state.quality_mode
        )
    return {"platform": "linkedin", "post_type": post_type, "content": content, **meta}
