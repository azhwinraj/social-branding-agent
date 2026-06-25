from dataclasses import dataclass, field


@dataclass
class AgentState:
    context_input: str = ""
    platforms: list[str] = field(default_factory=list)
    needs_research: bool = False
    research_override: bool | None = None  # None = auto, True/False = forced
    research_results: str = ""
    style_examples: dict[str, list[str]] = field(default_factory=dict)
    drafts: list[dict] = field(default_factory=list)
    run_id: str = ""
