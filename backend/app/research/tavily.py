from __future__ import annotations

import httpx

from app.config import settings

_BASE = "https://api.tavily.com"


async def search(query: str, max_results: int = 5) -> list[dict]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"{_BASE}/search",
            json={
                "api_key": settings.tavily_api_key,
                "query": query,
                "search_depth": "basic",
                "max_results": max_results,
                "include_answer": True,
            },
        )
        resp.raise_for_status()
        return resp.json().get("results", [])
