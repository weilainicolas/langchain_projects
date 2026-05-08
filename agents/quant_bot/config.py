"""Quant_bot configuration constants."""

from __future__ import annotations

LLM_MODEL = "gpt-4o"

EXCHANGE_ID = "binanceus"  # override with QUANT_BOT_EXCHANGE env var or --exchange flag

TIMEFRAMES = {"trend": "1w", "setup": "1d", "entry": "4h"}

OHLCV_LIMIT = {"1w": 200, "1d": 730, "4h": 1500}

MIN_24H_VOLUME_USD = 100_000_000
MIN_RR_RATIO = 3.0
MIN_BACKTEST_WIN_RATE = 0.55
BACKTEST_HORIZON_DAYS = 60
BACKTEST_LOOKBACK_DAYS = 730

# Hard cap on the number of structured-data items (bars, headlines, rows, etc.)
# any scout may include in a single LLM call. Defense-in-depth budget control.
MAX_LLM_DATA_ITEMS = 100
