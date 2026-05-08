"""Liquidity gating: enforce >$100M 24h volume so swing positions don't slip."""

from __future__ import annotations

from agents.quant_bot.config import MIN_24H_VOLUME_USD
from agents.quant_bot.tools.market_data import fetch_ticker


def passes_liquidity_filter(symbol: str) -> tuple[bool, float]:
    t = fetch_ticker(symbol)
    quote_vol = t.get("quoteVolume")
    if quote_vol is None:
        last = t.get("last") or 0
        base_vol = t.get("baseVolume") or 0
        quote_vol = last * base_vol
    return quote_vol >= MIN_24H_VOLUME_USD, float(quote_vol)
