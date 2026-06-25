from fastapi import APIRouter
from pydantic import BaseModel
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
    state = AgentState(
        context_input=req.context,
        platforms=req.platforms,
    )
    result = await graph.ainvoke(state)
    return {"drafts": result.get("drafts", []), "run_id": result.get("run_id", "")}
