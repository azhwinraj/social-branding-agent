from dataclasses import dataclass, field


@dataclass
class AgentState:
    context_input: str = ""
    platforms: list[str] = field(default_factory=list)
    quality_mode: str = "balanced"       # "fast" | "balanced" | "polish"
    needs_research: bool = False
    research_override: bool | None = None
    research_results: str = ""
    style_examples: dict[str, list[str]] = field(default_factory=dict)
    post_types: dict[str, str] = field(default_factory=dict)      # {"linkedin": "project_showcase", ...}
    router_reasoning: str = ""                                      # surfaced as tooltip in UI
    drafts: list[dict] = field(default_factory=list)
    run_id: str = ""
