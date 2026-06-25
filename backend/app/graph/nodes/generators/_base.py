from __future__ import annotations


def _user_message(context: str, research: str, examples: list[str]) -> str:
    parts = [context]
    if research:
        parts.append(f"Current research on this topic:\n{research}")
    if examples:
        ex_block = "\n\n---\n\n".join(examples)
        parts.append(
            "Here are examples of past approved posts in this person's voice"
            f" — match the style:\n\n{ex_block}"
        )
    return "\n\n".join(parts)
