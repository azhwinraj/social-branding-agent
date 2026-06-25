import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import Draft, StyleExample
from app.db.session import get_db
from app.graph.builder import graph
from app.graph.state import AgentState
from app.llm.embed import embed

router = APIRouter()


class GenerateRequest(BaseModel):
    context: str
    platforms: list[str] = ["linkedin", "x", "medium"]
    image_description: str | None = None
    research: str = "auto"  # "auto" | "on" | "off"


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
        research_override=research_override,
    )
    result = await graph.ainvoke(state)
    return {"drafts": result.get("drafts", []), "run_id": run_id}


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
        pass  # embedding failure doesn't block approval

    db.commit()
    return {"status": "approved", "id": draft_id, "embedding": example.embedding is not None}
