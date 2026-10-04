"""ClaimScout agent: plan -> research -> extract -> match -> rank.

Each stage runs on an NVIDIA Nemotron model served by Nebius Token Factory. Web research uses Tavily.
Without API keys the pipeline runs in demo mode against a bundled snapshot, so the app always works.
"""
from __future__ import annotations

import datetime as dt
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Optional

from .config import Settings
from .models import Match, ScoutResult, Settlement, UserProfile
from .prompts import EXTRACT_SYSTEM, MATCH_SYSTEM, PLAN_SYSTEM
from .search import rank_urls

UNCLAIMED_URL = "https://www.missingmoney.com/"
SNAPSHOT = Path(__file__).resolve().parent.parent / "data" / "sample_settlements.json"
VERDICT_ORDER = {"likely": 0, "maybe": 1, "unlikely": 2}

Log = Callable[[str], None]


def _today() -> dt.date:
    return dt.date.today()


def _not_expired(s: Settlement, today: dt.date) -> bool:
    try:
        return dt.date.fromisoformat(s.deadline) >= today
    except ValueError:
        return True  # unknown deadline: keep it, the user can check


def dedupe(settlements: list[Settlement]) -> list[Settlement]:
    out: dict[str, Settlement] = {}
    for s in settlements:
        key = " ".join(sorted(w for w in s.name.lower().replace("$", " ").split() if len(w) > 3))
        if key and key not in out:
            out[key] = s
    return list(out.values())


def sort_matches(matches: list[Match]) -> list[Match]:
    def key(m: Match):
        try:
            d = dt.date.fromisoformat(m.settlement.deadline).toordinal()
        except ValueError:
            d = 10**9
        return (VERDICT_ORDER[m.verdict], -m.confidence, d)
    return sorted(matches, key=key)


# ---------------------------------------------------------------- live mode
def run_live(profile: UserProfile, settings: Settings, log: Log) -> ScoutResult:
    from .llm import LLM
    from .search import Researcher

    llm, web = LLM(settings), Researcher(settings.tavily_key)
    today = _today()
    log(f"Models: planner/extractor = {llm.fast_model}, eligibility judge = {llm.reason_model}")

    plan = llm.json(PLAN_SYSTEM.replace("MAX", str(settings.max_queries)),
                    f"TODAY: {today}\n\n{profile.as_text()}")
    queries = [q for q in plan.get("queries", []) if isinstance(q, str)][: settings.max_queries]
    log(f"Planned {len(queries)} searches: " + "; ".join(queries))

    with ThreadPoolExecutor(max_workers=5) as pool:
        hits = [h for batch in pool.map(web.search, queries) for h in batch]
    urls = rank_urls(hits, settings.max_pages)
    log(f"Tavily returned {len(hits)} results; reading the top {len(urls)} pages")
    pages = web.extract(urls)

    def extract(item):
        url, text = item
        try:
            data = llm.json(EXTRACT_SYSTEM, f"TODAY: {today}\nURL: {url}\n\nPAGE:\n{text}")
        except Exception as e:  # one bad page should not sink the run
            log(f"Skipped {url}: {e}")
            return []
        found = []
        for raw in data.get("settlements", []):
            try:
                s = Settlement(**{k: raw.get(k, "") or "" for k in Settlement.model_fields if k != "source_url"},
                               source_url=url)
                found.append(s)
            except Exception:
                continue
        return found

    with ThreadPoolExecutor(max_workers=4) as pool:
        settlements = [s for batch in pool.map(extract, pages.items()) for s in batch]
    settlements = [s for s in dedupe(settlements) if _not_expired(s, today)]
    log(f"Extracted {len(settlements)} open settlements")

    matches = judge(llm, profile, settlements, today, log)
    return ScoutResult(queries=queries, settlements_found=len(settlements), matches=sort_matches(matches),
                       unclaimed_property_url=UNCLAIMED_URL)


def judge(llm, profile: UserProfile, settlements: list[Settlement], today: dt.date, log: Log) -> list[Match]:
    matches: list[Match] = []
    for start in range(0, len(settlements), 8):
        chunk = settlements[start:start + 8]
        listing = "\n".join(f"[{i}] {s.name} | Class: {s.who_qualifies} | Proof: {s.proof_required or 'not stated'}"
                            for i, s in enumerate(chunk))
        data = llm.json(MATCH_SYSTEM, f"TODAY: {today}\n\nPERSON:\n{profile.as_text()}\n\nSETTLEMENTS:\n{listing}",
                        reasoning=True, max_tokens=4000)
        for m in data.get("matches", []):
            try:
                idx = int(m["index"])
                verdict = m.get("verdict", "unlikely")
                if verdict not in VERDICT_ORDER or not 0 <= idx < len(chunk):
                    continue
                matches.append(Match(settlement=chunk[idx], verdict=verdict, reason=m.get("reason", ""),
                                     what_to_check=m.get("what_to_check", ""),
                                     confidence=float(m.get("confidence", 0) or 0)))
            except (KeyError, ValueError, TypeError):
                continue
    log(f"Judged {len(matches)} settlements with {llm.reason_model}")
    return matches


# ---------------------------------------------------------------- demo mode
def run_demo(profile: UserProfile, log: Log) -> ScoutResult:
    """Keyword matching over a bundled snapshot. Used only when API keys are missing."""
    raw = json.loads(SNAPSHOT.read_text())
    settlements = [Settlement(**s) for s in raw["settlements"]]
    log("DEMO MODE: no API keys set, using a bundled snapshot and keyword matching (no AI).")
    stated = " ".join([profile.brands_and_products, profile.stores_and_services,
                       profile.breach_notices, profile.other_notes]).lower()
    matches = []
    for s, keys in zip(settlements, [r["keywords"] for r in raw["settlements"]]):
        hit = next((k for k in keys if k in stated), None)
        if hit:
            matches.append(Match(settlement=s, verdict="maybe", confidence=0.5,
                                 reason=f'You mentioned "{hit}", which this settlement covers.',
                                 what_to_check="Read the class definition and confirm your dates and details before filing."))
    log(f"Snapshot has {len(settlements)} settlements; {len(matches)} keyword matches")
    return ScoutResult(queries=[], settlements_found=len(settlements), matches=sort_matches(matches),
                       unclaimed_property_url=UNCLAIMED_URL, demo_mode=True)


def scout(profile: UserProfile, settings: Optional[Settings] = None, log: Optional[Log] = None) -> ScoutResult:
    settings = settings or Settings()
    trace: list[str] = []

    def _log(msg: str):
        trace.append(msg)
        if log:
            log(msg)

    result = run_demo(profile, _log) if settings.demo_mode else run_live(profile, settings, _log)
    result.trace = trace
    return result
