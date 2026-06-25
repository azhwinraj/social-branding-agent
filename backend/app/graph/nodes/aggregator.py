import json

from app.db.models import Draft
from app.db.session import SessionLocal
from app.graph.state import AgentState


async def aggregator(state: AgentState) -> dict:
    if not state.drafts:
        return {}
    # Persist post_types + router_reasoning together so the UI tooltip has the
    # reasoning available even after page reload (no separate DB column needed).
    types_payload: dict = dict(state.post_types)
    if state.router_reasoning:
        types_payload["__reasoning__"] = state.router_reasoning
    post_types_json = json.dumps(types_payload) if types_payload else None
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
