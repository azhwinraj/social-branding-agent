"""
Tests for type-specific adherence rules (by_type.py) and their integration
with platform-level rules via _all_issues().
"""
from __future__ import annotations

import json

import pytest

from app.evals.adherence.by_type import (
    check_by_type,
    _check_has_metric,
    _check_event_has_specific_reference,
    _check_thread_has_multiple_tweets,
    _check_tutorial_has_code,
)
from app.graph.nodes.adherence import _all_issues, _resolve_prompt_path


# ---------------------------------------------------------------------------
# linkedin/project_showcase — must contain a number/metric
# ---------------------------------------------------------------------------

def test_project_showcase_passes_with_metric():
    assert _check_has_metric("We cut latency by 40% using async batching.") == []


def test_project_showcase_passes_with_bare_number():
    assert _check_has_metric("I ran 59 tests across three edge-case categories.") == []


def test_project_showcase_fails_without_metric():
    issues = _check_has_metric("I shipped a tool that makes RAG pipelines faster.")
    assert len(issues) == 1
    assert "number" in issues[0].lower() or "metric" in issues[0].lower()


def test_check_by_type_project_showcase_pass():
    assert check_by_type("linkedin", "project_showcase", "Reduced cost by 60%.") == []


def test_check_by_type_project_showcase_fail():
    issues = check_by_type("linkedin", "project_showcase", "No numbers here at all.")
    assert len(issues) >= 1


# ---------------------------------------------------------------------------
# linkedin/event_recap — must reference a specific person / talk / session
# ---------------------------------------------------------------------------

def test_event_recap_passes_with_proper_noun():
    content = "Andrej Karpathy said context is the new compute."
    assert _check_event_has_specific_reference(content) == []


def test_event_recap_passes_with_quote():
    content = 'The talk ended with "RAG is a retrieval problem, not a generation one."'
    assert _check_event_has_specific_reference(content) == []


def test_event_recap_passes_with_mid_sentence_name():
    # "by Google" — capitalized mid-sentence
    content = "The demo by Google showed a 10x speedup on embedding retrieval."
    assert _check_event_has_specific_reference(content) == []


def test_event_recap_fails_with_no_specific_reference():
    content = "Great event today. Lots of interesting talks about agents and models."
    issues = _check_event_has_specific_reference(content)
    assert len(issues) == 1
    assert "speaker" in issues[0].lower() or "name" in issues[0].lower()


# ---------------------------------------------------------------------------
# x/thread — must have 3+ tweets
# ---------------------------------------------------------------------------

def test_thread_passes_json_array_3_tweets():
    content = json.dumps(["Tweet one.", "Tweet two.", "Tweet three."])
    assert _check_thread_has_multiple_tweets(content) == []


def test_thread_passes_json_array_5_tweets():
    content = json.dumps([f"Tweet {i}." for i in range(5)])
    assert _check_thread_has_multiple_tweets(content) == []


def test_thread_fails_json_array_2_tweets():
    content = json.dumps(["Only one.", "And two."])
    issues = _check_thread_has_multiple_tweets(content)
    assert len(issues) == 1
    assert "2" in issues[0]


def test_thread_passes_plain_text_3_tweets():
    content = "Tweet one.\n\nTweet two.\n\nTweet three."
    assert _check_thread_has_multiple_tweets(content) == []


def test_thread_fails_plain_text_1_tweet():
    content = "Just one long tweet with no separators."
    issues = _check_thread_has_multiple_tweets(content)
    assert len(issues) == 1


def test_check_by_type_thread_pass():
    content = json.dumps(["T1", "T2", "T3", "T4"])
    assert check_by_type("x", "thread", content) == []


# ---------------------------------------------------------------------------
# medium/tutorial — must contain code blocks
# ---------------------------------------------------------------------------

def test_tutorial_passes_with_code_block():
    content = "Here is how:\n\n```python\nprint('hello')\n```\n\nDone."
    assert _check_tutorial_has_code(content) == []


def test_tutorial_fails_without_code_block():
    issues = _check_tutorial_has_code("This tutorial explains things but has no code.")
    assert len(issues) == 1
    assert "```" in issues[0]


def test_check_by_type_tutorial_fail():
    issues = check_by_type("medium", "tutorial", "No code here.")
    assert len(issues) >= 1


# ---------------------------------------------------------------------------
# medium/case_study — must contain a number/metric
# ---------------------------------------------------------------------------

def test_case_study_passes_with_metric():
    assert check_by_type("medium", "case_study", "Latency dropped from 4.2s to 0.8s.") == []


def test_case_study_fails_without_metric():
    issues = check_by_type("medium", "case_study", "It was much faster after the change.")
    assert len(issues) >= 1


# ---------------------------------------------------------------------------
# Types with no rules — check_by_type returns [] for them
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("platform,post_type", [
    ("linkedin", "technical_deep_dive"),
    ("linkedin", "learning"),
    ("linkedin", "hot_take"),
    ("linkedin", "milestone"),
    ("x", "single_shot"),
    ("x", "hot_take"),
    ("x", "link_share"),
    ("x", "live_event"),
    ("medium", "opinion"),
    ("medium", "deep_analysis"),
])
def test_no_type_rules_returns_empty(platform, post_type):
    assert check_by_type(platform, post_type, "any content") == []


# ---------------------------------------------------------------------------
# _all_issues — platform + type rules combined
# ---------------------------------------------------------------------------

def test_all_issues_combines_platform_and_type_rules():
    # linkedin/project_showcase with no hashtags AND no metric — should get both issues
    content = "I built a tool. It works great."   # short, no #, no metric
    issues = _all_issues("linkedin", "project_showcase", content)
    issue_text = " ".join(issues)
    assert any("hashtag" in i.lower() or "#" in i for i in issues), "Expected hashtag issue"
    assert any("number" in i.lower() or "metric" in i.lower() for i in issues), "Expected metric issue"


def test_all_issues_clean_draft_has_no_issues():
    content = (
        "Reduced inference cost by 40% using a 3-layer pre-filter pipeline. "
        "Here's what made it work: first, a regex layer catches the obvious junk. "
        "Then a small classifier handles edge cases. Finally, the LLM only sees clean input.\n\n"
        "The result: 89% of attacks caught before the model. Zero false positives in prod.\n\n"
        "#AIEngineering #LLMSecurity #AgentDesign"
    )
    assert _all_issues("linkedin", "project_showcase", content) == []


# ---------------------------------------------------------------------------
# _resolve_prompt_path — falls back correctly
# ---------------------------------------------------------------------------

def test_resolve_prompt_path_known_type():
    assert _resolve_prompt_path("linkedin", "project_showcase") == "linkedin/project_showcase.md"


def test_resolve_prompt_path_unknown_type_uses_default():
    path = _resolve_prompt_path("linkedin", "NONEXISTENT")
    assert path == "linkedin/technical_deep_dive.md"   # DEFAULT_TYPE["linkedin"]


def test_resolve_prompt_path_unknown_platform_uses_legacy():
    path = _resolve_prompt_path("tiktok", "")
    assert path == "tiktok_gen.md"
