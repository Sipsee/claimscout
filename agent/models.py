"""Data models shared across the ClaimScout pipeline."""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    """What the user tells ClaimScout about themselves. Stays in the session; never stored."""
    state: str = ""
    brands_and_products: str = ""      # "Levoit air purifier, Kia Sportage, Fitbit"
    stores_and_services: str = ""      # "CVS ExtraCare, Comcast, Amazon Prime"
    breach_notices: str = ""           # "got a letter from OneTouchPoint"
    other_notes: str = ""              # free text

    def as_text(self) -> str:
        parts = [
            f"State of residence: {self.state or 'unknown'}",
            f"Products and brands owned or bought: {self.brands_and_products or 'none listed'}",
            f"Stores, memberships and services used: {self.stores_and_services or 'none listed'}",
            f"Data breach notices received: {self.breach_notices or 'none listed'}",
            f"Other notes: {self.other_notes or 'none'}",
        ]
        return "\n".join(parts)


class Settlement(BaseModel):
    """A single open settlement, extracted from a web page by the model."""
    name: str
    who_qualifies: str = Field(description="Plain-English class definition")
    payout: str = ""
    deadline: str = Field("", description="Claim deadline as YYYY-MM-DD if known")
    proof_required: str = Field("", description="What proof a claimant needs, if any")
    claim_url: str = ""
    source_url: str = ""


class Match(BaseModel):
    """The model's verdict on whether a user is in a settlement's class."""
    settlement: Settlement
    verdict: Literal["likely", "maybe", "unlikely"]
    reason: str
    what_to_check: str = Field("", description="What the user should confirm before filing")
    confidence: float = 0.0


class ScoutResult(BaseModel):
    queries: list[str]
    settlements_found: int
    matches: list[Match]
    unclaimed_property_url: Optional[str] = None
    trace: list[str] = []
    demo_mode: bool = False
