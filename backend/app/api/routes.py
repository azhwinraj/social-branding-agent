import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import Draft
from app.db.session import get_db
from app.graph.builder import graph
from app.graph.state import AgentState

router = APIRouter()


class GenerateRequest(BaseModel):
    context: str
    platforms: list[str] = ["linkedin", "x", "medium"]


@router.get("/health")
async def health():
    return {"status": "ok", "service": "social-branding-agent"}


@router.post("/generate")
async def generate(req: GenerateRequest):
    run_id = str(uuid.uuid4())
    state = AgentState(
        context_input=req.context,
        platforms=req.platforms,
        run_id=run_id,
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
