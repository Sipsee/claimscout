"""Thin wrapper around Nebius Token Factory's OpenAI-compatible API."""
from __future__ import annotations

import json
import re
from typing import Any

from .config import NEBIUS_BASE_URL, FAST_PREFS, REASON_PREFS, Settings, pick_model


def _extract_json(text: str) -> Any:
    """Pull the first JSON object or array out of a model reply."""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.S)
    if fence:
        text = fence.group(1).strip()
    for opener, closer in (("{", "}"), ("[", "]")):
        start, end = text.find(opener), text.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError(f"Model did not return JSON: {text[:200]}")


class LLM:
    def __init__(self, settings: Settings):
        from openai import OpenAI
        self.client = OpenAI(base_url=NEBIUS_BASE_URL, api_key=settings.nebius_key)
        fast, reason = settings.fast_model, settings.reason_model
        if not (fast and reason):
            available = [m.id for m in self.client.models.list().data]
            fast = fast or pick_model(available, FAST_PREFS)
            reason = reason or pick_model(available, REASON_PREFS) or fast
        if not fast:
            raise RuntimeError("No NVIDIA Nemotron model found on Token Factory. Set FAST_MODEL / REASON_MODEL.")
        self.fast_model, self.reason_model = fast, reason

    def json(self, system: str, user: str, *, reasoning: bool = False, max_tokens: int = 2500) -> Any:
        model = self.reason_model if reasoning else self.fast_model
        last_err: Exception | None = None
        for _ in range(2):
            resp = self.client.chat.completions.create(
                model=model,
                temperature=0.1,
                max_tokens=max_tokens,
                messages=[{"role": "system", "content": system + "\nRespond with JSON only."},
                          {"role": "user", "content": user}],
            )
            try:
                return _extract_json(resp.choices[0].message.content or "")
            except ValueError as e:
                last_err = e
        raise last_err  # type: ignore[misc]
