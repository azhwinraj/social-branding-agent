from __future__ import annotations

import asyncio

from app.graph.nodes.generators.linkedin import _linkedin
from app.graph.nodes.generators.medium import _medium
from app.graph.nodes.generators.x import _x
from app.graph.state import AgentState


async def generators(state: AgentState) -> dict:
    results = await asyncio.gather(_linkedin(state), _x(state), _medium(state))
    drafts = [r for r in results if r.get("content")]
    return {"drafts": drafts}
