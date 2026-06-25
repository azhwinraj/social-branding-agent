"""
Type-specific adherence rules.

Each rule is a function (content: str) -> list[str] (issues).
BY_TYPE maps (platform, post_type) to a list of rules that run in addition
to the universal platform checks in adherence.py.

Adding a new type rule:
  1. Write a _check_* function below.
  2. Add an entry to BY_TYPE.
  3. Add a passing/failing fixture test in tests/test_adherence_by_type.py.
"""
from __future__ import annotations

import json
import re
from typing import Callable


def _check_has_metric(content: str) -> list[str]:
    """Post must contain at least one specific number or metric."""
    if not re.search(r"\d+", content):
        return [
            "Missing a specific number or metric. Include at least one concrete"
            " data point (e.g. '89%', '3 weeks', '40% cost reduction')."
        ]
    return []


def _check_event_has_specific_reference(content: str) -> list[str]:
    """
    Event recap must reference a specific person, talk, or session.
    Heuristic: a capitalized word that appears mid-sentence (not at the very
    start of a sentence), indicating a proper noun, OR a quoted phrase.
    """
    has_mid_sentence_cap = bool(re.search(r"[a-z,)’”'\"]\s+[A-Z][a-z]+", content))
    has_quote = bool(re.search(r'["“”‘’]', content))
    if not (has_mid_sentence_cap or has_quote):
        return [
            "Event recap should reference a specific speaker, talk, or session by name."
            " Mention at least one person or session title."
        ]
    return []


def _check_thread_has_multiple_tweets(content: str) -> list[str]:
    """
    X thread must contain at least 3 tweets.
    Accepts JSON array format (preferred) or blank-line-separated format.
    """
    # Try JSON array (the x/thread prompt requests this format)
    try:
        parsed = json.loads(content.strip())
        if isinstance(parsed, list):
            count = len(parsed)
            if count >= 3:
                return []
            return [f"Thread has only {count} tweet(s). A thread needs at least 3 tweets."]
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: blank-line-separated plain text
    tweets = [t.strip() for t in content.split("\n\n") if t.strip()]
    if len(tweets) >= 3:
        return []
    return [f"Thread has only {len(tweets)} tweet(s). A thread needs at least 3 tweets."]


def _check_tutorial_has_code(content: str) -> list[str]:
    """Tutorial must contain at least one fenced code block."""
    if "```" not in content:
        return ["Tutorial is missing code blocks. Use ``` fences around all code examples."]
    return []


# ---------------------------------------------------------------------------
# Registry — (platform, post_type) → ordered list of rule functions
# ---------------------------------------------------------------------------

BY_TYPE: dict[tuple[str, str], list[Callable[[str], list[str]]]] = {
    ("linkedin", "project_showcase"): [_check_has_metric],
    ("linkedin", "event_recap"):      [_check_event_has_specific_reference],
    ("x",        "thread"):           [_check_thread_has_multiple_tweets],
    ("medium",   "tutorial"):         [_check_tutorial_has_code],
    ("medium",   "case_study"):       [_check_has_metric],
}


def check_by_type(platform: str, post_type: str, content: str) -> list[str]:
    """Return all type-specific issues for this (platform, post_type) pair."""
    issues: list[str] = []
    for rule in BY_TYPE.get((platform, post_type), []):
        issues.extend(rule(content))
    return issues
