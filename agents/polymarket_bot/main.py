"""polymarket_bot CLI: run the research committee on one binary market.

Research-only mode — never places orders. Output is a BetTicket (or a
rejection reason explaining which consensus rule failed).

Run from repo root:
    python -m agents.polymarket_bot.main --market will-trump-win-2024
    python -m agents.polymarket_bot.main --market 0xabc123...   # condition_id
"""

from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv

from agents.polymarket_bot.committee.engine import build_committee
from agents.polymarket_bot.schema import BetTicket

load_dotenv()


def render_ticket(ticket: BetTicket) -> str:
    evidence_lines = "\n".join(
        f"- [{e.directional_impact}] {e.source}: {e.summary}"
        + (f"  ({e.url})" if e.url else "")
        for e in ticket.evidence[:5]
    ) or "(none)"

    return (
        "| Field | Value |\n"
        "| :--- | :--- |\n"
        f"| **Market** | {ticket.market_question} |\n"
        f"| **Slug** | {ticket.slug} |\n"
        f"| **Side** | **{ticket.side}** |\n"
        f"| **Market price** | {ticket.market_price:.3f} |\n"
        f"| **Our probability** | {ticket.our_probability:.3f} |\n"
        f"| **Edge** | {ticket.edge_pp:.1f} pp |\n"
        f"| **Full Kelly** | {ticket.kelly_fraction_of_bankroll:.2%} of bankroll |\n"
        f"| **Recommended stake** | {ticket.recommended_stake_pct:.2%} of bankroll "
        f"(fractional Kelly, capped) |\n"
        f"| **Confidence** | {ticket.confidence} |\n"
        f"| **Days to resolve** | {ticket.days_to_resolution:.1f} |\n"
        f"| **Critic's warning** | \"{ticket.critic_warning}\" |\n"
        f"| **Calibration** | {ticket.calibration_note} |\n\n"
        f"**Evidence (top 5):**\n{evidence_lines}\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Polymarket research committee.")
    parser.add_argument(
        "--market",
        required=True,
        help="Polymarket market slug or condition_id.",
    )
    args = parser.parse_args()

    print(f"[committee] convening for '{args.market}'...", file=sys.stderr)
    graph = build_committee()
    final = graph.invoke({"market_ref": args.market})

    if final.get("ticket") is None:
        print(
            f"\n## ❌ No Bet\n\n{final.get('rejection_reason', 'Setup did not pass committee.')}\n"
        )
        return

    print("\n## ✅ Bet Ticket\n")
    print(render_ticket(final["ticket"]))


if __name__ == "__main__":
    main()
