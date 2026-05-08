"""Walk-forward backtest of a trend-only variant of strategy.txt.

Per-conversation override: stripped the BB-breakout + volume-expansion triggers
(those are volatility/breakout filters, not trend) — entry is now PURELY a
trend signal: 30m bias + 15m EMA-cross. Everything else (stops, TPs, sizing,
cooldown) remains identical to the dual-window spec.

  Long entry (same 15m bar):
    Bias    (30m, ffilled): close > EMA50  AND  RSI(14) > 50.
    Trigger (15m):          EMA9 just crossed above EMA21.

  Short entry (mirror):
    Bias    (30m): close < EMA50  AND  RSI(14) < 50.
    Trigger (15m): EMA9 just crossed below EMA21.

  Risk & exits:
    Stop loss: 15m middle BB (SMA20) at the entry bar.
    TP1:       1:1 R:R — close 50% AND tighten stop to entry - 0.25*R (long)
               / entry + 0.25*R (short). Strategy.txt says "break-even"; we
               give the runner 0.25R of breathing room instead — empirically
               the BE-stop is a near-zero outcome on small retraces.
    TP2:       15m RSI(14) crosses back through 50 against the bias.
    Cooldown:  4 bars after any pure-SL exit.
    Max hold:  28 days (sanity cap; in practice trades close in hours).

  Bias filter (relaxed shorts):
    Long  bias: 30m close > EMA50  AND  RSI(14) > 50.
    Short bias: 30m close < EMA50  AND  RSI(14) < 50.   (was <40 — too tight)

  Position sizing:
    Skip the trade if the implied stop distance is below MIN_STOP_DIST_PCT
    (fees dominate when the move is too small). Otherwise size to risk
    TARGET_RISK_PCT per trade, with leverage capped at MAX_LEVERAGE.

Run from repo root:
    python -m agents.quant_bot.portfolio_backtest --asset BTC/USDT --days 30 --capital 100
"""

from __future__ import annotations

import argparse
import statistics
import sys
from dataclasses import dataclass

import pandas as pd
from dotenv import load_dotenv

from agents.quant_bot.tools.indicators import enrich
from agents.quant_bot.tools.market_data import fetch_ohlcv
from agents.quant_bot.tools.timeframes import align_to_index

load_dotenv()

FEE_RATE = 0.0005
MAX_HOLD_DAYS = 28
COOLDOWN_BARS = 4
SCALE_OUT_FRAC = 0.5            # close 50% at TP1 per spec
TARGET_RISK_PCT = 0.01          # 1.0% per trade — upper bound of strategy spec
MAX_LEVERAGE = 3.0              # capped at 3x (was 10x — fee drag dominated)
MIN_STOP_DIST_PCT = 0.003       # skip if stop < 0.3% from entry (fee-trap zone)
POST_TP1_RETRACE_FRAC = 0.25    # post-TP1 stop at entry - 0.25R (long) / + 0.25R (short)
SHORT_RSI_BIAS_MAX = 50         # was 40 — relaxed to symmetric with long side

BARS_PER_DAY_15M = 96


@dataclass
class Trade:
    entry_ts: str
    bias: str
    entry_price: float
    initial_stop: float
    tp1: float
    leverage: float
    leg1_price: float | None
    final_price: float
    final_ts: str
    bars_held: int
    exit_reason: str
    return_pct: float
    equity_after: float


def _build_signals(m15: pd.DataFrame, m30: pd.DataFrame) -> pd.DataFrame:
    """Pre-compute all entry signal flags, all aligned on the m15 index."""
    bias_src = pd.DataFrame({
        "long": (m30["close"] > m30["ema50"]) & (m30["rsi14"] > 50),
        "short": (m30["close"] < m30["ema50"]) & (m30["rsi14"] < SHORT_RSI_BIAS_MAX),
    })
    bias = align_to_index(bias_src, m15.index).fillna(False).astype(bool)

    out = m15.copy()
    out["bias_long"] = bias["long"]
    out["bias_short"] = bias["short"]

    ema9_above = m15["ema9"] > m15["ema21"]
    out["ema_cross_up"] = ema9_above & ~ema9_above.shift(1).fillna(False)
    out["ema_cross_down"] = ~ema9_above & ema9_above.shift(1).fillna(True)

    out["enter_long"] = out["bias_long"] & out["ema_cross_up"]
    out["enter_short"] = out["bias_short"] & out["ema_cross_down"]
    return out


def _entry_levels(row: pd.Series, bias: str) -> tuple[float, float, float] | None:
    entry = float(row["close"])
    stop = float(row["bb_mid"])  # 15m middle Bollinger band (SMA20)
    if bias == "long":
        if stop >= entry:
            return None
        risk = entry - stop
        tp1 = entry + risk
    else:
        if stop <= entry:
            return None
        risk = stop - entry
        tp1 = entry - risk
    if (risk / entry) < MIN_STOP_DIST_PCT:
        return None
    return entry, stop, tp1


