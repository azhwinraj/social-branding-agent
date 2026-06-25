"""
Tests for the 3-refinement soft limit warning.

Warning fires on the 4th refinement (revision_number > MAX_REFINEMENTS_BEFORE_WARNING).
The draft is still returned — the warning is informational only.
"""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base, Draft, DraftRevision
from app.graph.refinement import MAX_REFINEMENTS_BEFORE_WARNING


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch):
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


def _seed(Session):
    with Session() as db:
        draft = Draft(
            platform="x",
            content="Original thread. 3 tweets. Here's how it works.",
            context_input="I built something.",
            post_type="thread",
            model_tier=0,
            total_cost_usd=0.0,
            status="pending",
            created_at=datetime.utcnow(),
        )
        db.add(draft)
        db.flush()
        db.add(DraftRevision(
            id=f"r0-{draft.id}",
            draft_id=draft.id,
            revision_number=0,
            content=draft.content,
            model_used="groq/llama-3.3-70b-versatile",
            tier=0,
            is_current=True,
            created_at=datetime.utcnow(),
        ))
        db.commit()
        db.refresh(draft)
        return draft


def _mock_llm(content: str = '["tweet1", "tweet2", "tweet3"]'):
    async def fake(model, messages, **kwargs):
        r = MagicMock()
        r.choices[0].message.content = content
        r.usage.prompt_tokens = 80
        r.usage.completion_tokens = 60
        return r
    return fake


async def _do_refine(draft_id, instruction, content='["t1", "t2", "t3"]'):
    from app.graph.refinement import refine
    with patch("litellm.acompletion", side_effect=_mock_llm(content)), \
         patch("litellm.completion_cost", return_value=0.0):
        return await refine(draft_id, instruction)


async def test_no_warning_on_first_refinement(isolated_db):
    draft = _seed(isolated_db)
    result = await _do_refine(draft.id, "first")
    assert result["warning"] is None


async def test_no_warning_up_to_limit(isolated_db):
    draft = _seed(isolated_db)
    for i in range(MAX_REFINEMENTS_BEFORE_WARNING):
        result = await _do_refine(draft.id, f"refinement {i+1}")
    assert result["warning"] is None


async def test_warning_fires_on_refinement_beyond_limit(isolated_db):
    draft = _seed(isolated_db)
    # Do MAX_REFINEMENTS_BEFORE_WARNING refinements (no warning)
    for i in range(MAX_REFINEMENTS_BEFORE_WARNING):
        await _do_refine(draft.id, f"refinement {i+1}")
    # One more — this one should trigger the warning
    result = await _do_refine(draft.id, "one too many")
    assert result["warning"] == "soft_limit_reached"


async def test_draft_still_returned_despite_warning(isolated_db):
    draft = _seed(isolated_db)
    for i in range(MAX_REFINEMENTS_BEFORE_WARNING + 1):
        result = await _do_refine(draft.id, f"r{i+1}")

    # Even when warning fires, the revision must be present
    assert result["revision"] is not None
    assert result["revision"]["content"] is not None
    assert result["revision"]["revision_number"] == MAX_REFINEMENTS_BEFORE_WARNING + 1


async def test_refinement_continues_past_warning(isolated_db):
    """Warning is not a hard limit — 5th refinement should also succeed."""
    draft = _seed(isolated_db)
    for i in range(MAX_REFINEMENTS_BEFORE_WARNING + 2):
        result = await _do_refine(draft.id, f"r{i+1}")

    assert result["revision"]["revision_number"] == MAX_REFINEMENTS_BEFORE_WARNING + 2
    assert result["warning"] == "soft_limit_reached"
