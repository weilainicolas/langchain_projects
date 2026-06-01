"""Pydantic schemas for the polymarket_bot committee.

The BetTicket is the final user-facing artifact. The other models are
intermediate signals exchanged between scouts inside the committee graph.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Side = Literal["YES", "NO"]
Tone = Literal["supports_yes", "supports_no", "neutral", "mixed"]


class PolymarketMarket(BaseModel):
    """Canonical market snapshot pulled from Gamma + CLOB."""

    condition_id: str
    slug: str
    question: str
    description: str = ""
    end_date_iso: str
    yes_token_id: str
    no_token_id: str
    market_price_yes: float = Field(ge=0.0, le=1.0)
    market_price_no: float = Field(ge=0.0, le=1.0)
    spread_bps: float
    volume_24h_usd: float
    days_to_resolution: float


class EvidenceItem(BaseModel):
    source: str
    url: str = ""
    summary: str
    directional_impact: Tone


class ResearchSignal(BaseModel):
    """Output of the Research Scout."""

    base_rate_reference: str = Field(
        description="Short label naming the reference class used for the base rate, "
        "e.g. 'historical incumbent re-election rate in midterm years'."
    )
    base_rate: float = Field(ge=0.0, le=1.0)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    summary: str
    items_considered: int = 0


class ProbabilityEstimate(BaseModel):
    """Output of the Probability Scout."""

    our_probability_yes: float = Field(ge=0.0, le=1.0)
    confidence: Literal["low", "medium", "high"]
    reasoning: str = Field(
        description="Walk-through: start from base rate, adjust up/down per evidence item, land on final p."
    )


class CriticVerdict(BaseModel):
    """Output of the Adversarial Critic."""

    veto: bool
    warning: str
    risks: list[str] = Field(default_factory=list)
    market_pricing_in: str = Field(
        description="What is the market pricing in that our estimate may be ignoring?"
    )


class CalibrationResult(BaseModel):
    """Output of the Calibration Auditor."""

    samples: int
    our_brier: float = Field(ge=0.0, le=1.0)
    market_brier: float = Field(ge=0.0, le=1.0)
    beats_market: bool
    notes: str = ""


class BetTicket(BaseModel):
    """Final committee output. Research-only mode — no order placement."""

    market_question: str
    condition_id: str
    slug: str
    side: Side
    market_price: float = Field(ge=0.0, le=1.0)
    our_probability: float = Field(ge=0.0, le=1.0)
    edge_pp: float = Field(description="|our_p - market_p| * 100, in percentage points")
    kelly_fraction_of_bankroll: float = Field(ge=0.0, le=1.0)
    recommended_stake_pct: float = Field(ge=0.0, le=1.0)
    confidence: Literal["low", "medium", "high"]
    critic_warning: str
    calibration_note: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    days_to_resolution: float