def _leverage_for(entry: float, stop: float) -> float:
    stop_dist_pct = abs(entry - stop) / entry
    if stop_dist_pct < 1e-6:
        return 0.0
    return min(TARGET_RISK_PCT / stop_dist_pct, MAX_LEVERAGE)


def _simulate_trade(
    m15: pd.DataFrame,
    entry_i: int,
    bias: str,
    entry: float,
    stop: float,
    tp1: float,
    max_hold_bars: int,
) -> tuple[int, list[tuple[float, float]], str]:
    end_i = min(entry_i + max_hold_bars, len(m15) - 1)
    risk = abs(entry - stop)
    post_tp1_stop = (
        entry - POST_TP1_RETRACE_FRAC * risk
        if bias == "long"
        else entry + POST_TP1_RETRACE_FRAC * risk
    )
    in_phase2 = False
    current_stop = stop
    leg1_price: float | None = None

    for j in range(entry_i + 1, end_i + 1):
        bar = m15.iloc[j]
        prev = m15.iloc[j - 1]

        if bias == "long":
            sl_hit = bar["low"] <= current_stop
            tp1_hit = (not in_phase2) and bar["high"] >= tp1
            tp2_hit = in_phase2 and prev["rsi14"] >= 50 and bar["rsi14"] < 50
        else:
            sl_hit = bar["high"] >= current_stop
            tp1_hit = (not in_phase2) and bar["low"] <= tp1
            tp2_hit = in_phase2 and prev["rsi14"] <= 50 and bar["rsi14"] > 50

        if sl_hit:
            if in_phase2:
                return j, [(SCALE_OUT_FRAC, leg1_price), (1 - SCALE_OUT_FRAC, current_stop)], "RETRACE_STOP"
            return j, [(1.0, current_stop)], "SL"

        if tp1_hit:
            in_phase2 = True
            leg1_price = tp1
            current_stop = post_tp1_stop  # entry ± 0.25R, not exact BE
            continue

        if tp2_hit:
            return j, [(SCALE_OUT_FRAC, leg1_price), (1 - SCALE_OUT_FRAC, float(bar["close"]))], "TP2"

    final_close = float(m15.iloc[end_i]["close"])
    if in_phase2:
        return end_i, [(SCALE_OUT_FRAC, leg1_price), (1 - SCALE_OUT_FRAC, final_close)], "TIMEOUT_PHASE2"
    return end_i, [(1.0, final_close)], "TIMEOUT"


def _apply_trade(equity: float, bias: str, entry: float, legs, leverage: float) -> float:
    """Return new equity after fees and price moves on a leveraged position."""
    total_pct = 0.0
    fees_pct = FEE_RATE * leverage  # entry fee on full notional
    for frac, price in legs:
        if bias == "long":
            move = (price - entry) / entry
        else:
            move = (entry - price) / entry
        total_pct += frac * leverage * move
        fees_pct += FEE_RATE * frac * leverage
    return equity * (1 + total_pct - fees_pct)


