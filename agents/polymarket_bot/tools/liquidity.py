"""Liquidity gate: enforce a minimum 24h volume and maximum spread.

A wide-spread market punishes both entry and exit; tight spread = real
market-maker presence = more trustworthy midprice for the edge calculation.
"""

from __future__ import annotations

from agents.polymarket_bot.config import MAX_SPREAD_BPS, MIN_DAYS_TO_RESOLUTION, MIN_VOLUME_USD


def passes_liquidity_filter(
    volume_24h_usd: float, spread_bps: float, days_to_resolution: float
) -> tuple[bool, str]:
    """Returns (passes, reason). `reason` is empty when passes=True."""
    if volume_24h_usd < MIN_VOLUME_USD:
        return False, f"24h volume ${volume_24h_usd:,.0f} < required ${MIN_VOLUME_USD:,.0f}."
    if spread_bps > MAX_SPREAD_BPS:
        return False, f"Spread {spread_bps:.0f}bps > max {MAX_SPREAD_BPS}bps."
    if days_to_resolution < MIN_DAYS_TO_RESOLUTION:
        return False, (
            f"Resolves in {days_to_resolution:.2f}d (< {MIN_DAYS_TO_RESOLUTION}d) — "
            f"too much last-minute news risk."
        )
    return True, ""
