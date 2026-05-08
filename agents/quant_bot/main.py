"""Sentinel Committee CLI: run the multi-agent swing analysis on a symbol.

Run from repo root:
    python -m agents.quant_bot.main --asset BTC/USDT
    python -m agents.quant_bot.main --asset ETH/USDT --skip-liquidity
"""

from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv

from agents.quant_bot.committee.engine import build_committee
from agents.quant_bot.schema import TradeTicket
from agents.quant_bot.tools.liquidity import passes_liquidity_filter

load_dotenv()


def render_ticket(ticket: TradeTicket) -> str:
    entry_low, entry_high = ticket.entry_range
    t1, t2 = ticket.targets[0], ticket.targets[1]
    return (
        "| Field | Value |\n"
        "| :--- | :--- |\n"
        f"| **Asset** | {ticket.asset} |\n"
        f"| **Bias** | {ticket.bias.upper()} |\n"
        f"| **Strategy** | {ticket.strategy} |\n"
        f"| **Timeframe** | {ticket.timeframe} |\n"
        f"| **Trade Trifecta** | **Entry:** {entry_low:.2f}–{entry_high:.2f} | "
        f"**T1/T2:** {t1:.2f} / {t2:.2f} | **Stop:** {ticket.stop_loss:.2f} |\n"
        f"| **R:R Ratio** | 1:{ticket.rr_ratio:.2f} |\n"
        f"| **Backtest Success** | {ticket.backtest_win_rate:.0%} "
        f"(based on last {ticket.backtest_samples} similar setups) |\n"
        f"| **Critic's Warning** | \"{ticket.critic_warning}\" |\n"
        f"| **Sentiment** | {ticket.sentiment_summary} |\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Sentinel Committee crypto swing analyzer.")
    parser.add_argument("--asset", required=True, help="CCXT symbol, e.g. BTC/USDT")
    parser.add_argument(
        "--skip-liquidity", action="store_true",
        help="Skip the >$100M 24h volume gate (useful for testing).",
    )
    parser.add_argument(
        "--exchange",
        help="CCXT exchange id (default: kraken; override per-run). Sets QUANT_BOT_EXCHANGE.",
    )
    args = parser.parse_args()

    if args.exchange:
        os.environ["QUANT_BOT_EXCHANGE"] = args.exchange

    if not args.skip_liquidity:
        ok, vol = passes_liquidity_filter(args.asset)
        if not ok:
            print(
                f"[liquidity] {args.asset} fails filter: 24h quote volume "
                f"${vol:,.0f} < required $100M.",
                file=sys.stderr,
            )
            sys.exit(2)

    print(f"[committee] convening for {args.asset}...", file=sys.stderr)
    graph = build_committee()
    final = graph.invoke({"symbol": args.asset})

    if final.get("ticket") is None:
        print(f"\n## ❌ No Trade\n\n{final.get('rejection_reason', 'Setup did not pass committee.')}\n")
        return

    print("\n## ✅ Trade Ticket\n")
    print(render_ticket(final["ticket"]))


if __name__ == "__main__":
    main()
