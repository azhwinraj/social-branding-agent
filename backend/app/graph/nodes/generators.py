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
    if "x" not in state.platforms:
        return {}
    messages = [
        {"role": "system", "content": load("x_gen.md")},
        {"role": "user", "content": state.context_input},
    ]
    with SessionLocal() as db:
        content, meta = await call("x_gen", "x", messages, state.run_id, db)
    return {"platform": "x", "content": content, **meta}


async def _medium(state: AgentState) -> dict:
    if "medium" not in state.platforms:
        return {}
    messages = [
        {"role": "system", "content": load("medium_gen.md")},
        {"role": "user", "content": state.context_input},
    ]
    with SessionLocal() as db:
        content, meta = await call("medium_gen", "medium", messages, state.run_id, db)
    return {"platform": "medium", "content": content, **meta}


async def generators(state: AgentState) -> dict:
    results = await asyncio.gather(_linkedin(state), _x(state), _medium(state))
    drafts = [r for r in results if r.get("content")]
    return {"drafts": drafts}
