"""LangGraph state machine:
  load_market -> research -> probability -> critic -> calibration -> finalize.

Consensus rules — emit a ticket only when ALL of:
- Liquidity gate passes (volume / spread / time-to-resolution).
- Critic does not veto.
- |our_p - market_p| * 100 >= MIN_EDGE_PP.
- Calibration auditor beats the naive prior on similar resolved markets,
  OR returned zero samples (no calibration data ≠ veto).
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from agents.polymarket_bot.committee.state import CommitteeState
from agents.polymarket_bot.config import KELLY_FRACTION, MAX_STAKE_PCT, MIN_EDGE_PP
from agents.polymarket_bot.schema import BetTicket, PolymarketMarket
from agents.polymarket_bot.scouts.auditor import run_calibration_auditor
from agents.polymarket_bot.scouts.critic import run_critic
from agents.polymarket_bot.scouts.probability import run_probability_scout
from agents.polymarket_bot.scouts.research import run_research_scout
from agents.polymarket_bot.tools.clob import fetch_midprice_and_spread
from agents.polymarket_bot.tools.gamma import fetch_market
from agents.polymarket_bot.tools.liquidity import passes_liquidity_filter


def _node_load_market(state: CommitteeState) -> CommitteeState:
    raw = fetch_market(state["market_ref"])
    yes_mid, yes_spread = fetch_midprice_and_spread(raw["yes_token_id"])
    no_mid, no_spread = fetch_midprice_and_spread(raw["no_token_id"])

    # Fall back to Gamma's snapshot if the CLOB book is empty.
    if yes_mid <= 0:
        yes_mid = raw["gamma_price_yes"]
    if no_mid <= 0:
        no_mid = raw["gamma_price_no"]

    market = PolymarketMarket(
        condition_id=raw["condition_id"],
        slug=raw["slug"],
        question=raw["question"],
        description=raw["description"],
        end_date_iso=raw["end_date_iso"],
        yes_token_id=raw["yes_token_id"],
        no_token_id=raw["no_token_id"],
        market_price_yes=max(0.0, min(1.0, yes_mid)),
        market_price_no=max(0.0, min(1.0, no_mid)),
        spread_bps=min(yes_spread, no_spread),
        volume_24h_usd=raw["volume_24h_usd"],
        days_to_resolution=raw["days_to_resolution"],
    )
    return {"market": market}


def _node_research(state: CommitteeState) -> CommitteeState:
    return {"research": run_research_scout(state["market"])}


def _node_probability(state: CommitteeState) -> CommitteeState:
    return {"estimate": run_probability_scout(state["market"], state["research"])}


def _node_critic(state: CommitteeState) -> CommitteeState:
    return {
        "critic": run_critic(state["market"], state["research"], state["estimate"])
    }


def _node_calibration(state: CommitteeState) -> CommitteeState:
    # Skip the expensive blind re-estimation if the critic already vetoed.
    if state["critic"].veto:
        return {"calibration": None}  # type: ignore[typeddict-item]
    return {"calibration": run_calibration_auditor(state["market"])}


def _kelly_fraction(p: float, market_price: float) -> float:
    """Kelly fraction for a binary YES contract trading at `market_price`,
    where we believe true probability is `p`. Returns 0 on no edge.

    Payoff per $1: (1/market_price) - 1 = b. Kelly: f* = (b*p - q) / b.
    """
    if not 0 < market_price < 1 or not 0 <= p <= 1:
        return 0.0
    b = (1 / market_price) - 1
    q = 1 - p
    f = (b * p - q) / b if b > 0 else 0.0
    return max(0.0, f)


def _node_finalize(state: CommitteeState) -> CommitteeState:
    market = state["market"]
    critic = state["critic"]
    estimate = state["estimate"]
    calibration = state.get("calibration")
    research = state["research"]

    ok, reason = passes_liquidity_filter(
        market.volume_24h_usd, market.spread_bps, market.days_to_resolution
    )
    if not ok:
        return {"ticket": None, "rejection_reason": f"Liquidity gate: {reason}"}

    if critic.veto:
        return {"ticket": None, "rejection_reason": f"Critic veto: {critic.warning}"}

    edge_pp = (estimate.our_probability_yes - market.market_price_yes) * 100
    if abs(edge_pp) < MIN_EDGE_PP:
        return {
            "ticket": None,
            "rejection_reason": (
                f"Edge {edge_pp:+.1f}pp below required {MIN_EDGE_PP}pp "
                f"(our {estimate.our_probability_yes:.2%} vs market {market.market_price_yes:.2%})."
            ),
        }

    if calibration is not None and calibration.samples > 0 and not calibration.beats_market:
        return {
            "ticket": None,
            "rejection_reason": (
                f"Calibration audit failed: our Brier {calibration.our_brier:.3f} "
                f">= naive prior {calibration.market_brier:.3f} on {calibration.samples} samples."
            ),
        }

    side = "YES" if edge_pp > 0 else "NO"
    market_price_for_side = market.market_price_yes if side == "YES" else market.market_price_no
    our_p_for_side = estimate.our_probability_yes if side == "YES" else 1 - estimate.our_probability_yes

    full_kelly = _kelly_fraction(our_p_for_side, market_price_for_side)
    fractional = full_kelly * KELLY_FRACTION
    recommended = min(fractional, MAX_STAKE_PCT)

    ticket = BetTicket(
        market_question=market.question,
        condition_id=market.condition_id,
        slug=market.slug,
        side=side,
        market_price=market_price_for_side,
        our_probability=our_p_for_side,
        edge_pp=abs(edge_pp),
        kelly_fraction_of_bankroll=full_kelly,
        recommended_stake_pct=recommended,
        confidence=estimate.confidence,
        critic_warning=critic.warning,
        calibration_note=calibration.notes if calibration else "skipped",
        evidence=research.evidence,
        days_to_resolution=market.days_to_resolution,
    )
    return {"ticket": ticket, "rejection_reason": None}


def build_committee():
    g = StateGraph(CommitteeState)
    g.add_node("load_market", _node_load_market)
    g.add_node("research", _node_research)
    g.add_node("probability", _node_probability)
    g.add_node("critic", _node_critic)
    g.add_node("calibration", _node_calibration)
    g.add_node("finalize", _node_finalize)

    g.set_entry_point("load_market")
    g.add_edge("load_market", "research")
    g.add_edge("research", "probability")
    g.add_edge("probability", "critic")
    g.add_edge("critic", "calibration")
    g.add_edge("calibration", "finalize")
    g.add_edge("finalize", END)
    return g.compile()
