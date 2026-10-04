"""Configuration and NVIDIA Nemotron model discovery on Nebius Token Factory."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

NEBIUS_BASE_URL = os.getenv("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/")

# Preferred Nemotron models, best first. The fast model plans searches and extracts
# data; the reasoning model makes the eligibility call, where accuracy matters most.
FAST_PREFS = ["nemotron-3-nano", "nemotron-3-super", "nemotron-nano", "nemotron-super", "nemotron"]
REASON_PREFS = ["nemotron-3-ultra", "nemotron-3-super", "nemotron-ultra", "nemotron-super", "nemotron"]


@dataclass
class Settings:
    nebius_key: str = field(default_factory=lambda: os.getenv("NEBIUS_API_KEY", ""))
    tavily_key: str = field(default_factory=lambda: os.getenv("TAVILY_API_KEY", ""))
    fast_model: str = field(default_factory=lambda: os.getenv("FAST_MODEL", ""))
    reason_model: str = field(default_factory=lambda: os.getenv("REASON_MODEL", ""))
    max_queries: int = int(os.getenv("MAX_QUERIES", "5"))
    max_pages: int = int(os.getenv("MAX_PAGES", "8"))

    @property
    def demo_mode(self) -> bool:
        return not (self.nebius_key and self.tavily_key)


def pick_model(available: list[str], prefs: list[str]) -> str | None:
    """Pick the first available model whose id contains a preferred substring.

    Model ids on Token Factory change as NVIDIA ships new Nemotron versions, so we
    discover them at runtime instead of hard-coding one id.
    """
    lowered = [(m, m.lower()) for m in available]
    for pref in prefs:
        hits = [m for m, low in lowered if pref in low and "omni" not in low and "embed" not in low]
        if hits:
            return sorted(hits)[-1]
    return None
