"""Timeframe resampling and cross-timeframe alignment helpers."""

from __future__ import annotations

import pandas as pd


def resample(df: pd.DataFrame, target: str) -> pd.DataFrame:
    """Resample OHLCV to a coarser timeframe (e.g., '2h')."""
    return (
        df.resample(target, label="left", closed="left")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
        .dropna()
    )


def align_to_index(
    htf_df: pd.DataFrame,
    base_index: pd.DatetimeIndex,
    columns: list[str] | None = None,
) -> pd.DataFrame:
    """Forward-fill higher-timeframe data onto a finer base index.

    Shifts by 1 to ensure no lookahead — at base bar t, you only see the
    higher-TF bar that closed STRICTLY before t."""
    src = htf_df[columns] if columns else htf_df
    return src.shift(1).reindex(base_index, method="ffill")
