"""
Tests for style_memory type-filtered retrieval and cold-start fallback logic.

Uses an in-memory SQLite database seeded with fixture rows so the actual
SQL queries are exercised rather than mocked.
"""
from __future__ import annotations

import json
import math

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, StyleExample
from app.graph.nodes.style_memory import _MIN_TYPE_MATCHES, _cosine, _retrieve_for_platform, _top_k


# ---------------------------------------------------------------------------
# In-memory DB fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


def _fake_vec(seed: float, dim: int = 8) -> list[float]:
    """Deterministic unit vector based on a seed."""
    raw = [math.sin(seed * (i + 1)) for i in range(dim)]
    mag = math.sqrt(sum(x * x for x in raw))
    return [x / mag for x in raw]


def _embed_json(seed: float) -> str:
    return json.dumps(_fake_vec(seed))


def _add_example(db, platform: str, post_type: str, content: str, vec_seed: float) -> None:
    db.add(StyleExample(
        draft_id=1,
        platform=platform,
        post_type=post_type,
        content=content,
        embedding=_embed_json(vec_seed),
    ))
    db.commit()


# ---------------------------------------------------------------------------
# Pure-function tests (no DB)
# ---------------------------------------------------------------------------

def test_cosine_identical_vectors():
    v = [1.0, 0.0, 0.0]
    assert _cosine(v, v) == pytest.approx(1.0)


def test_cosine_orthogonal_vectors():
    assert _cosine([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_cosine_zero_vector_returns_zero():
    assert _cosine([0.0, 0.0], [1.0, 1.0]) == 0.0


def test_top_k_returns_highest_similarity_first():
    class FakeRow:
        def __init__(self, content, vec):
            self.content = content
            self.embedding = json.dumps(vec)

    query = [1.0, 0.0]
    rows = [
        FakeRow("low",  [0.0, 1.0]),   # cos=0.0
        FakeRow("high", [1.0, 0.0]),   # cos=1.0
        FakeRow("mid",  [0.7, 0.7]),   # cos≈0.7
    ]
    result = _top_k(query, rows, 2)
    assert result == ["high", "mid"]


def test_top_k_k_larger_than_rows_returns_all():
    class FakeRow:
        def __init__(self, content, vec):
            self.content = content
            self.embedding = json.dumps(vec)

    rows = [FakeRow("a", [1.0, 0.0]), FakeRow("b", [0.0, 1.0])]
    assert len(_top_k([1.0, 0.0], rows, 10)) == 2


# ---------------------------------------------------------------------------
# Path 1 — type-filtered retrieval
# ---------------------------------------------------------------------------

def test_path1_used_when_enough_type_matches(db_session):
    for i in range(_MIN_TYPE_MATCHES):
        _add_example(db_session, "linkedin", "project_showcase", f"post {i}", float(i + 1))
    # Also add a different type that should NOT be returned
    _add_example(db_session, "linkedin", "hot_take", "distractor", 99.0)

    query_vec = _fake_vec(1.5)
    result = _retrieve_for_platform(db_session, "linkedin", "project_showcase", query_vec)

    assert result is not None
    assert len(result) <= 3
    # The distractor (different type) must not appear
    assert "distractor" not in result


def test_path1_returns_up_to_3_results(db_session):
    for i in range(5):
        _add_example(db_session, "x", "thread", f"tweet {i}", float(i + 1))

    query_vec = _fake_vec(1.0)
    result = _retrieve_for_platform(db_session, "x", "thread", query_vec)

    assert result is not None
    assert len(result) == 3


# ---------------------------------------------------------------------------
# Path 2 — platform-only cold-start fallback
# ---------------------------------------------------------------------------

def test_path2_used_when_too_few_type_matches(db_session):
    # Only 1 type-matched example (below _MIN_TYPE_MATCHES threshold)
    _add_example(db_session, "linkedin", "project_showcase", "typed post", 1.0)
    # But there are other types on the same platform
    _add_example(db_session, "linkedin", "learning", "learning post A", 2.0)
    _add_example(db_session, "linkedin", "learning", "learning post B", 3.0)

    query_vec = _fake_vec(1.0)
    result = _retrieve_for_platform(db_session, "linkedin", "project_showcase", query_vec)

    assert result is not None
    # Should draw from the full platform pool (3 rows), not just the 1 typed row
    assert len(result) <= 3
    # The typed post is in the pool so it may appear — just verify no crash and count
    assert len(result) >= 1


def test_path2_used_when_post_type_missing(db_session):
    # Platform has examples but post_type is empty (router fallback edge case)
    _add_example(db_session, "medium", "case_study", "medium post", 1.0)
    _add_example(db_session, "medium", "opinion", "opinion post", 2.0)

    query_vec = _fake_vec(1.5)
    result = _retrieve_for_platform(db_session, "medium", "", query_vec)

    assert result is not None


# ---------------------------------------------------------------------------
# Path 3 — default voice rubric
# ---------------------------------------------------------------------------

def test_path3_used_when_no_examples(db_session):
    # Empty DB — no examples for any platform
    query_vec = _fake_vec(1.0)
    result = _retrieve_for_platform(db_session, "linkedin", "project_showcase", query_vec)

    assert result is not None
    assert len(result) == 1
    # Should be the rubric content, not an empty string
    assert len(result[0]) > 50


def test_path3_used_when_embed_unavailable(db_session):
    # Has examples but no query vector (embed failed)
    _add_example(db_session, "linkedin", "learning", "a post", 1.0)

    result = _retrieve_for_platform(db_session, "linkedin", "learning", query_vec=None)

    # Should fall through to rubric since we can't rank
    assert result is not None
    assert len(result) == 1


def test_path3_all_three_platforms_have_rubric():
    """Every platform must have a default_voice rubric file."""
    from app.llm.prompts import load
    for platform in ["linkedin", "x", "medium"]:
        rubric = load(f"default_voice/{platform}.md")
        assert len(rubric.strip()) > 50, f"Rubric for {platform} is too short"
