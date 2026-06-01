"""Adversarial Critic: hunts for the bull/bear case the committee missed.

In a prediction market, the market price IS a forecast — if a sharp,
liquid market disagrees with us by 5+ points, the prior is that the market
is right and we are wrong. The critic exists to make us articulate WHY we
think we're the ones with edge."""

from __future__ import annotations

from agents.polymarket_bot.schema import (
    CriticVerdict,
    PolymarketMarket,
    ProbabilityEstimate,
    ResearchSignal,
)
from agents.polymarket_bot.tools.llm import structured_call


SYSTEM_PROMPT = """You are the Adversarial Critic on a Polymarket committee.
A scout has proposed a P(YES) that disagrees with the market. Your job is to
invalidate the trade — assume the market is right by default.

VETO (veto=True) when ANY of the following is true:
- The reference class is wrong or cherry-picked.
- The evidence supplied is mostly stale, off-topic, or low-quality.
- The probability scout ignored a major obvious factor (e.g. ignored a
  scheduled debate, court ruling, earnings date, weather forecast).
- The estimate hand-waves through a known uncertainty (e.g. assumes a
  recount won't happen when one is currently being litigated).
- The market is dominated by sharp traders on a topic with well-known
  information asymmetry (insider trading, sports betting on team news).

Otherwise veto=False, but always fill `warning` with the single strongest
risk and `market_pricing_in` with the bullish-for-the-other-side story you
think the market is encoding."""


def run_critic(
    market: PolymarketMarket,
    research: ResearchSignal,
    estimate: ProbabilityEstimate,
) -> CriticVerdict:
    edge_pp = (estimate.our_probability_yes - market.market_price_yes) * 100
    side = "YES" if edge_pp > 0 else "NO"
    evidence_lines = "\n".join(
        f"- [{e.directional_impact}] {e.source}: {e.summary}" for e in research.evidence
    ) or "(none)"

    user = (
        f"Market: {market.question}\n"
        f"Market price YES: {market.market_price_yes:.3f}\n"
        f"Our P(YES):       {estimate.our_probability_yes:.3f}\n"
        f"Implied edge:     {edge_pp:+.1f}pp on the {side} side\n"
        f"Days to resolve:  {market.days_to_resolution:.1f}\n\n"
        f"Reference class:  {research.base_rate_reference} (base={research.base_rate:.2%})\n"
        f"Confidence:       {estimate.confidence}\n\n"
        f"Probability scout reasoning:\n{estimate.reasoning}\n\n"
        f"Evidence list:\n{evidence_lines}\n\n"
        "Find the strongest reason this edge could be illusory. Decide whether to veto."
    )
    return structured_call(SYSTEM_PROMPT, user, CriticVerdict)
