"""
Tests for draft_revisions is_current flag management and revision numbering.

Uses in-memory SQLite + mocked LLM calls — no Groq API needed.
"""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base, Draft, DraftRevision
from app.db.session import SessionLocal


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """
    Replace SessionLocal with a StaticPool in-memory engine for every test.
    autouse=True so all tests in this module use it automatically.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine)

    monkeypatch.setattr("app.graph.refinement.SessionLocal", TestSession)
    monkeypatch.setattr("app.llm.cascade.SessionLocal", TestSession, raising=False)

    yield TestSession

    Base.metadata.drop_all(engine)


def _seed_draft(Session, platform: str = "linkedin", post_type: str = "project_showcase") -> Draft:
    """Create a draft with its initial revision 0."""
    with Session() as db:
        draft = Draft(
            platform=platform,
            content="Original draft content. Built a scanner. 89% catch rate.",
            context_input="I shipped a prompt injection scanner.",
            post_type=post_type,
            model_tier=0,
            total_cost_usd=0.001,
            status="pending",
            created_at=datetime.utcnow(),
        )
        db.add(draft)
        db.flush()

        rev0 = DraftRevision(
            id=f"r0-{draft.id}",
            draft_id=draft.id,
            revision_number=0,
            content=draft.content,
            refinement_instruction=None,
            model_used="groq/llama-3.3-70b-versatile",
            tier=0,
            is_current=True,
            created_at=datetime.utcnow(),
        )
        db.add(rev0)
        db.commit()
        db.refresh(draft)
        return draft


_MOCK_META = {
    "model": "groq/llama-3.3-70b-versatile",
    "tier": 0,
    "prompt_tokens": 200,
    "completion_tokens": 120,
    "cost_usd": 0.0001,
}


# ---------------------------------------------------------------------------
# Revision numbering
# ---------------------------------------------------------------------------

async def test_first_refinement_creates_revision_1(isolated_db):
    draft = _seed_draft(isolated_db)
    with patch("app.graph.refinement.call", new=AsyncMock(return_value=("Rev 1 content.", _MOCK_META))):
        result = await __import__("app.graph.refinement", fromlist=["refine"]).refine(
            draft.id, "Make it punchier"
        )

    assert result["revision"]["revision_number"] == 1
    assert result["revision"]["content"] == "Rev 1 content."
    assert result["revision"]["refinement_instruction"] == "Make it punchier"


async def test_second_refinement_creates_revision_2(isolated_db):
    from app.graph.refinement import refine

    draft = _seed_draft(isolated_db)
    with patch("app.graph.refinement.call", new=AsyncMock(return_value=("Rev 1.", _MOCK_META))):
        await refine(draft.id, "instruction 1")
    with patch("app.graph.refinement.call", new=AsyncMock(return_value=("Rev 2.", _MOCK_META))):
        result = await refine(draft.id, "instruction 2")

    assert result["revision"]["revision_number"] == 2


# ---------------------------------------------------------------------------
# is_current flag — exactly one true per draft
# ---------------------------------------------------------------------------

async def test_is_current_flips_to_latest_revision(isolated_db):
    from app.graph.refinement import refine

    draft = _seed_draft(isolated_db)

    for i in range(3):
        with patch("app.graph.refinement.call", new=AsyncMock(return_value=(f"Rev {i+1}.", _MOCK_META))):
            await refine(draft.id, f"instruction {i+1}")

    with isolated_db() as db:
        revisions = (
            db.query(DraftRevision)
            .filter(DraftRevision.draft_id == draft.id)
            .all()
        )

    current_revs = [r for r in revisions if r.is_current]
    assert len(current_revs) == 1, f"Expected exactly 1 is_current, got {len(current_revs)}"
    assert current_revs[0].revision_number == 3


async def test_all_four_revisions_exist_after_three_refinements(isolated_db):
    from app.graph.refinement import refine

    draft = _seed_draft(isolated_db)

    for i in range(3):
        with patch("app.graph.refinement.call", new=AsyncMock(return_value=(f"Rev {i+1}.", _MOCK_META))):
            await refine(draft.id, f"instruction {i+1}")

    with isolated_db() as db:
        revision_numbers = [
            r.revision_number
            for r in db.query(DraftRevision)
            .filter(DraftRevision.draft_id == draft.id)
            .order_by(DraftRevision.revision_number)
            .all()
        ]

    assert revision_numbers == [0, 1, 2, 3]


async def test_draft_content_denormalized_to_latest(isolated_db):
    from app.graph.refinement import refine

    draft = _seed_draft(isolated_db)
    with patch("app.graph.refinement.call", new=AsyncMock(return_value=("Updated content!", _MOCK_META))):
        await refine(draft.id, "change something")

    with isolated_db() as db:
        updated = db.query(Draft).filter(Draft.id == draft.id).first()
        assert updated.content == "Updated content!"


# ---------------------------------------------------------------------------
# revert_to_revision
# ---------------------------------------------------------------------------

async def test_revert_restores_content_and_is_current(isolated_db):
    from app.graph.refinement import refine, revert_to_revision

    draft = _seed_draft(isolated_db)
    with patch("app.graph.refinement.call", new=AsyncMock(return_value=("Rev 1 content.", _MOCK_META))):
        await refine(draft.id, "first refinement")
    with patch("app.graph.refinement.call", new=AsyncMock(return_value=("Rev 2 content.", _MOCK_META))):
        await refine(draft.id, "second refinement")

    # Revert to revision 1
    reverted = revert_to_revision(draft.id, 1)
    assert reverted["revision_number"] == 1
    assert reverted["content"] == "Rev 1 content."
    assert reverted["is_current"] is True

    # Verify DB state
    with isolated_db() as db:
        current = (
            db.query(DraftRevision)
            .filter(DraftRevision.draft_id == draft.id, DraftRevision.is_current == True)  # noqa: E712
            .all()
        )
        assert len(current) == 1
        assert current[0].revision_number == 1

        draft_row = db.query(Draft).filter(Draft.id == draft.id).first()
        assert draft_row.content == "Rev 1 content."


async def test_revert_raises_for_unknown_revision(isolated_db):
    draft = _seed_draft(isolated_db)
    with pytest.raises(ValueError, match="Revision 99"):
        __import__("app.graph.refinement", fromlist=["revert_to_revision"]).revert_to_revision(
            draft.id, 99
        )
