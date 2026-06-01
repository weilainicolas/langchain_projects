"""Calibration Auditor: did our estimator beat the naive prior on similar
resolved markets? Pure delegator to tools/calibration.py — kept as its own
scout to mirror the quant_bot pattern and to make the swap to a stricter
audit (e.g. market-closing-mid Brier) a one-file change."""

from __future__ import annotations

from agents.polymarket_bot.schema import CalibrationResult, PolymarketMarket
from agents.polymarket_bot.tools.calibration import score_calibration


def run_calibration_auditor(market: PolymarketMarket) -> CalibrationResult:
    samples, our_brier, market_brier = score_calibration(market.question)
    if samples == 0:
        return CalibrationResult(
            samples=0,
            our_brier=0.0,
            market_brier=0.0,
            beats_market=False,
            notes="No comparable resolved markets found — calibration check skipped.",
        )
    return CalibrationResult(
        samples=samples,
        our_brier=our_brier,
        market_brier=market_brier,
        beats_market=our_brier < market_brier,
        notes=(
            f"Re-estimated {samples} similar resolved markets blind. "
            f"Our Brier={our_brier:.3f} vs naive-prior Brier={market_brier:.3f}."
        ),
    )
