"""polymarket_bot configuration constants."""

from __future__ import annotations

LLM_MODEL = "gpt-4o"

GAMMA_API = "https://gamma-api.polymarket.com"
CLOB_API = "https://clob.polymarket.com"

# Consensus thresholds for the finalize node.
MIN_EDGE_PP = 5.0           # |our_p - market_p| * 100 must be at least this many points
MIN_VOLUME_USD = 50_000     # rolling 24h volume gate
MAX_SPREAD_BPS = 300        # 3% spread cap (mid - bid) / mid * 10000
MIN_DAYS_TO_RESOLUTION = 1  # skip markets resolving in < 24h (news risk)

# Kelly sizing. We bet a fraction of full Kelly to survive estimation error.
KELLY_FRACTION = 0.25
MAX_STAKE_PCT = 0.05        # never recommend > 5% of bankroll on one market

# Calibration auditor pulls the N most semantically similar resolved markets,
# re-asks the probability scout blind, and compares Brier vs market-implied Brier.
CALIBRATION_SAMPLE_SIZE = 8
CALIBRATION_LOOKBACK_DAYS = 365

# Hard cap on the number of items (headlines, resolved markets, etc.) any scout
# may include in a single LLM call. Defense-in-depth budget control.
MAX_LLM_DATA_ITEMS = 50