def run_backtest(
    asset: str, days: int = 30, capital: float = 100.0, invert: bool = False
) -> tuple[list[Trade], float, str, dict]:
    print(f"[fetch] {asset} 15m+30m ({days + 10}d incl. warmup)...", file=sys.stderr)
    m15 = enrich(fetch_ohlcv(asset, "15m", days=days + 10))
    m30 = enrich(fetch_ohlcv(asset, "30m", days=days + 10))
    print(f"[fetch] 15m {len(m15)} | 30m {len(m30)}", file=sys.stderr)

    m15 = _build_signals(m15, m30)

    end_ts = m15.index[-1]
    start_ts = end_ts - pd.Timedelta(days=days)
    if start_ts < m15.index[0]:
        actual = (end_ts - m15.index[0]).days
        raise SystemExit(f"only {actual}d of 15m data; need {days}.")
    i0 = m15.index.get_indexer([start_ts], method="nearest")[0]
    window_label = f"{m15.index[i0].strftime('%Y-%m-%d %H:%M')} → {end_ts.strftime('%Y-%m-%d %H:%M')}"

    long_sigs = int(m15.iloc[i0:]["enter_long"].sum())
    short_sigs = int(m15.iloc[i0:]["enter_short"].sum())
    print(f"[signals] in window: long={long_sigs} short={short_sigs}", file=sys.stderr)

    max_hold_bars = MAX_HOLD_DAYS * BARS_PER_DAY_15M
    equity = capital
    trades: list[Trade] = []
    last_sl_bar = -10**9
    skipped_cooldown = 0
    skipped_too_tight = 0
    i = i0

    while i < len(m15) - 1:
        row = m15.iloc[i]
        bias: str | None = None
        if row["enter_long"]:
            bias = "long"
        elif row["enter_short"]:
            bias = "short"

        if bias is None:
            i += 1
            continue

        if invert:
            bias = "short" if bias == "long" else "long"

        if (i - last_sl_bar) < COOLDOWN_BARS:
            skipped_cooldown += 1
            i += 1
            continue

        levels = _entry_levels(row, bias)
        if levels is None:
            skipped_too_tight += 1
            i += 1
            continue
        entry, stop, tp1 = levels
        lev = _leverage_for(entry, stop)
        if lev <= 0:
            i += 1
            continue

        exit_i, legs, reason = _simulate_trade(m15, i, bias, entry, stop, tp1, max_hold_bars)
        new_equity = _apply_trade(equity, bias, entry, legs, lev)
        ret_pct = (new_equity / equity - 1) * 100

        trades.append(Trade(
            entry_ts=m15.index[i].strftime("%Y-%m-%d %H:%M"),
            bias=bias,
            entry_price=round(entry, 2),
            initial_stop=round(stop, 2),
            tp1=round(tp1, 2),
            leverage=round(lev, 2),
            leg1_price=round(legs[0][1], 2) if len(legs) == 2 else None,
            final_price=round(legs[-1][1], 2),
            final_ts=m15.index[exit_i].strftime("%Y-%m-%d %H:%M"),
            bars_held=exit_i - i,
            exit_reason=reason,
            return_pct=round(ret_pct, 2),
            equity_after=round(new_equity, 2),
        ))
        equity = new_equity
        if reason == "SL":
            last_sl_bar = exit_i
        i = exit_i + 1

    diag = {
        "long_signals": long_sigs,
        "short_signals": short_sigs,
        "skipped_cooldown": skipped_cooldown,
        "skipped_too_tight": skipped_too_tight,
    }
    return trades, equity, window_label, diag


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dual-Window Scalping backtest (per strategy.txt)."
    )
    parser.add_argument("--asset", default="BTC/USDT")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--capital", type=float, default=100.0)
    parser.add_argument(
        "--invert", action="store_true",
        help="Flip every long signal to a short (and vice versa). Tests the "
             "'just do the opposite' hypothesis — usually loses harder due to fees.",
    )
    args = parser.parse_args()

    trades, final, window, diag = run_backtest(args.asset, args.days, args.capital, args.invert)
    if args.invert:
        print("\n[!] INVERTED MODE: every long signal flipped to short and vice versa.\n")
    pnl_pct = (final / args.capital - 1) * 100
    sl = sum(t.exit_reason == "SL" for t in trades)
    retrace = sum(t.exit_reason == "RETRACE_STOP" for t in trades)
    tp2 = sum(t.exit_reason == "TP2" for t in trades)
    timeout = sum(t.exit_reason in ("TIMEOUT", "TIMEOUT_PHASE2") for t in trades)

    print(f"\n## Dual-Window Scalping — {args.asset} (last {args.days}d, 15m exec / 30m bias)\n")
    print(f"Window:   {window}")
    print(f"Starting: ${args.capital:.2f}")
    print(f"Final:    ${final:.2f}")
    print(f"Return:   {pnl_pct:+.2f}%")
    print(
        f"Trades: {len(trades)}  (SL {sl}  retrace-stop {retrace}  TP2 {tp2}  timeout {timeout})"
    )
    print(
        f"Signals: long {diag['long_signals']}  short {diag['short_signals']}   "
        f"skipped: cooldown {diag['skipped_cooldown']}  too-tight {diag['skipped_too_tight']}"
    )
    if trades:
        wins = [t for t in trades if t.return_pct > 0]
        avg_hold_h = statistics.mean(t.bars_held for t in trades) * 15 / 60
        avg_lev = statistics.mean(t.leverage for t in trades)
        print(f"Win rate: {len(wins) / len(trades):.0%}")
        print(f"Avg hold: {avg_hold_h:.1f}h    avg leverage: {avg_lev:.2f}x")
        print(
            f"Best/worst: {max(t.return_pct for t in trades):+.2f}% / "
            f"{min(t.return_pct for t in trades):+.2f}%"
        )

    print("\n## Trade log\n")
    if not trades:
        print("(no entry signals triggered in the period)")
        return
    print(
        f"{'entry':>16} {'side':>5} {'lev':>5} {'bars':>5} "
        f"{'in':>9} {'sl':>9} {'tp1':>9} {'leg1':>9} {'final':>9} "
        f"{'why':>14} {'ret%':>7} {'eq$':>8}"
    )
    for t in trades:
        leg1_s = f"{t.leg1_price:>9.2f}" if t.leg1_price is not None else f"{'-':>9}"
        print(
            f"{t.entry_ts:>16} {t.bias:>5} {t.leverage:>5.2f} {t.bars_held:>5} "
            f"{t.entry_price:>9.2f} {t.initial_stop:>9.2f} {t.tp1:>9.2f} {leg1_s} "
            f"{t.final_price:>9.2f} {t.exit_reason:>14} {t.return_pct:>+7.2f} {t.equity_after:>8.2f}"
        )


if __name__ == "__main__":
    main()
