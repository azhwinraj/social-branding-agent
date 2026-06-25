import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.models import Draft, LlmCall, StyleExample
from app.db.session import get_db
from app.graph.builder import graph
from app.graph.state import AgentState
from app.llm.embed import embed
from app.scheduler.jobs import schedule_draft

router = APIRouter()


class GenerateRequest(BaseModel):
    context: str
    platforms: list[str] = ["linkedin", "x", "medium"]
    image_description: str | None = None
    research: str = "auto"   # "auto" | "on" | "off"
    mode: str = "balanced"   # "fast" | "balanced" | "polish"


class ScheduleRequest(BaseModel):
    scheduled_at: datetime  # ISO 8601 from frontend


@router.get("/health")
async def health():
    return {"status": "ok", "service": "social-branding-agent"}


@router.post("/generate")
async def generate(req: GenerateRequest):
    run_id = str(uuid.uuid4())
    context = req.context
    if req.image_description:
        context = f"[Image attached: {req.image_description}]\n\n{context}"

    research_override: bool | None = None
    if req.research == "on":
        research_override = True
    elif req.research == "off":
        research_override = False

    state = AgentState(
        context_input=context,
        platforms=req.platforms,
        run_id=run_id,
        quality_mode=req.mode,
        research_override=research_override,
    )
    result = await graph.ainvoke(state)
    return {
        "drafts": result.get("drafts", []),
        "run_id": run_id,
        "post_types": result.get("post_types", {}),
        "router_reasoning": result.get("router_reasoning", ""),
    }


@router.get("/drafts")
async def list_drafts(db: Session = Depends(get_db)):
    rows = db.query(Draft).order_by(Draft.created_at.desc()).limit(50).all()
    return [
        {
            "id": r.id,
            "platform": r.platform,
            "content": r.content,
            "context_input": r.context_input,
            "status": r.status,
            "total_cost_usd": r.total_cost_usd,
            "created_at": r.created_at.isoformat(),
            "scheduled_at": r.scheduled_at.isoformat() if r.scheduled_at else None,
        }
        for r in rows
    ]


@router.post("/drafts/{draft_id}/approve")
async def approve_draft(draft_id: int, db: Session = Depends(get_db)):
    draft = db.query(Draft).filter(Draft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    draft.status = "approved"
    draft.approved_at = datetime.utcnow()

    example = StyleExample(
        draft_id=draft.id,
        platform=draft.platform,
        content=draft.content,
    )
    db.add(example)
    db.flush()

    try:
        vector = await embed(draft.content)
        example.embedding = json.dumps(vector)
    except Exception:
        pass

    db.commit()
    return {"status": "approved", "id": draft_id, "embedding": example.embedding is not None}


@router.post("/drafts/{draft_id}/schedule")
async def schedule_draft_route(
    draft_id: int, req: ScheduleRequest, db: Session = Depends(get_db)
):
    draft = db.query(Draft).filter(Draft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    draft.scheduled_at = req.scheduled_at
    draft.status = "scheduled"
    db.commit()

    schedule_draft(draft_id, draft.platform, draft.content, req.scheduled_at)

    return {"status": "scheduled", "scheduled_at": req.scheduled_at.isoformat()}


@router.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    # Overall LLM call totals
    totals = db.query(
        func.count(LlmCall.id).label("calls"),
        func.coalesce(func.sum(LlmCall.prompt_tokens), 0).label("prompt_tokens"),
        func.coalesce(func.sum(LlmCall.completion_tokens), 0).label("completion_tokens"),
        func.coalesce(func.sum(LlmCall.cost_usd), 0.0).label("cost_usd"),
    ).one()

    # Breakdown by model
    by_model = db.query(
        LlmCall.model,
        func.count(LlmCall.id).label("calls"),
        func.coalesce(func.sum(LlmCall.prompt_tokens + LlmCall.completion_tokens), 0).label("tokens"),
        func.coalesce(func.sum(LlmCall.cost_usd), 0.0).label("cost_usd"),
    ).group_by(LlmCall.model).order_by(func.sum(LlmCall.cost_usd).desc()).all()

    # Breakdown by node
    by_node = db.query(
        LlmCall.node,
        func.count(LlmCall.id).label("calls"),
        func.coalesce(func.sum(LlmCall.prompt_tokens + LlmCall.completion_tokens), 0).label("tokens"),
        func.coalesce(func.sum(LlmCall.cost_usd), 0.0).label("cost_usd"),
    ).group_by(LlmCall.node).order_by(func.count(LlmCall.id).desc()).all()

    # Cost by day (SQLite strftime)
    by_day = db.query(
        func.strftime("%Y-%m-%d", LlmCall.created_at).label("date"),
        func.count(LlmCall.id).label("calls"),
        func.coalesce(func.sum(LlmCall.cost_usd), 0.0).label("cost_usd"),
        func.coalesce(func.sum(LlmCall.prompt_tokens + LlmCall.completion_tokens), 0).label("tokens"),
    ).group_by("date").order_by("date").all()

    # Draft counts
    draft_totals = db.query(
        Draft.status, func.count(Draft.id).label("count")
    ).group_by(Draft.status).all()

    return {
        "totals": {
            "calls": totals.calls,
            "prompt_tokens": totals.prompt_tokens,
            "completion_tokens": totals.completion_tokens,
            "total_tokens": totals.prompt_tokens + totals.completion_tokens,
            "cost_usd": totals.cost_usd,
        },
        "by_model": [
            {"model": r.model, "calls": r.calls, "tokens": r.tokens, "cost_usd": r.cost_usd}
            for r in by_model
        ],
        "by_node": [
            {"node": r.node, "calls": r.calls, "tokens": r.tokens, "cost_usd": r.cost_usd}
            for r in by_node
        ],
        "by_day": [
            {"date": r.date, "calls": r.calls, "cost_usd": r.cost_usd, "tokens": r.tokens}
            for r in by_day
        ],
        "drafts": {r.status: r.count for r in draft_totals},
    }
