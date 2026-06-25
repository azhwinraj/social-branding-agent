from __future__ import annotations

from app.graph.state import AgentState
from app.research.tavily import search


def _format(results: list[dict]) -> str:
    if not results:
        return ""
    lines = []
    for r in results:
        title = r.get("title", "")
        url = r.get("url", "")
        snippet = r.get("content", "")[:300]
        lines.append(f"- {title} ({url})\n  {snippet}")
    return "\n\n".join(lines)


async def research(state: AgentState) -> dict:
    if not state.needs_research:
        return {}
    try:
        results = await search(state.context_input, max_results=5)
        return {"research_results": _format(results)}
    except Exception:
        return {}
