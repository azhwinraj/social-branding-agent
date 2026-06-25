from __future__ import annotations

ALLOWED_TYPES: dict[str, list[str]] = {
    "linkedin": [
        "project_showcase",
        "technical_deep_dive",
        "learning",
        "event_recap",
        "hot_take",
        "milestone",
    ],
    "x": [
        "thread",
        "single_shot",
        "hot_take",
        "link_share",
        "live_event",
    ],
    "medium": [
        "tutorial",
        "case_study",
        "opinion",
        "deep_analysis",
    ],
}

# Fallback used when the router returns an unknown or missing type.
DEFAULT_TYPE: dict[str, str] = {
    "linkedin": "technical_deep_dive",
    "x": "single_shot",
    "medium": "opinion",
}
