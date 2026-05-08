"""Walk-forward backtester for the Sentinel Committee.

Given a TradeTicket, find historical bars whose indicator state matches the
proposed entry "signature" and simulate the trade forward — counting whether
the percentage-equivalent target or stop was hit first within HORIZON days.
"""

from __future__ import annotations

import pandas as pd

from agents.quant_bot.config import BACKTEST_HORIZON_DAYS, BACKTEST_LOOKBACK_DAYS
from agents.quant_bot.schema import BacktestResult, TrendSignal


class HistoricalValidator:
    """Walk-forward simulator over enriched daily OHLCV."""

    def __init__(self, daily_df: pd.DataFrame) -> None:
        self.df = daily_df.tail(BACKTEST_LOOKBACK_DAYS).copy()

    def run(self, signal: TrendSignal) -> BacktestResult:
        entry_mid = (signal.entry_low + signal.entry_high) / 2
        target_pct = (signal.target_2 - entry_mid) / entry_mid
        stop_pct = (signal.stop_loss - entry_mid) / entry_mid

        if signal.bias == "long" and (target_pct <= 0 or stop_pct >= 0):
            return BacktestResult(
                win_rate=0.0, samples=0, avg_max_drawdown_pct=0.0,
                notes="Invalid R:R geometry for long.",
            )
        if signal.bias == "short" and (target_pct >= 0 or stop_pct <= 0):
            return BacktestResult(
                win_rate=0.0, samples=0, avg_max_drawdown_pct=0.0,
                notes="Invalid R:R geometry for short.",
            )

        matches = self._find_signature_matches(signal)
        if matches.empty:
            return BacktestResult(
                win_rate=0.0, samples=0, avg_max_drawdown_pct=0.0,
                notes="No similar historical setups found.",
            )

        wins = 0
        drawdowns: list[float] = []
        for entry_idx in matches.index:
            outcome = self._simulate_forward(entry_idx, signal.bias, target_pct, stop_pct)
            if outcome is None:
                continue
            won, dd = outcome
            wins += int(won)
            drawdowns.append(dd)

        n = len(drawdowns)
        if n == 0:
            return BacktestResult(
                win_rate=0.0, samples=0, avg_max_drawdown_pct=0.0,
                notes="Matches found but none had enough forward bars to simulate.",
            )

        return BacktestResult(
            win_rate=wins / n,
            samples=n,
            avg_max_drawdown_pct=sum(drawdowns) / n,
            notes=f"Signature matched {n} historical setups in last {BACKTEST_LOOKBACK_DAYS}d.",
        )

    def _find_signature_matches(self, signal: TrendSignal) -> pd.DataFrame:
        sig = signal.indicator_snapshot
        rsi_band = (sig.rsi14 - 5, sig.rsi14 + 5)
        dist_band = (sig.dist_ema50_pct - 1.0, sig.dist_ema50_pct + 1.0)

        scan = self.df.iloc[:-BACKTEST_HORIZON_DAYS]
        return scan[
            scan["rsi14"].between(*rsi_band)
            & scan["dist_ema50_pct"].between(*dist_band)
        ]

    def _simulate_forward(
        self, entry_idx, bias: str, target_pct: float, stop_pct: float
    ) -> tuple[bool, float] | None:
        loc = self.df.index.get_loc(entry_idx)
        window = self.df.iloc[loc + 1 : loc + 1 + BACKTEST_HORIZON_DAYS]
        if len(window) < 5:
            return None

        entry_price = float(self.df.loc[entry_idx, "close"])
        target_price = entry_price * (1 + target_pct)
        stop_price = entry_price * (1 + stop_pct)

        if bias == "long":
            running_low = entry_price
            for _, bar in window.iterrows():
                running_low = min(running_low, bar["low"])
                if bar["low"] <= stop_price:
                    dd = (running_low - entry_price) / entry_price * 100
                    return False, dd
                if bar["high"] >= target_price:
                    dd = (running_low - entry_price) / entry_price * 100
                    return True, dd
            dd = (running_low - entry_price) / entry_price * 100
            return False, dd

        running_high = entry_price
        for _, bar in window.iterrows():
            running_high = max(running_high, bar["high"])
            if bar["high"] >= stop_price:
                dd = (entry_price - running_high) / entry_price * 100
                return False, dd
            if bar["low"] <= target_price:
                dd = (entry_price - running_high) / entry_price * 100
                return True, dd
        dd = (entry_price - running_high) / entry_price * 100
        return False, dd
