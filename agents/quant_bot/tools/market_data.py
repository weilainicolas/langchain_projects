"""CCXT-backed market data fetcher."""

from __future__ import annotations

import os
from functools import lru_cache

import ccxt
import pandas as pd

from agents.quant_bot.config import EXCHANGE_ID, OHLCV_LIMIT


def _resolve_exchange_id() -> str:
    return os.environ.get("QUANT_BOT_EXCHANGE") or EXCHANGE_ID


@lru_cache(maxsize=4)
def _exchange_for(ex_id: str) -> ccxt.Exchange:
    return getattr(ccxt, ex_id)({"enableRateLimit": True})


def _exchange() -> ccxt.Exchange:
    return _exchange_for(_resolve_exchange_id())


def fetch_ohlcv(
    symbol: str,
    timeframe: str,
    limit: int | None = None,
    days: int | None = None,
) -> pd.DataFrame:
    """Return OHLCV as a DataFrame indexed by UTC timestamp.

    If `days` is set, paginates backward via the `since` parameter to gather
    enough bars (kraken caps single calls at ~720). Otherwise uses a single
    `limit`-bar fetch (default per-timeframe in OHLCV_LIMIT)."""
    ex = _exchange()
    if days is None:
        n = limit or OHLCV_LIMIT.get(timeframe, 500)
        raw = ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=n)
    else:
        end_ms = ex.milliseconds()
        target_start = end_ms - int(days * 24 * 60 * 60 * 1000)
        raw: list = []
        seen: set[int] = set()
        cursor = target_start
        while cursor < end_ms:
            batch = ex.fetch_ohlcv(symbol, timeframe=timeframe, since=cursor, limit=720)
            if not batch:
                break
            new_bars = [b for b in batch if b[0] not in seen]
            if not new_bars:
                break
            raw.extend(new_bars)
            seen.update(b[0] for b in new_bars)
            cursor = batch[-1][0] + 1
    df = pd.DataFrame(raw, columns=["ts", "open", "high", "low", "close", "volume"])
    df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    df = df.set_index("ts").sort_index()
    return df


def fetch_ticker(symbol: str) -> dict:
    return _exchange().fetch_ticker(symbol)
