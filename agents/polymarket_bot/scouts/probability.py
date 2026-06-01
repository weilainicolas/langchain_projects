"""Probability Scout: synthesizes evidence + base rate into a single P(YES).

The prompt forces an explicit Bayesian walk-through (start at base rate, list
adjustments per evidence item, land on final p). This pattern dramatically
reduces base-rate neglect vs. asking for a probability cold."""

from __future__ import annotations

from agents.polymarket_bot.schema import PolymarketMarket, ProbabilityEstimate, ResearchSignal
from agents.polymarket_bot.tools.llm import structured_call


SYSTEM_PROMPT = """You are the Probability Scout. Given a reference-class base
rate and a list of evidence items, output your best estimate of P(YES) for a
binary Polymarket market.

Process — perform this explicitly in `reasoning`:
1. Start from the supplied base rate.
2. For each evidence item, state how much it moves your estimate up or down
   (in percentage points). Be honest: most single news items move a posterior
   by 1–5pp, not 20pp.
3. Sum the adjustments and report the final probability.

Calibrate confidence:
- low:    evidence is sparse / conflicting / base rate is weak.
- medium: 3+ evidence items, mostly consistent, decent base rate.
- high:   strong base rate AND multiple consistent strong-signal items
          AND no major unknown.

Do NOT anchor to the market price — you don't see it. The committee compares
your number to the market separately."""


def run_probability_scout(
    market: PolymarketMarket, research: ResearchSignal
) -> ProbabilityEstimate:
    evidence_block = "\n".join(
        f"- [{e.directional_impact}] {e.source}: {e.summary}"
        for e in research.evidence
    ) or "(no evidence items)"

    user = (
        f"Market question: {market.question}\n"
        f"Resolution date: {market.end_date_iso}\n"
        f"Days to resolution: {market.days_to_resolution:.1f}\n\n"
        f"Reference class: {research.base_rate_reference}\n"
        f"Base rate: {research.base_rate:.2%}\n\n"
        f"Evidence:\n{evidence_block}\n\n"
        f"Research summary: {research.summary}\n\n"
        "Walk through your Bayesian update and produce a final P(YES)."
    )
    return structured_call(SYSTEM_PROMPT, user, ProbabilityEstimate)
