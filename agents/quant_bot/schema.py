"""Pydantic schemas for the Sentinel Committee.

The TradeTicket is the final user-facing artifact. The other models are
intermediate signals exchanged between scouts inside the committee graph.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Bias = Literal["long", "short"]


class IndicatorSnapshot(BaseModel):
    """Indicator state at entry — used by the auditor to match historical setups."""

    rsi14: float
    dist_ema50_pct: float


class TrendSignal(BaseModel):
    """Output of the Trend Scout."""

    bias: Bias
    strategy: str = Field(description="Short label, e.g. 'D1 Mean Reversion (50 EMA Touch)'")
    entry_low: float
    entry_high: float
    target_1: float
    target_2: float
    stop_loss: float
    rationale: str
    indicator_snapshot: IndicatorSnapshot


class SentimentSignal(BaseModel):
    """Output of the Sentiment Scout."""

    tone: Literal["bullish", "bearish", "neutral", "mixed"]
    divergence: bool = Field(description="True if news tone diverges from price action.")
    summary: str
    headlines_considered: int = 0


class CriticVerdict(BaseModel):
    """Output of the Adversarial Critic."""

    veto: bool
    warning: str
    risks: list[str] = Field(default_factory=list)


class BacktestResult(BaseModel):
    """Output of the Backtest Auditor."""

    win_rate: float = Field(ge=0.0, le=1.0)
    samples: int
    avg_max_drawdown_pct: float
    notes: str = ""


class TradeTicket(BaseModel):
    """Final committee output."""

    asset: str
    bias: Bias
    timeframe: str
    strategy: str
    entry_range: tuple[float, float]
    targets: list[float]
    stop_loss: float
    rr_ratio: float
    backtest_win_rate: float
    backtest_samples: int
    critic_warning: str
    sentiment_summary: str
