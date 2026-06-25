from __future__ import annotations

import json
import re

from app.db.session import SessionLocal
from app.graph.state import AgentState
from app.llm.cascade import call
from app.llm.prompts import load


def _parse(text: str) -> bool:
    text = re.sub(r"```(?:json)?\n?", "", text).strip()
    try:
        return bool(json.loads(text).get("needs_research", False))
    except Exception:
        return False


async def router(state: AgentState) -> dict:
    # User override takes precedence over auto-detection
    if state.research_override is not None:
        return {"needs_research": state.research_override}

    messages = [
        {"role": "system", "content": load("router.md")},
        {"role": "user", "content": state.context_input},
    ]
    try:
        with SessionLocal() as db:
            content, _ = await call("router", "router", messages, state.run_id, db)
        return {"needs_research": _parse(content)}
    except Exception:
        return {"needs_research": False}
