from typing import Annotated
from dataclasses import dataclass, field
from operator import add


@dataclass
class AgentState:
    context_input: str = ""
    platforms: list[str] = field(default_factory=list)
    needs_research: bool = False
    research_results: str = ""
    style_examples: dict[str, list[str]] = field(default_factory=dict)
    drafts: Annotated[list[dict], add] = field(default_factory=list)
    run_id: str = ""
