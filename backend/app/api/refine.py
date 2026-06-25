"""
Refinement API endpoints.

POST   /api/drafts/{draft_id}/refine
GET    /api/drafts/{draft_id}/revisions
POST   /api/drafts/{draft_id}/revert

Note: the brief specifies outputs/{output_id} in the URL, but our data model
uses drafts as the per-platform output row (no separate draft_outputs table),
so draft_id serves as the output identifier.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.db.models import Draft, DraftRevision
from app.db.session import get_db
from app.graph.refinement import MAX_REFINEMENTS_BEFORE_WARNING, refine, revert_to_revision

router = APIRouter()


class RefineRequest(BaseModel):
    instruction: str

    @field_validator("instruction")
    @classmethod
    def instruction_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("instruction must not be empty")
        return v.strip()


class RevertRequest(BaseModel):
    revision_number: int


def _serialize_revision(rev: DraftRevision) -> dict:
    return {
        "id": rev.id,
        "draft_id": rev.draft_id,
        "revision_number": rev.revision_number,
        "content": rev.content,
        "refinement_instruction": rev.refinement_instruction,
        "model_used": rev.model_used,
        "tier": rev.tier,
        "tokens_in": rev.tokens_in,
        "tokens_out": rev.tokens_out,
        "cost_usd": rev.cost_usd,
        "latency_ms": rev.latency_ms,
        "adherence_passed": rev.adherence_passed,
        "is_current": rev.is_current,
        "created_at": rev.created_at.isoformat() if rev.created_at else None,
    }


@router.post("/drafts/{draft_id}/refine")
async def refine_draft(
    draft_id: int,
    req: RefineRequest,
    db: Session = Depends(get_db),
):
    """Refine a draft with a free-text instruction.

    Uses the same model tier as the original draft. Returns the new revision
    and a soft-limit warning if the user has exceeded MAX_REFINEMENTS_BEFORE_WARNING.
    """
    draft = db.query(Draft).filter(Draft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail=f"Draft {draft_id} not found")

    try:
        result = await refine(draft_id, req.instruction)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Refinement failed: {exc}")

    return {
        "revision": result["revision"],
        "warning": result["warning"],
    }


@router.get("/drafts/{draft_id}/revisions")
def list_revisions(draft_id: int, db: Session = Depends(get_db)):
    """Return all revisions for a draft, oldest first."""
    draft = db.query(Draft).filter(Draft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail=f"Draft {draft_id} not found")

    revisions = (
        db.query(DraftRevision)
        .filter(DraftRevision.draft_id == draft_id)
        .order_by(DraftRevision.revision_number)
        .all()
    )
    return {
        "revisions": [_serialize_revision(r) for r in revisions],
        "total": len(revisions),
        "refinement_count": sum(1 for r in revisions if r.refinement_instruction is not None),
        "soft_limit": MAX_REFINEMENTS_BEFORE_WARNING,
    }


@router.post("/drafts/{draft_id}/revert")
def revert_draft(
    draft_id: int,
    req: RevertRequest,
    db: Session = Depends(get_db),
):
    """Revert a draft to an earlier revision. No LLM call — pure flag swap."""
    draft = db.query(Draft).filter(Draft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail=f"Draft {draft_id} not found")

    try:
        revision = revert_to_revision(draft_id, req.revision_number)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return {"current_revision": revision}
