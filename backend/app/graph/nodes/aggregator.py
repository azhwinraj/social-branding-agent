import json

from app.db.models import Draft
from app.db.session import SessionLocal
from app.graph.state import AgentState


async def aggregator(state: AgentState) -> dict:
    if not state.drafts:
        return {}
    post_types_json = json.dumps(state.post_types) if state.post_types else None
    with SessionLocal() as db:
        for draft in state.drafts:
            db.add(Draft(
                platform=draft["platform"],
                content=draft["content"],
                context_input=state.context_input,
                total_cost_usd=draft.get("cost_usd", 0.0),
                status="pending",
                post_type=draft.get("post_type"),
                post_types_json=post_types_json,
                model_tier=draft.get("tier"),
            ))
        db.commit()
    return {}
