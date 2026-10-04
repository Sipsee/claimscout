import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.config import Settings, pick_model
from agent.ics import deadlines_ics
from agent.llm import _extract_json
from agent.models import Match, Settlement, UserProfile
from agent.pipeline import dedupe, scout, sort_matches
from agent.search import rank_urls


def S(name, deadline="2099-01-01"):
    return Settlement(name=name, who_qualifies="x", deadline=deadline)


def test_pick_model_prefers_order_and_skips_omni():
    avail = ["meta-llama/Llama-3.3-70B", "nvidia/nemotron-3-nano-omni", "nvidia/nemotron-3-nano-30b-a3b",
             "nvidia/nemotron-3-ultra-550b-a55b"]
    assert pick_model(avail, ["nemotron-3-ultra", "nemotron"]) == "nvidia/nemotron-3-ultra-550b-a55b"
    assert pick_model(avail, ["nemotron-3-nano"]) == "nvidia/nemotron-3-nano-30b-a3b"
    assert pick_model(["gpt"], ["nemotron"]) is None


def test_extract_json_handles_think_and_fences():
    assert _extract_json('<think>hmm {"a":0}</think>```json\n{"a": 1}\n```') == {"a": 1}
    assert _extract_json('Sure! [1, 2]') == [1, 2]


def test_dedupe_and_sort():
    a, b = S("$15M Levoit air purifier settlement"), S("Levoit air purifier settlement $15M")
    assert len(dedupe([a, b])) == 1
    ms = [Match(settlement=S("A", "2026-12-01"), verdict="maybe", reason="", confidence=0.9),
          Match(settlement=S("B", "2026-11-01"), verdict="likely", reason="", confidence=0.5),
          Match(settlement=S("C", "2026-10-20"), verdict="likely", reason="", confidence=0.5)]
    assert [m.settlement.name for m in sort_matches(ms)] == ["C", "B", "A"]


def test_rank_urls_prefers_settlement_pages():
    hits = [{"url": "https://blog.example.com/x", "score": 0.9},
            {"url": "https://topclassactions.com/y", "score": 0.5},
            {"url": "https://blog.example.com/x", "score": 0.9}]
    assert rank_urls(hits, 5) == ["https://topclassactions.com/y", "https://blog.example.com/x"]


def test_demo_mode_end_to_end():
    st = Settings(nebius_key="", tavily_key="")
    r = scout(UserProfile(brands_and_products="Levoit air purifier", stores_and_services="CVS ExtraCare"), st)
    names = [m.settlement.name for m in r.matches]
    assert r.demo_mode and len(names) == 2 and any("Levoit" in n for n in names)
    assert scout(UserProfile(), st).matches == []


def test_ics_has_reminder_three_days_early():
    m = Match(settlement=S("Test, settlement", "2026-11-03"), verdict="likely", reason="")
    ics = deadlines_ics([m])
    assert "DTSTART;VALUE=DATE:20261031" in ics and "Test\\, settlement" in ics


def test_live_pipeline_with_fakes(monkeypatch):
    import agent.llm, agent.search

    class FakeLLM:
        fast_model, reason_model = "nvidia/nemotron-3-nano", "nvidia/nemotron-3-ultra"
        def __init__(self, settings): pass
        def json(self, system, user, reasoning=False, max_tokens=0):
            if "planner" in system:
                return {"queries": ["levoit settlement", "kia settlement"]}
            if "extract" in system:
                return {"settlements": [
                    {"name": "Levoit purifier settlement", "who_qualifies": "Levoit buyers", "deadline": "2099-11-03"},
                    {"name": "Old expired settlement", "who_qualifies": "anyone", "deadline": "2001-01-01"}]}
            return {"matches": [{"index": 0, "verdict": "likely", "reason": "owns Levoit", "confidence": 0.9}]}

    class FakeWeb:
        def __init__(self, key): pass
        def search(self, q, max_results=5): return [{"url": f"https://topclassactions.com/{q}", "score": 1}]
        def extract(self, urls): return {u: "page text" for u in urls}

    monkeypatch.setattr(agent.llm, "LLM", FakeLLM)
    monkeypatch.setattr(agent.search, "Researcher", FakeWeb)
    r = scout(UserProfile(brands_and_products="Levoit"), Settings(nebius_key="k", tavily_key="k"))
    assert not r.demo_mode and r.settlements_found == 1
    assert r.matches[0].verdict == "likely" and r.matches[0].settlement.source_url.startswith("https://topclassactions.com/")
