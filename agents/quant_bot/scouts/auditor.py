"""Backtest Auditor: deterministic walk-forward simulation, no LLM."""

from __future__ import annotations

import pandas as pd

from agents.quant_bot.schema import BacktestResult, TrendSignal
from agents.quant_bot.tools.backtester import HistoricalValidator


def run_auditor(trend: TrendSignal, daily_df: pd.DataFrame) -> BacktestResult:
    return HistoricalValidator(daily_df).run(trend)
