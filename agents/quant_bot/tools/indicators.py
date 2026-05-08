"""Hand-rolled technical indicators (no ta-lib dependency)."""

from __future__ import annotations

import numpy as np
import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    with np.errstate(divide="ignore", invalid="ignore"):
        rs = gain / loss
    return (100 - 100 / (1 + rs)).fillna(50)


def bollinger(series: pd.Series, period: int = 20, stdev: float = 2.0) -> pd.DataFrame:
    mid = series.rolling(period).mean()
    sd = series.rolling(period).std()
    return pd.DataFrame({"bb_mid": mid, "bb_up": mid + stdev * sd, "bb_low": mid - stdev * sd})


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    tr = pd.concat(
        [(high - low), (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1
    ).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


def swing_low(series: pd.Series, lookback: int = 20) -> float:
    return float(series.tail(lookback).min())


def swing_high(series: pd.Series, lookback: int = 20) -> float:
    return float(series.tail(lookback).max())


def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    fast_ema = ema(series, fast)
    slow_ema = ema(series, slow)
    line = fast_ema - slow_ema
    sig = ema(line, signal)
    return pd.DataFrame({"macd": line, "macd_signal": sig, "macd_hist": line - sig})


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    """Add the standard indicator columns used by every scout."""
    out = df.copy()
    out["ema9"] = ema(df["close"], 9)
    out["ema20"] = ema(df["close"], 20)
    out["ema21"] = ema(df["close"], 21)
    out["ema50"] = ema(df["close"], 50)
    out["ema200"] = ema(df["close"], 200)
    out["rsi14"] = rsi(df["close"], 14)
    bb = bollinger(df["close"])
    out[["bb_mid", "bb_up", "bb_low"]] = bb
    out["atr14"] = atr(df, 14)
    out["dist_ema50_pct"] = (df["close"] - out["ema50"]) / out["ema50"] * 100
    m = macd(df["close"])
    out[["macd", "macd_signal", "macd_hist"]] = m
    return out
