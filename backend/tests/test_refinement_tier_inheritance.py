"""
Tests for refinement tier inheritance.

Verifies that the cascade starts at the same model tier as the original
draft rather than always starting from tier 0.
"""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, call as mock_call

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base, Draft, DraftRevision
from app.llm.cascade import _PLATFORM_TIERS


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


def _seed_draft_at_tier(Session, tier: int) -> Draft:
    model = _PLATFORM_TIERS["balanced"][tier]
    with Session() as db:
        draft = Draft(
            platform="linkedin",
            content="Draft at tier " + str(tier) + ". Shipped. 42% reduction.",
            context_input="I shipped something.",
            post_type="project_showcase",
            model_tier=tier,
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
            model_used=model,
            tier=tier,
            is_current=True,
            created_at=datetime.utcnow(),
        )
        db.add(rev0)
        db.commit()
        db.refresh(draft)
        return draft


_BALANCED_MODELS = _PLATFORM_TIERS["balanced"]


async def test_tier0_draft_refines_at_tier0(isolated_db):
    from app.graph.refinement import refine

    draft = _seed_draft_at_tier(isolated_db, tier=0)
    expected_model = _BALANCED_MODELS[0]

    called_with_model = []

    async def fake_acompletion(model, messages, **kwargs):
        called_with_model.append(model)
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "Refined at tier 0. 42% reduction."
        mock_resp.usage.prompt_tokens = 100
        mock_resp.usage.completion_tokens = 80
        return mock_resp

    with patch("litellm.acompletion", side_effect=fake_acompletion), \
         patch("litellm.completion_cost", return_value=0.0001):
        await refine(draft.id, "make it snappier")

    assert len(called_with_model) >= 1
    assert called_with_model[0] == expected_model, (
        f"Expected first call to use {expected_model!r}, got {called_with_model[0]!r}"
    )


async def test_tier1_draft_refines_at_tier1_not_tier0(isolated_db):
    from app.graph.refinement import refine

    draft = _seed_draft_at_tier(isolated_db, tier=1)
    tier0_model = _BALANCED_MODELS[0]
    tier1_model = _BALANCED_MODELS[1]

    called_with_model = []

    async def fake_acompletion(model, messages, **kwargs):
        called_with_model.append(model)
        mock_resp = MagicMock()
        mock_resp.choices[0].message.content = "Refined at tier 1. 42% reduction."
        mock_resp.usage.prompt_tokens = 100
        mock_resp.usage.completion_tokens = 80
        return mock_resp

    with patch("litellm.acompletion", side_effect=fake_acompletion), \
         patch("litellm.completion_cost", return_value=0.0001):
        await refine(draft.id, "shorter please")

    assert tier0_model not in called_with_model, (
        f"Tier 0 model {tier0_model!r} should NOT have been called for a tier-1 draft"
    )
    assert tier1_model in called_with_model, (
        f"Tier 1 model {tier1_model!r} should have been called"
    )


async def test_tier_stored_on_revision(isolated_db):
    """The new revision should record the tier that was actually used."""
    from app.graph.refinement import refine

    draft = _seed_draft_at_tier(isolated_db, tier=0)

    async def fake_acompletion(model, messages, **kwargs):
        r = MagicMock()
        r.choices[0].message.content = "Content. 42%."
        r.usage.prompt_tokens = 50
        r.usage.completion_tokens = 40
        return r

    with patch("litellm.acompletion", side_effect=fake_acompletion), \
         patch("litellm.completion_cost", return_value=0.0):
        result = await refine(draft.id, "any change")

    assert result["revision"]["tier"] == 0


async def test_infer_mode_and_tier_known_model():
    from app.graph.refinement import _infer_mode_and_tier

    mode, tier = _infer_mode_and_tier("groq/llama-3.3-70b-versatile", "linkedin")
    assert mode == "balanced"
    assert tier == 0


async def test_infer_mode_and_tier_unknown_model_falls_back():
    from app.graph.refinement import _infer_mode_and_tier

    mode, tier = _infer_mode_and_tier("unknown/model", "linkedin")
    assert mode == "balanced"
    assert tier == 0
