"""
Tests for POST /api/drafts/{draft_id}/regenerate.

Uses FastAPI TestClient with an in-memory SQLite DB and a mocked cascade
so no real LLM calls are made. The integration test (marked 'integration')
runs against a real Groq call.
"""
from __future__ import annotations

from datetime import datetime
from typing import Generator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base, Draft
from app.db.session import get_db
from app.main import app


# ---------------------------------------------------------------------------
# In-memory DB + TestClient fixtures
#
# StaticPool is required: sqlite:///:memory: gives each connection its own
# empty DB, so tests would see "no such table" on any re-query after commit.
# StaticPool reuses a single connection for all sessions in the test.
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
def test_db(test_engine) -> Generator:
    Session = sessionmaker(bind=test_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def client(test_db) -> Generator:
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def linkedin_draft(test_db) -> Draft:
    draft = Draft(
        platform="linkedin",
        content="Original content about shipping a tool.",
        context_input="I shipped a prompt injection scanner.",
        post_type="project_showcase",
        post_types_json='{"linkedin": "project_showcase", "x": "thread"}',
        total_cost_usd=0.001,
        status="pending",
        created_at=datetime.utcnow(),
    )
    test_db.add(draft)
    test_db.commit()
    test_db.refresh(draft)
    return draft


# ---------------------------------------------------------------------------
# Validation tests (no LLM calls needed)
# ---------------------------------------------------------------------------

def test_regenerate_404_unknown_draft(client):
    resp = client.post("/api/drafts/9999/regenerate", json={"platform": "linkedin", "post_type": "learning"})
    assert resp.status_code == 404


def test_regenerate_400_unknown_platform(client, linkedin_draft):
    resp = client.post(
        f"/api/drafts/{linkedin_draft.id}/regenerate",
        json={"platform": "tiktok", "post_type": "video"},
    )
    assert resp.status_code == 400
    assert "platform" in resp.json()["detail"].lower()


def test_regenerate_400_unknown_post_type(client, linkedin_draft):
    resp = client.post(
        f"/api/drafts/{linkedin_draft.id}/regenerate",
        json={"platform": "linkedin", "post_type": "NOT_A_TYPE"},
    )
    assert resp.status_code == 400
    assert "post_type" in resp.json()["detail"].lower()


def test_regenerate_400_platform_mismatch(client, linkedin_draft):
    # Draft is linkedin, but request says x
    resp = client.post(
        f"/api/drafts/{linkedin_draft.id}/regenerate",
        json={"platform": "x", "post_type": "thread"},
    )
    assert resp.status_code == 400
    assert "linkedin" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Happy path — mocked LLM call
# ---------------------------------------------------------------------------

_MOCK_META = {
    "model": "groq/llama-3.3-70b-versatile",
    "tier": 0,
    "prompt_tokens": 100,
    "completion_tokens": 150,
    "cost_usd": 0.0002,
}

def test_regenerate_happy_path_updates_draft(client, test_db, linkedin_draft):
    new_content = "I spent 3 weeks debugging one missing sentence. Here's what I learned."

    with patch("app.api.routes.call", new=AsyncMock(return_value=(new_content, _MOCK_META))):
        resp = client.post(
            f"/api/drafts/{linkedin_draft.id}/regenerate",
            json={"platform": "linkedin", "post_type": "learning"},
        )

    assert resp.status_code == 200
    body = resp.json()["draft_output"]

    assert body["content"] == new_content
    assert body["post_type"] == "learning"
    assert body["status"] == "pending"
    assert body["platform"] == "linkedin"


def test_regenerate_updates_db_row(client, test_db, linkedin_draft):
    new_content = "Shipped webex-mcp — 15 tools, OAuth2+PKCE. Here's how it went."

    with patch("app.api.routes.call", new=AsyncMock(return_value=(new_content, _MOCK_META))):
        client.post(
            f"/api/drafts/{linkedin_draft.id}/regenerate",
            json={"platform": "linkedin", "post_type": "milestone"},
        )

    test_db.refresh(linkedin_draft)
    assert linkedin_draft.content == new_content
    assert linkedin_draft.post_type == "milestone"
    assert linkedin_draft.status == "pending"
    assert linkedin_draft.approved_at is None
    assert linkedin_draft.scheduled_at is None


def test_regenerate_updates_post_types_json(client, test_db, linkedin_draft):
    with patch("app.api.routes.call", new=AsyncMock(return_value=("new", _MOCK_META))):
        client.post(
            f"/api/drafts/{linkedin_draft.id}/regenerate",
            json={"platform": "linkedin", "post_type": "hot_take"},
        )

    import json
    test_db.refresh(linkedin_draft)
    types = json.loads(linkedin_draft.post_types_json)
    # linkedin type updated, x type preserved from original post_types_json
    assert types["linkedin"] == "hot_take"
    assert types.get("x") == "thread"


def test_regenerate_resets_approved_draft(client, test_db, linkedin_draft):
    # Simulate a previously-approved draft
    linkedin_draft.status = "approved"
    linkedin_draft.approved_at = datetime.utcnow()
    test_db.commit()

    with patch("app.api.routes.call", new=AsyncMock(return_value=("new content", _MOCK_META))):
        resp = client.post(
            f"/api/drafts/{linkedin_draft.id}/regenerate",
            json={"platform": "linkedin", "post_type": "event_recap"},
        )

    assert resp.status_code == 200
    test_db.refresh(linkedin_draft)
    assert linkedin_draft.status == "pending"
    assert linkedin_draft.approved_at is None


# ---------------------------------------------------------------------------
# Integration test — real Groq call
# ---------------------------------------------------------------------------

@pytest.mark.integration
async def test_regenerate_integration_returns_valid_content(test_db, linkedin_draft):
    import os
    from app.config import settings

    if not settings.groq_api_key:
        pytest.skip("GROQ_API_KEY not set")

    os.environ["GROQ_API_KEY"] = settings.groq_api_key

    from httpx import AsyncClient, ASGITransport

    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                f"/api/drafts/{linkedin_draft.id}/regenerate",
                json={"platform": "linkedin", "post_type": "learning"},
            )
        assert resp.status_code == 200
        body = resp.json()["draft_output"]
        assert len(body["content"]) > 50
        assert body["post_type"] == "learning"
    finally:
        app.dependency_overrides.clear()
