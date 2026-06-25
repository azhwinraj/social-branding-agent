from functools import lru_cache
from pathlib import Path

_DIR = Path(__file__).parent


@lru_cache(maxsize=None)
def load(filename: str) -> str:
    return (_DIR / filename).read_text(encoding="utf-8")
