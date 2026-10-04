"""Live web research with Tavily: search for open settlements, then extract page text."""
from __future__ import annotations

TRUSTED_HINTS = ("topclassactions.com", "classaction.org", "settlement", "claimdepot.com", "ftc.gov")


class Researcher:
    def __init__(self, api_key: str):
        from tavily import TavilyClient
        self.client = TavilyClient(api_key=api_key)

    def search(self, query: str, max_results: int = 5) -> list[dict]:
        res = self.client.search(query=query, search_depth="advanced", max_results=max_results,
                                 topic="general", days=120)
        return res.get("results", [])

    def extract(self, urls: list[str]) -> dict[str, str]:
        if not urls:
            return {}
        res = self.client.extract(urls=urls[:20])
        return {r["url"]: r.get("raw_content", "")[:12000] for r in res.get("results", [])}


def rank_urls(results: list[dict], limit: int) -> list[str]:
    """Dedupe search hits and prefer settlement-specific pages."""
    seen, scored = set(), []
    for r in results:
        url = r.get("url", "")
        if not url or url in seen:
            continue
        seen.add(url)
        bonus = 1.0 if any(h in url.lower() for h in TRUSTED_HINTS) else 0.0
        scored.append((r.get("score", 0) + bonus, url))
    return [u for _, u in sorted(scored, reverse=True)[:limit]]
