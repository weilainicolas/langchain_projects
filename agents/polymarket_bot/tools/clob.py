"""Polymarket CLOB API client — read-only.

Gamma's outcomePrices field is a snapshot and can lag the live book by
seconds-to-minutes. For the bet-sizing decision we want the live midprice
and spread, which only the CLOB exposes.

The /book endpoint is public; signing is only required for order placement,
which we deliberately do not do in research-only mode.
"""

from __future__ import annotations

from typing import Any

import requests

from agents.polymarket_bot.config import CLOB_API

_TIMEOUT = 15


def fetch_book(token_id: str) -> dict[str, Any]:
    """Returns {'bids': [...], 'asks': [...]} for one outcome token. Each level
    is a dict with 'price' and 'size' (both as strings in the upstream API).
    """
    resp = requests.get(f"{CLOB_API}/book", params={"token_id": token_id}, timeout=_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    return {
        "bids": data.get("bids", []) or [],
        "asks": data.get("asks", []) or [],
    }


def _best_price(levels: list[dict[str, Any]], side: str) -> float | None:
    """Best bid = max price; best ask = min price."""
    prices = []
    for lvl in levels:
        try:
            prices.append(float(lvl.get("price", 0)))
        except (TypeError, ValueError):
            continue
    if not prices:
        return None
    return max(prices) if side == "bid" else min(prices)


def fetch_midprice_and_spread(token_id: str) -> tuple[float, float]:
    """Returns (midprice, spread_bps).

    Falls back to (NaN-ish defaults) if the book is empty — caller should treat
    that as a liquidity failure.
    """
    book = fetch_book(token_id)
    bid = _best_price(book["bids"], "bid")
    ask = _best_price(book["asks"], "ask")

    if bid is None or ask is None or ask <= 0:
        return 0.0, float("inf")

    mid = (bid + ask) / 2
    spread_bps = (ask - bid) / mid * 10_000 if mid > 0 else float("inf")
    return mid, spread_bps
