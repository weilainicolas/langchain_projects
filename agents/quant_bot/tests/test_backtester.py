"""Backtester behavior — deterministic, on synthetic data only."""

from __future__ import annotations

from agents.quant_bot.schema import IndicatorSnapshot, TrendSignal
from agents.quant_bot.tools.backtester import HistoricalValidator


def _signal_from_row(row, target_pct: float, stop_pct: float, bias: str = "long") -> TrendSignal:
    px = float(row["close"])
    return TrendSignal(
        bias=bias,
        strategy="test",
        entry_low=px * 0.999,
        entry_high=px * 1.001,
        target_1=px * (1 + target_pct / 2),
        target_2=px * (1 + target_pct),
        stop_loss=px * (1 + stop_pct),
        rationale="synthetic",
        indicator_snapshot=IndicatorSnapshot(
            rsi14=float(row["rsi14"]),
            dist_ema50_pct=float(row["dist_ema50_pct"]),
        ),
    )


def test_finds_matches_in_oscillating_market(oscillating_daily):
    """An oscillator visits every RSI/EMA-distance state many times — we
    should find plenty of signature matches."""
    last = oscillating_daily.iloc[-1]
    sig = _signal_from_row(last, target_pct=0.06, stop_pct=-0.02)
    result = HistoricalValidator(oscillating_daily).run(sig)
    assert result.samples > 5, f"expected several matches, got {result.samples}"
    assert 0.0 <= result.win_rate <= 1.0


def test_invalid_long_geometry_returns_zero_winrate(oscillating_daily):
    """Stop above entry on a long is invalid — should short-circuit to 0."""
    last = oscillating_daily.iloc[-1]
    sig = _signal_from_row(last, target_pct=0.05, stop_pct=0.02)  # stop ABOVE entry
    result = HistoricalValidator(oscillating_daily).run(sig)
    assert result.win_rate == 0.0
    assert result.samples == 0
    assert "Invalid R:R geometry" in result.notes


def test_tight_stop_wide_target_loses_more_often(oscillating_daily):
    """1:5 R:R should win less often than 1:1 R:R on the same data — basic sanity."""
    last = oscillating_daily.iloc[-1]
    easy = _signal_from_row(last, target_pct=0.01, stop_pct=-0.01)   # 1:1
    hard = _signal_from_row(last, target_pct=0.05, stop_pct=-0.01)   # 5:1
    easy_r = HistoricalValidator(oscillating_daily).run(easy)
    hard_r = HistoricalValidator(oscillating_daily).run(hard)
    if easy_r.samples > 0 and hard_r.samples > 0:
        assert easy_r.win_rate >= hard_r.win_rate


def test_no_matches_returns_clean_zero(trending_up_daily):
    """Pick an absurd RSI value not present in the trending series."""
    last = trending_up_daily.iloc[-1].copy()
    last["rsi14"] = -999  # impossible — no historical bar will match
    last["dist_ema50_pct"] = -999
    sig = _signal_from_row(last, target_pct=0.05, stop_pct=-0.02)
    result = HistoricalValidator(trending_up_daily).run(sig)
    assert result.samples == 0
    assert result.win_rate == 0.0
