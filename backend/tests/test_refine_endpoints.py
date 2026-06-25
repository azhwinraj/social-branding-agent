"""
Tests for the refinement API endpoints:
  POST /api/drafts/{id}/refine
  GET  /api/drafts/{id}/revisions
  POST /api/drafts/{id}/revert

Uses StaticPool in-memory SQLite. Happy-path tests mock the refinement
subgraph at the function level; validation tests run against real DB state.
The revert round-trip test drives the subgraph end-to-end with a mocked LLM.
"""
from __future__ import annotations

from datetime import datetime
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base, Draft, DraftRevision
from app.db.session import get_db
from app.main import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def test_db(test_engine):
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def client(test_db, monkeypatch) -> Generator:
    monkeypatch.setattr("app.graph.refinement.SessionLocal", sessionmaker(bind=test_db.bind))

    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _seed_draft(db) -> Draft:
    draft = Draft(
        platform="linkedin",
        content="Original content. Reduced cost by 40%.",
        context_input="I shipped a tool.",
        post_type="project_showcase",
        model_tier=0,
        total_cost_usd=0.001,
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


_MOCK_REVISION = {
    "id": "r1-1-abcd1234",
    "draft_id": 1,
    "revision_number": 1,
    "content": "Refined content. Reduced cost by 40%.",
    "refinement_instruction": "Make paragraph 2 less salesy",
    "model_used": "groq/llama-3.3-70b-versatile",
    "tier": 0,
    "tokens_in": 200,
    "tokens_out": 130,
    "cost_usd": 0.0001,
    "latency_ms": 850,
    "adherence_passed": True,
    "adherence_failures": [],
    "is_current": True,
    "created_at": "2026-06-25T12:00:00",
}


# ---------------------------------------------------------------------------
# POST /api/drafts/{id}/refine — validation
# ---------------------------------------------------------------------------

def test_refine_404_unknown_draft(client):
    resp = client.post("/api/drafts/9999/refine", json={"instruction": "make it better"})
    assert resp.status_code == 404


def test_refine_400_empty_instruction(client, test_db):
    draft = _seed_draft(test_db)
    resp = client.post(f"/api/drafts/{draft.id}/refine", json={"instruction": "   "})
    assert resp.status_code == 422   # Pydantic validation error


def test_refine_400_missing_instruction(client, test_db):
    draft = _seed_draft(test_db)
    resp = client.post(f"/api/drafts/{draft.id}/refine", json={})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/drafts/{id}/refine — happy path (mocked subgraph)
# ---------------------------------------------------------------------------

def test_refine_returns_revision_and_null_warning(client, test_db):
    draft = _seed_draft(test_db)
    mock_result = {"revision": {**_MOCK_REVISION, "draft_id": draft.id}, "warning": None}

    with patch("app.api.refine.refine", new=AsyncMock(return_value=mock_result)):
        resp = client.post(
            f"/api/drafts/{draft.id}/refine",
            json={"instruction": "Make paragraph 2 less salesy"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["revision"]["revision_number"] == 1
    assert body["revision"]["content"] == "Refined content. Reduced cost by 40%."
    assert body["warning"] is None


def test_refine_returns_soft_limit_warning(client, test_db):
    draft = _seed_draft(test_db)
    mock_result = {
        "revision": {**_MOCK_REVISION, "draft_id": draft.id, "revision_number": 4},
        "warning": "soft_limit_reached",
    }

    with patch("app.api.refine.refine", new=AsyncMock(return_value=mock_result)):
        resp = client.post(
            f"/api/drafts/{draft.id}/refine",
            json={"instruction": "yet another change"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["warning"] == "soft_limit_reached"
    assert body["revision"] is not None


# ---------------------------------------------------------------------------
# GET /api/drafts/{id}/revisions
# ---------------------------------------------------------------------------

def test_revisions_404_unknown_draft(client):
    resp = client.get("/api/drafts/9999/revisions")
    assert resp.status_code == 404


def test_revisions_returns_oldest_first(client, test_db):
    draft = _seed_draft(test_db)
    # Add a second revision manually
    test_db.add(DraftRevision(
        id=f"r1-{draft.id}",
        draft_id=draft.id,
        revision_number=1,
        content="Revised content. 40% reduction.",
        refinement_instruction="first instruction",
        model_used="groq/llama-3.3-70b-versatile",
        tier=0,
        is_current=True,
        created_at=datetime.utcnow(),
    ))
    # Flip the original to not current
    test_db.query(DraftRevision).filter(
        DraftRevision.id == f"r0-{draft.id}"
    ).update({"is_current": False})
    test_db.commit()

    resp = client.get(f"/api/drafts/{draft.id}/revisions")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2
    assert body["refinement_count"] == 1
    numbers = [r["revision_number"] for r in body["revisions"]]
    assert numbers == [0, 1], "Revisions must be oldest-first"


def test_revisions_includes_all_fields(client, test_db):
    draft = _seed_draft(test_db)
    resp = client.get(f"/api/drafts/{draft.id}/revisions")

    assert resp.status_code == 200
    rev = resp.json()["revisions"][0]
    for field in ("id", "draft_id", "revision_number", "content", "model_used",
                  "tier", "is_current", "created_at"):
        assert field in rev, f"Missing field: {field}"


def test_revisions_soft_limit_returned(client, test_db):
    draft = _seed_draft(test_db)
    resp = client.get(f"/api/drafts/{draft.id}/revisions")
    assert "soft_limit" in resp.json()


# ---------------------------------------------------------------------------
# POST /api/drafts/{id}/revert — validation
# ---------------------------------------------------------------------------

def test_revert_404_unknown_draft(client):
    resp = client.post("/api/drafts/9999/revert", json={"revision_number": 0})
    assert resp.status_code == 404


def test_revert_404_unknown_revision(client, test_db):
    draft = _seed_draft(test_db)
    resp = client.post(f"/api/drafts/{draft.id}/revert", json={"revision_number": 99})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Revert round-trip — real subgraph, mocked LLM
# Refine 3×, revert to revision 1, assert draft.content matches revision 1
# ---------------------------------------------------------------------------

def _mock_llm(content: str):
    async def fake(model, messages, **kwargs):
        r = MagicMock()
        r.choices[0].message.content = content
        r.usage.prompt_tokens = 100
        r.usage.completion_tokens = 80
        return r
    return fake


async def test_revert_restores_content_via_api(test_db, monkeypatch):
    """
    Refine 3x then revert via API to revision 1.
    Asserts: response contains revision 1 content,
             DB draft.content is updated to match.
    """
    from httpx import AsyncClient, ASGITransport

    monkeypatch.setattr(
        "app.graph.refinement.SessionLocal",
        sessionmaker(bind=test_db.bind),
    )

    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        draft = _seed_draft(test_db)

        # Refine 3 times with distinct content per revision
        revision_contents = ["Rev 1 content. 40%.", "Rev 2 content. 40%.", "Rev 3 content. 40%."]
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            for i, content in enumerate(revision_contents):
                with patch("litellm.acompletion", side_effect=_mock_llm(content)), \
                     patch("litellm.completion_cost", return_value=0.0001):
                    r = await ac.post(
                        f"/api/drafts/{draft.id}/refine",
                        json={"instruction": f"instruction {i+1}"},
                    )
                assert r.status_code == 200

            # Revert to revision 1
            resp = await ac.post(
                f"/api/drafts/{draft.id}/revert",
                json={"revision_number": 1},
            )

        assert resp.status_code == 200
        current = resp.json()["current_revision"]
        assert current["revision_number"] == 1
        assert current["content"] == "Rev 1 content. 40%."
        assert current["is_current"] is True

        # Verify DB denormalization
        test_db.refresh(draft)
        assert draft.content == "Rev 1 content. 40%."

    finally:
        app.dependency_overrides.clear()


async def test_revisions_list_after_revert_has_correct_is_current(test_db, monkeypatch):
    """After revert, exactly one revision has is_current=True."""
    from httpx import AsyncClient, ASGITransport

    monkeypatch.setattr(
        "app.graph.refinement.SessionLocal",
        sessionmaker(bind=test_db.bind),
    )

    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        draft = _seed_draft(test_db)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            for i in range(2):
                with patch("litellm.acompletion", side_effect=_mock_llm(f"Rev {i+1}. 40%.")), \
                     patch("litellm.completion_cost", return_value=0.0):
                    await ac.post(
                        f"/api/drafts/{draft.id}/refine",
                        json={"instruction": f"inst {i+1}"},
                    )

            await ac.post(f"/api/drafts/{draft.id}/revert", json={"revision_number": 0})
            resp = await ac.get(f"/api/drafts/{draft.id}/revisions")

        revisions = resp.json()["revisions"]
        current = [r for r in revisions if r["is_current"]]
        assert len(current) == 1
        assert current[0]["revision_number"] == 0

    finally:
        app.dependency_overrides.clear()
