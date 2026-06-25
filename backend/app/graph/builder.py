import os
from langgraph.graph import StateGraph, END

from app.config import settings
from app.graph.state import AgentState
from app.graph.nodes.router import router
from app.graph.nodes.research import research
from app.graph.nodes.style_memory import style_memory
from app.graph.nodes.generators import generators
from app.graph.nodes.adherence import adherence
from app.graph.nodes.aggregator import aggregator


def _research_route(state: AgentState) -> str:
    return "research" if state.needs_research else "style_memory"


def _setup_tracing():
    if settings.langchain_api_key:
        os.environ.setdefault("LANGCHAIN_API_KEY", settings.langchain_api_key)
        os.environ.setdefault("LANGCHAIN_TRACING_V2", settings.langchain_tracing_v2)
        os.environ.setdefault("LANGCHAIN_PROJECT", settings.langchain_project)


def build_graph():
    _setup_tracing()

    builder = StateGraph(AgentState)

    builder.add_node("router", router)
    builder.add_node("research", research)
    builder.add_node("style_memory", style_memory)
    builder.add_node("generators", generators)
    builder.add_node("adherence", adherence)
    builder.add_node("aggregator", aggregator)

    builder.set_entry_point("router")
    builder.add_conditional_edges(
        "router",
        _research_route,
        {"research": "research", "style_memory": "style_memory"},
    )
    builder.add_edge("research", "style_memory")
    builder.add_edge("style_memory", "generators")
    builder.add_edge("generators", "adherence")
    builder.add_edge("adherence", "aggregator")
    builder.add_edge("aggregator", END)

    return builder.compile()


graph = build_graph()
