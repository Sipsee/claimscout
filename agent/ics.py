"""Turn claim deadlines into a calendar file so nothing expires unnoticed."""
from __future__ import annotations

import datetime as dt

from .models import Match


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace(",", "\\,").replace(";", "\\;").replace("\n", "\\n")


def deadlines_ics(matches: list[Match]) -> str:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//ClaimScout//EN"]
    for i, m in enumerate(matches):
        try:
            day = dt.date.fromisoformat(m.settlement.deadline)
        except ValueError:
            continue
        remind = day - dt.timedelta(days=3)
        lines += [
            "BEGIN:VEVENT", f"UID:claimscout-{i}-{day:%Y%m%d}@claimscout", f"DTSTAMP:{stamp}",
            f"DTSTART;VALUE=DATE:{remind:%Y%m%d}", f"DTEND;VALUE=DATE:{remind + dt.timedelta(days=1):%Y%m%d}",
            f"SUMMARY:{_esc('Claim deadline in 3 days: ' + m.settlement.name)}",
            f"DESCRIPTION:{_esc(m.what_to_check + ' Claim: ' + (m.settlement.claim_url or m.settlement.source_url))}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
