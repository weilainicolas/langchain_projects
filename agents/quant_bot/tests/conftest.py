"""Synthetic OHLCV fixtures — no network, no LLM."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from agents.quant_bot.tools.indicators import enrich


def _ohlcv_from_close(close: np.ndarray, start: str = "2023-01-01") -> pd.DataFrame:
    n = len(close)
    idx = pd.date_range(start, periods=n, freq="D", tz="UTC")
    rng = np.random.default_rng(42)
    noise_high = rng.uniform(0.001, 0.01, size=n)
    noise_low = rng.uniform(0.001, 0.01, size=n)
    high = close * (1 + noise_high)
    low = close * (1 - noise_low)
    open_ = np.concatenate([[close[0]], close[:-1]])
    volume = np.full(n, 1_000.0)
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=idx,
    )


@pytest.fixture
def trending_up_daily() -> pd.DataFrame:
    """800 days of a noisy uptrend — clean enough that EMA50 < EMA200 inverts mid-series."""
    rng = np.random.default_rng(7)
    base = np.linspace(20_000, 60_000, 800)
    noise = rng.normal(0, 500, size=800).cumsum() * 0.1
    close = base + noise
    return enrich(_ohlcv_from_close(close))


@pytest.fixture
def oscillating_daily() -> pd.DataFrame:
    """800 days oscillating around 30k — gives the backtester many signature matches."""
    rng = np.random.default_rng(11)
    t = np.arange(800)
    close = 30_000 + 2_000 * np.sin(t / 40) + rng.normal(0, 300, size=800)
    return enrich(_ohlcv_from_close(close))
