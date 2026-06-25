from __future__ import annotations

from app.db.session import SessionLocal
from app.graph.state import AgentState
from app.llm.cascade import call
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
    if content.lower().lstrip().split()[0:4] and any(
        content.lower().lstrip().startswith(b) for b in _BANNED_OPENERS
    ):
        issues.append("Starts with a generic opener. Begin with something specific and direct.")
    if "#" not in content:
        issues.append("Missing hashtags. Add 2–3 relevant hashtags at the end.")
    return issues


def _check_x(content: str) -> list[str]:
    issues: list[str] = []
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
    lines = [l for l in content.strip().splitlines() if l.strip()]
    if len(lines) < 3:
        issues.append("Needs more paragraphs. Aim for at least 3 distinct paragraphs.")
    return issues


_CHECKERS = {
    "linkedin": _check_linkedin,
    "x": _check_x,
    "medium": _check_medium,
}


async def _retry(platform: str, draft: dict, issues: list[str], state: AgentState) -> dict | None:
    system_prompt = load(f"{platform}_gen.md")
    issue_text = "\n".join(f"- {i}" for i in issues)
    messages = [
        {"role": "system", "content": system_prompt},
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
                f"{platform}_gen_retry", platform, messages, state.run_id, db
            )
        return {"platform": platform, "content": content, **meta}
    except Exception:
        return None


async def adherence(state: AgentState) -> dict:
    if not state.drafts:
        return {}

    checked: list[dict] = []
    for draft in state.drafts:
        platform = draft.get("platform", "")
        checker = _CHECKERS.get(platform)

        if checker is None:
            checked.append(draft)
            continue

        issues = checker(draft["content"])
        if not issues:
            checked.append(draft)
            continue

        retried = await _retry(platform, draft, issues, state)
        if retried:
            remaining = checker(retried["content"])
            if remaining:
                retried["adherence_warning"] = True
            checked.append(retried)
        else:
            checked.append({**draft, "adherence_warning": True})

    return {"drafts": checked}
