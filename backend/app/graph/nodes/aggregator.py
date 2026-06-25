from app.db.models import Draft
from app.db.session import SessionLocal
from app.graph.state import AgentState


async def aggregator(state: AgentState) -> dict:
    if not state.drafts:
        return {}
    with SessionLocal() as db:
        for draft in state.drafts:
            db.add(Draft(
                platform=draft["platform"],
                content=draft["content"],
                context_input=state.context_input,
                total_cost_usd=draft.get("cost_usd", 0.0),
                status="pending",
            ))
        db.commit()
    return {}
