"""Sentiment Scout: reads recent news and flags price/narrative divergence."""

from __future__ import annotations

import json

from agents.quant_bot.config import MAX_LLM_DATA_ITEMS
from agents.quant_bot.schema import SentimentSignal, TrendSignal
from agents.quant_bot.tools.llm import structured_call
from agents.quant_bot.tools.news import fetch_crypto_news


SYSTEM_PROMPT = """You are the Sentiment Scout on a crypto swing committee.
You read recent news headlines for one asset and judge:
1. Overall tone (bullish / bearish / neutral / mixed).
2. Whether news tone diverges from the proposed trade bias — divergence is a
   warning, not a veto.
Be brief. 2–3 sentences in `summary`."""


def _asset_keyword(symbol: str) -> str:
    base = symbol.split("/")[0]
    aliases = {"BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana"}
    return aliases.get(base, base.lower())


def run_sentiment_scout(symbol: str, trend: TrendSignal) -> SentimentSignal:
    headlines = fetch_crypto_news(_asset_keyword(symbol), max_items=MAX_LLM_DATA_ITEMS)
    headlines = headlines[:MAX_LLM_DATA_ITEMS]  # belt-and-braces cap
    if not headlines:
        return SentimentSignal(
            tone="neutral",
            divergence=False,
            summary="No news source configured (NEWSAPI_KEY missing) — skipping sentiment check.",
            headlines_considered=0,
        )

    user = (
        f"Asset: {symbol}\n"
        f"Proposed bias from Trend Scout: {trend.bias}\n"
        f"Proposed strategy: {trend.strategy}\n\n"
        f"Recent headlines (most recent first):\n{json.dumps(headlines, indent=2)}"
    )
    out = structured_call(SYSTEM_PROMPT, user, SentimentSignal)
    out.headlines_considered = len(headlines)
    return out
