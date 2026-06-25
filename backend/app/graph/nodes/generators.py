import asyncio

from app.db.session import SessionLocal
from app.graph.state import AgentState
from app.llm.cascade import call
from app.llm.prompts import load


async def _linkedin(state: AgentState) -> dict:
    if "linkedin" not in state.platforms:
        return {}
    messages = [
        {"role": "system", "content": load("linkedin_gen.md")},
        {"role": "user", "content": state.context_input},
    ]
    with SessionLocal() as db:
        content, meta = await call("linkedin_gen", "linkedin", messages, state.run_id, db)
    return {"platform": "linkedin", "content": content, **meta}


async def _x(state: AgentState) -> dict:
    return {}  # Phase C


async def _medium(state: AgentState) -> dict:
    return {}  # Phase C


async def generators(state: AgentState) -> dict:
    results = await asyncio.gather(_linkedin(state), _x(state), _medium(state))
    drafts = [r for r in results if r.get("content")]
    return {"drafts": drafts}
