from __future__ import annotations

import json

from app.db.session import SessionLocal
from app.evals.adherence.by_type import check_by_type
from app.graph.state import AgentState
from app.llm.cascade import call
from app.llm.post_types import ALLOWED_TYPES, DEFAULT_TYPE
from app.llm.prompts import load

_BANNED_OPENERS = [
    "i'm excited to share",
    "thrilled to announce",
    "happy to announce",
    "pleased to share",
    "i am excited",
    "delighted to",
]


def _check_linkedin(content: str) -> list[str]:
    issues: list[str] = []
    words = len(content.split())
    if words < 50:
        issues.append(f"Too short ({words} words). Write at least 50 words.")
    if words > 600:
        issues.append(f"Too long ({words} words). Keep it under 600 words.")
    if any(content.lower().lstrip().startswith(b) for b in _BANNED_OPENERS):
        issues.append("Starts with a generic opener. Begin with something specific and direct.")
    if "#" not in content:
        issues.append("Missing hashtags. Add 2–3 relevant hashtags at the end.")
    return issues


def _check_x(content: str) -> list[str]:
    """Check per-tweet character limits. Handles both JSON array and plain text formats."""
    issues: list[str] = []
    # JSON array format (used by x/thread prompt)
    try:
        parsed = json.loads(content.strip())
        if isinstance(parsed, list):
            for i, tweet in enumerate(parsed, 1):
                if len(str(tweet)) > 280:
                    issues.append(f"Tweet {i} is {len(str(tweet))} chars — max is 280.")
            return issues
    except (json.JSONDecodeError, ValueError):
        pass
    # Plain text, blank-line-separated
    tweets = [t.strip() for t in content.split("\n\n") if t.strip()]
    for i, tweet in enumerate(tweets, 1):
        if len(tweet) > 280:
            issues.append(f"Tweet {i} is {len(tweet)} chars — max is 280.")
    return issues


def _check_medium(content: str) -> list[str]:
    issues: list[str] = []
    words = len(content.split())
    if words < 200:
        issues.append(f"Too short ({words} words). Medium articles need at least 200 words.")
    lines = [ln for ln in content.strip().splitlines() if ln.strip()]
    if len(lines) < 3:
        issues.append("Needs more paragraphs. Aim for at least 3 distinct paragraphs.")
    return issues


_PLATFORM_CHECKERS = {
    "linkedin": _check_linkedin,
    "x":        _check_x,
    "medium":   _check_medium,
}


def _all_issues(platform: str, post_type: str, content: str) -> list[str]:
    """Platform-level rules + type-specific rules, combined."""
    issues: list[str] = []
    checker = _PLATFORM_CHECKERS.get(platform)
    if checker:
        issues.extend(checker(content))
    issues.extend(check_by_type(platform, post_type, content))
    return issues


def _resolve_prompt_path(platform: str, post_type: str) -> str:
    if post_type in ALLOWED_TYPES.get(platform, []):
        return f"{platform}/{post_type}.md"
    fallback = DEFAULT_TYPE.get(platform, "")
    if fallback:
        return f"{platform}/{fallback}.md"
    return f"{platform}_gen.md"   # last-resort: legacy flat file


async def _retry(platform: str, post_type: str, draft: dict, issues: list[str], state: AgentState) -> dict | None:
    issue_text = "\n".join(f"- {i}" for i in issues)
    messages = [
        {"role": "system", "content": load(_resolve_prompt_path(platform, post_type))},
        {"role": "user", "content": state.context_input},
        {"role": "assistant", "content": draft["content"]},
        {
            "role": "user",
            "content": f"That draft has these issues:\n{issue_text}\n\nPlease fix them and rewrite.",
        },
    ]
    try:
        with SessionLocal() as db:
            content, meta = await call(
                f"{platform}_gen_retry", platform, messages, state.run_id, db, state.quality_mode
            )
        return {"platform": platform, "post_type": post_type, "content": content, **meta}
    except Exception:
        return None


async def adherence(state: AgentState) -> dict:
    if not state.drafts:
        return {}

    checked: list[dict] = []
    for draft in state.drafts:
        platform = draft.get("platform", "")
        post_type = draft.get("post_type", "")

        issues = _all_issues(platform, post_type, draft["content"])
        if not issues:
            checked.append(draft)
            continue

        retried = await _retry(platform, post_type, draft, issues, state)
        if retried:
            remaining = _all_issues(platform, post_type, retried["content"])
            if remaining:
                retried["adherence_warning"] = True
            checked.append(retried)
        else:
            checked.append({**draft, "adherence_warning": True})

    return {"drafts": checked}
