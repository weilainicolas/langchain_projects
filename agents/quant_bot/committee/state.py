"""Mutable state passed between LangGraph nodes."""

from __future__ import annotations

from typing import TypedDict

import pandas as pd

from agents.quant_bot.schema import (
    BacktestResult,
    CriticVerdict,
    SentimentSignal,
    TradeTicket,
    TrendSignal,
)


class CommitteeState(TypedDict, total=False):
    symbol: str
    daily_df: pd.DataFrame
    trend: TrendSignal
    sentiment: SentimentSignal
    critic: CriticVerdict
    backtest: BacktestResult
    ticket: TradeTicket | None
    rejection_reason: str | None
