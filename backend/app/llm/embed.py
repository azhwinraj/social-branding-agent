from __future__ import annotations

import litellm


async def embed(text: str) -> list[float]:
    resp = await litellm.aembedding(model="gemini/text-embedding-004", input=[text])
    return resp.data[0]["embedding"]
