import os
from langgraph.graph import StateGraph, END

from app.config import settings
from app.graph.state import AgentState
from app.graph.nodes.generators import generators
from app.graph.nodes.aggregator import aggregator


def _stub_node(name: str):
    async def node(state: AgentState) -> dict:
        return {}
    node.__name__ = name
    return node


def _setup_tracing():
    if settings.langchain_api_key:
        os.environ.setdefault("LANGCHAIN_API_KEY", settings.langchain_api_key)
        os.environ.setdefault("LANGCHAIN_TRACING_V2", settings.langchain_tracing_v2)
        os.environ.setdefault("LANGCHAIN_PROJECT", settings.langchain_project)


def build_graph():
    _setup_tracing()

    builder = StateGraph(AgentState)

    # Phase B: router and adherence are stubs; generators + aggregator are wired
    # Phase C will wire adherence; Phase D will wire style_memory; Phase E will wire research
    builder.add_node("router", _stub_node("router"))
    builder.add_node("generators", generators)
    builder.add_node("adherence", _stub_node("adherence"))
    builder.add_node("aggregator", aggregator)

    builder.set_entry_point("router")
    builder.add_edge("router", "generators")
    builder.add_edge("generators", "adherence")
    builder.add_edge("adherence", "aggregator")
    builder.add_edge("aggregator", END)

    return builder.compile()


graph = build_graph()
