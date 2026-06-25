from __future__ import annotations

import asyncio
from functools import partial

import httpx

from app.config import settings


def _desktop_toast(platform: str, preview: str) -> None:
    try:
        from plyer import notification
        notification.notify(
            title=f"Time to post on {platform.capitalize()}!",
            message=preview[:200],
            app_name="Social Branding Agent",
            timeout=10,
        )
    except Exception:
        pass


async def _ntfy(platform: str, preview: str) -> None:
    if not settings.ntfy_topic:
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"https://ntfy.sh/{settings.ntfy_topic}",
                content=f"Time to post on {platform.capitalize()}!\n\n{preview[:300]}",
                headers={"Title": f"Post it! ({platform})"},
            )
    except Exception:
        pass


async def notify(draft_id: int, platform: str, content: str) -> None:
    preview = content[:200]
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, partial(_desktop_toast, platform, preview))
    await _ntfy(platform, preview)
