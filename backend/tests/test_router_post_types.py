"""
Tests for router post-type classification.

Unit tests (no API calls) cover _parse and fallback logic.
Integration tests (marked 'integration') make real Groq calls and assert
that every returned type is in ALLOWED_TYPES for that platform.
"""
from __future__ import annotations

import json
import pytest

from app.graph.nodes.router import _parse
from app.llm.post_types import ALLOWED_TYPES, DEFAULT_TYPE

ALL_PLATFORMS = ["linkedin", "x", "medium"]


# ---------------------------------------------------------------------------
# Unit tests — _parse and validation logic
# ---------------------------------------------------------------------------

def _make_raw(needs_research: bool, post_types: dict, reasoning: str = "test") -> str:
    return json.dumps(
        {"needs_research": needs_research, "post_types": post_types, "reasoning": reasoning}
    )


def test_parse_valid_types():
    raw = _make_raw(
        False,
        {"linkedin": "project_showcase", "x": "thread", "medium": "case_study"},
    )
    needs_research, post_types, reasoning = _parse(raw, ALL_PLATFORMS)
    assert needs_research is False
    assert post_types["linkedin"] == "project_showcase"
    assert post_types["x"] == "thread"
    assert post_types["medium"] == "case_study"
    assert reasoning == "test"


def test_parse_invalid_type_falls_back_to_default():
    raw = _make_raw(True, {"linkedin": "NOT_A_TYPE", "x": "single_shot", "medium": "opinion"})
    _, post_types, _ = _parse(raw, ALL_PLATFORMS)
    assert post_types["linkedin"] == DEFAULT_TYPE["linkedin"]
    assert post_types["x"] == "single_shot"       # valid — kept
    assert post_types["medium"] == "opinion"      # valid — kept


def test_parse_missing_platform_falls_back_to_default():
    # Router only returned types for linkedin and x, missing medium
    raw = _make_raw(False, {"linkedin": "hot_take", "x": "hot_take"})
    _, post_types, _ = _parse(raw, ALL_PLATFORMS)
    assert post_types["medium"] == DEFAULT_TYPE["medium"]


def test_parse_broken_json_returns_all_defaults():
    _, post_types, reasoning = _parse("not json at all", ALL_PLATFORMS)
    for platform in ALL_PLATFORMS:
        assert post_types[platform] == DEFAULT_TYPE[platform]
    assert reasoning == ""


def test_parse_markdown_fenced_json():
    raw = "```json\n" + _make_raw(True, {"linkedin": "learning", "x": "single_shot", "medium": "tutorial"}) + "\n```"
    needs_research, post_types, _ = _parse(raw, ALL_PLATFORMS)
    assert needs_research is True
    assert post_types["linkedin"] == "learning"


def test_parse_subset_of_platforms():
    raw = _make_raw(False, {"linkedin": "milestone"})
    _, post_types, _ = _parse(raw, ["linkedin"])
    assert "x" not in post_types
    assert "medium" not in post_types
    assert post_types["linkedin"] == "milestone"


def test_all_allowed_types_are_valid():
    """Every value in ALLOWED_TYPES should survive a round-trip through _parse."""
    for platform, types in ALLOWED_TYPES.items():
        for t in types:
            raw = _make_raw(False, {platform: t})
            _, post_types, _ = _parse(raw, [platform])
            assert post_types[platform] == t, f"Round-trip failed for {platform}/{t}"


# ---------------------------------------------------------------------------
# Integration tests — real Groq calls
# ---------------------------------------------------------------------------

FIXTURE_INPUTS = [
    # (description, context, expected_linkedin_types_hint)
    ("project_ship",   "I just open-sourced my prompt injection scanner. 89% pre-LLM catch rate, 59 tests.", ["project_showcase"]),
    ("event_attend",   "I attended the AI Engineer World's Fair yesterday. Karpathy talked about context as the new compute.", ["event_recap"]),
    ("learning_debug", "Spent 3 weeks chasing an agent bug. Turned out to be one missing sentence in my system prompt.", ["learning"]),
    ("hot_take_rag",   "RAG is not a retrieval problem. It's a data-modelling problem. Most teams learn this the hard way.", ["hot_take", "technical_deep_dive"]),
    ("tutorial_intent","Here's how to build a LangGraph fan-out with multi-provider cascade: step 1 define state...", ["technical_deep_dive"]),
    ("research_news",  "What's new in the Claude API this month?", ["technical_deep_dive", "deep_analysis"]),
    ("milestone_job",  "I'm joining Anthropic as a solutions engineer next month.", ["milestone"]),
    ("deep_dive",      "Explaining why fixed-size chunking in RAG throws away the document structure your model actually needs.", ["technical_deep_dive"]),
    ("case_study",     "I built an 8-agent JUnit test generator. Cut Gemini 2.5 Pro token costs by 40%. Here's what I learned.", ["project_showcase", "case_study"]),
    ("live_event",     "Karpathy on stage right now: 'the next unlock is context engineering, not bigger models'.", ["event_recap", "hot_take"]),
]


@pytest.mark.integration
@pytest.mark.parametrize("description,context,acceptable_linkedin", FIXTURE_INPUTS)
async def test_router_returns_valid_types(description, context, acceptable_linkedin):
    """
    Makes a real Groq call and asserts all returned types are in ALLOWED_TYPES.
    acceptable_linkedin is a hint for the assertion — we assert the type is valid,
    not that it exactly matches (the model has latitude on ambiguous inputs).
    """
    import os
    from app.config import settings

    if not settings.groq_api_key:
        pytest.skip("GROQ_API_KEY not set")

    os.environ["GROQ_API_KEY"] = settings.groq_api_key

    from app.graph.nodes.router import router as router_node
    from app.graph.state import AgentState

    state = AgentState(
        context_input=context,
        platforms=ALL_PLATFORMS,
        run_id=f"test-{description}",
    )
    result = await router_node(state)

    post_types: dict[str, str] = result["post_types"]
    for platform in ALL_PLATFORMS:
        assert platform in post_types, f"{platform} missing from post_types"
        assert post_types[platform] in ALLOWED_TYPES[platform], (
            f"{platform}: {post_types[platform]!r} not in ALLOWED_TYPES"
        )
