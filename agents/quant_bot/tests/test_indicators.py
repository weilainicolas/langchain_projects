"""Sanity checks for hand-rolled indicators."""

from __future__ import annotations

import numpy as np
import pandas as pd

from agents.quant_bot.tools.indicators import atr, bollinger, ema, enrich, macd, rsi


def _series(values) -> pd.Series:
    return pd.Series(values, dtype=float)


def test_ema_constant_series_is_flat():
    s = _series([100] * 100)
    assert ema(s, 20).iloc[-1] == 100


def test_ema_responds_faster_than_longer_period():
    s = _series(np.linspace(100, 200, 100))
    fast, slow = ema(s, 10).iloc[-1], ema(s, 50).iloc[-1]
    assert fast > slow > 100


def test_rsi_strict_uptrend_is_high():
    s = _series(np.linspace(100, 200, 100))
    assert rsi(s).iloc[-1] > 90


def test_rsi_strict_downtrend_is_low():
    s = _series(np.linspace(200, 100, 100))
    assert rsi(s).iloc[-1] < 10


def test_bollinger_bands_envelope_price():
    s = _series(np.linspace(100, 110, 100))
    bb = bollinger(s)
    assert (bb["bb_up"].dropna() >= bb["bb_mid"].dropna()).all()
    assert (bb["bb_low"].dropna() <= bb["bb_mid"].dropna()).all()


def test_atr_is_positive_and_tracks_range(trending_up_daily):
    a = atr(trending_up_daily, 14).dropna()
    assert (a > 0).all()


def test_enrich_adds_expected_columns(trending_up_daily):
    cols = {
        "ema20", "ema50", "ema200", "rsi14",
        "bb_mid", "bb_up", "bb_low", "atr14", "dist_ema50_pct",
        "macd", "macd_signal", "macd_hist",
    }
    assert cols.issubset(set(trending_up_daily.columns))


def test_macd_uptrend_line_above_signal():
    s = _series(np.linspace(100, 200, 200))
    out = macd(s).iloc[-1]
    # In a sustained uptrend, fast EMA > slow EMA so line > 0, and line > signal.
    assert out["macd"] > 0
    assert out["macd"] > out["macd_signal"]
    assert out["macd_hist"] > 0


def test_macd_signal_smoother_than_line():
    rng = np.random.default_rng(3)
    s = _series(100 + rng.normal(0, 1, 300).cumsum())
    m = macd(s).dropna()
    assert m["macd"].std() > m["macd_signal"].std()
