"""Trend Scout: multi-timeframe technical analyst that proposes a setup."""

from __future__ import annotations

import pandas as pd

from agents.quant_bot.config import TIMEFRAMES
from agents.quant_bot.schema import TrendSignal
from agents.quant_bot.tools.indicators import enrich, swing_high, swing_low
from agents.quant_bot.tools.llm import structured_call
from agents.quant_bot.tools.market_data import fetch_ohlcv


SYSTEM_PROMPT = """You are the Trend Scout on a crypto swing-trading committee.
You read multi-timeframe technical state (W1 trend, D1 setup, H4 entry) and
propose ONE concrete swing trade with a 14–60 day horizon.

Hard rules — compute these explicitly before responding:
- Let mid = (entry_low + entry_high) / 2.
- For a long: target_2 > mid > stop_loss; reward = target_2 - mid; risk = mid - stop_loss.
- For a short: target_2 < mid < stop_loss; reward = mid - target_2; risk = stop_loss - mid.
- R:R = reward / risk MUST be >= 3.0. If your first draft has R:R < 3, push
  target_2 out to the next structural extension (Bollinger band, prior swing
  high/low, or 1.618 fib) BEFORE responding. Do not respond with R:R < 3.
- Stop loss must be anchored to a real structural level (recent swing or
  ~2 ATR away), NOT a round number.
- Entry range must be a price band where a pullback could plausibly occur.

Indicator snapshot must include keys: rsi14, dist_ema50_pct (current values
on the daily timeframe). These are used by the auditor to find similar
historical setups."""


def _frame_context(label: str, df: pd.DataFrame) -> str:
    last = df.iloc[-1]
    return (
        f"[{label}] close={last['close']:.2f} ema50={last['ema50']:.2f} "
        f"ema200={last['ema200']:.2f} rsi14={last['rsi14']:.1f} "
        f"bb_low={last['bb_low']:.2f} bb_up={last['bb_up']:.2f} "
        f"atr14={last['atr14']:.2f} dist_ema50_pct={last['dist_ema50_pct']:.2f}"
    )


def run_trend_scout(symbol: str) -> tuple[TrendSignal, pd.DataFrame]:
    """Returns the proposed signal plus the enriched daily DataFrame
    (the auditor reuses it to avoid a duplicate fetch)."""
    weekly = enrich(fetch_ohlcv(symbol, TIMEFRAMES["trend"]))
    daily = enrich(fetch_ohlcv(symbol, TIMEFRAMES["setup"]))
    h4 = enrich(fetch_ohlcv(symbol, TIMEFRAMES["entry"]))

    last_d = daily.iloc[-1]
    structural_low = swing_low(daily["low"], 30)
    structural_high = swing_high(daily["high"], 30)
    atr_d = float(last_d["atr14"])

    user = (
        f"Asset: {symbol}\n"
        f"Last close: {last_d['close']:.2f}\n"
        f"Daily ATR(14): {atr_d:.2f}\n"
        f"30-bar swing low / high (D1): {structural_low:.2f} / {structural_high:.2f}\n\n"
        f"{_frame_context('W1', weekly)}\n"
        f"{_frame_context('D1', daily)}\n"
        f"{_frame_context('H4', h4)}\n\n"
        "Propose one swing trade. Set `indicator_snapshot` to the *current* daily values: "
        f"rsi14={last_d['rsi14']:.2f}, dist_ema50_pct={last_d['dist_ema50_pct']:.2f}."
    )

    signal = structured_call(SYSTEM_PROMPT, user, TrendSignal)
    signal.indicator_snapshot.rsi14 = float(last_d["rsi14"])
    signal.indicator_snapshot.dist_ema50_pct = float(last_d["dist_ema50_pct"])
    return signal, daily
