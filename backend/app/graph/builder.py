import os
from langgraph.graph import StateGraph, END
from langsmith import Client as LangSmithClient
from app.graph.state import AgentState
from app.config import settings


def _get_callbacks():
    if not settings.langchain_api_key:
        return []
    os.environ.setdefault("LANGCHAIN_API_KEY", settings.langchain_api_key)
    os.environ.setdefault("LANGCHAIN_TRACING_V2", settings.langchain_tracing_v2)
    os.environ.setdefault("LANGCHAIN_PROJECT", settings.langchain_project)
    return []


def _stub_node(name: str):
    def node(state: AgentState) -> dict:
        return {}
    node.__name__ = name
    return node


def build_graph():
    callbacks = _get_callbacks()

    builder = StateGraph(AgentState)

    builder.add_node("router", _stub_node("router"))
    builder.add_node("research", _stub_node("research"))
    builder.add_node("style_memory", _stub_node("style_memory"))
    builder.add_node("linkedin_gen", _stub_node("linkedin_gen"))
    builder.add_node("x_gen", _stub_node("x_gen"))
    builder.add_node("medium_gen", _stub_node("medium_gen"))
    builder.add_node("adherence", _stub_node("adherence"))
    builder.add_node("aggregator", _stub_node("aggregator"))

    builder.set_entry_point("router")
    builder.add_edge("router", "research")
    builder.add_edge("research", "style_memory")
    builder.add_edge("style_memory", "linkedin_gen")
    builder.add_edge("style_memory", "x_gen")
    builder.add_edge("style_memory", "medium_gen")
    builder.add_edge("linkedin_gen", "adherence")
    builder.add_edge("x_gen", "adherence")
    builder.add_edge("medium_gen", "adherence")
    builder.add_edge("adherence", "aggregator")
    builder.add_edge("aggregator", END)

    return builder.compile()


graph = build_graph()
