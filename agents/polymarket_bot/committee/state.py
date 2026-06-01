"""Mutable state passed between LangGraph nodes."""

from __future__ import annotations

from typing import TypedDict

from agents.polymarket_bot.schema import (
    BetTicket,
    CalibrationResult,
    CriticVerdict,
    PolymarketMarket,
    ProbabilityEstimate,
    ResearchSignal,
)


class CommitteeState(TypedDict, total=False):
    market_ref: str  # slug or condition_id supplied on the CLI
    market: PolymarketMarket
    research: ResearchSignal
    estimate: ProbabilityEstimate
    critic: CriticVerdict
    calibration: CalibrationResult
    ticket: BetTicket | None
    rejection_reason: str | None
