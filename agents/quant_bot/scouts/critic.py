"""Adversarial Critic: actively hunts for "the trap" in a proposed setup."""

from __future__ import annotations

import pandas as pd

from agents.quant_bot.schema import CriticVerdict, SentimentSignal, TrendSignal
from agents.quant_bot.tools.llm import structured_call


SYSTEM_PROMPT = """You are the Adversarial Critic — a Red Team analyst whose
job is to invalidate the Trend Scout's setup by finding bearish divergences,
liquidity gaps, or structural traps.

You set `veto=True` only when the setup is *materially* broken — for example:
- Stop sits inside a known liquidity grab zone.
- Daily RSI extreme (>75 long / <25 short) with no consolidation.
- Bias contradicts the W1 EMA200 regime.
- R:R math doesn't actually achieve >= 3:1.

Otherwise set `veto=False` and surface the strongest single risk in `warning`."""


def _state_block(daily_df: pd.DataFrame) -> str:
    tail = daily_df.tail(5)[["close", "ema50", "ema200", "rsi14", "bb_up", "bb_low"]]
    return tail.round(2).to_string()


def run_critic(
    symbol: str, trend: TrendSignal, sentiment: SentimentSignal, daily_df: pd.DataFrame
) -> CriticVerdict:
    entry_mid = (trend.entry_low + trend.entry_high) / 2
    rr = abs(trend.target_2 - entry_mid) / max(abs(entry_mid - trend.stop_loss), 1e-9)

    user = (
        f"Asset: {symbol}\n"
        f"Proposed: {trend.bias} via {trend.strategy}\n"
        f"Entry: [{trend.entry_low}, {trend.entry_high}]  T1: {trend.target_1}  "
        f"T2: {trend.target_2}  Stop: {trend.stop_loss}\n"
        f"Implied R:R = {rr:.2f}\n\n"
        f"Trend Scout rationale: {trend.rationale}\n\n"
        f"Sentiment: {sentiment.tone} (divergence={sentiment.divergence}) — {sentiment.summary}\n\n"
        f"Last 5 daily bars:\n{_state_block(daily_df)}\n\n"
        "Find the strongest reason this setup could fail, and decide whether to veto."
    )
    return structured_call(SYSTEM_PROMPT, user, CriticVerdict)
