"""LangGraph state machine: trend -> sentiment -> critic -> auditor -> finalize.

Consensus rules: ticket is only emitted when (a) the Critic does not veto,
(b) the backtest win rate is >= MIN_BACKTEST_WIN_RATE, and (c) R:R >= MIN_RR_RATIO.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from agents.quant_bot.committee.state import CommitteeState
from agents.quant_bot.config import MIN_BACKTEST_WIN_RATE, MIN_RR_RATIO
from agents.quant_bot.schema import TradeTicket
from agents.quant_bot.scouts.auditor import run_auditor
from agents.quant_bot.scouts.critic import run_critic
from agents.quant_bot.scouts.sentiment import run_sentiment_scout
from agents.quant_bot.scouts.trend import run_trend_scout


def _node_trend(state: CommitteeState) -> CommitteeState:
    signal, daily_df = run_trend_scout(state["symbol"])
    return {"trend": signal, "daily_df": daily_df}


def _node_sentiment(state: CommitteeState) -> CommitteeState:
    return {"sentiment": run_sentiment_scout(state["symbol"], state["trend"])}


def _node_critic(state: CommitteeState) -> CommitteeState:
    return {
        "critic": run_critic(
            state["symbol"], state["trend"], state["sentiment"], state["daily_df"]
        )
    }


def _node_auditor(state: CommitteeState) -> CommitteeState:
    if state["critic"].veto:
        return {"backtest": None}  # type: ignore[typeddict-item]
    return {"backtest": run_auditor(state["trend"], state["daily_df"])}


def _node_finalize(state: CommitteeState) -> CommitteeState:
    trend = state["trend"]
    critic = state["critic"]
    backtest = state.get("backtest")

    if critic.veto:
        return {"ticket": None, "rejection_reason": f"Critic veto: {critic.warning}"}

    entry_mid = (trend.entry_low + trend.entry_high) / 2
    rr = abs(trend.target_2 - entry_mid) / max(abs(entry_mid - trend.stop_loss), 1e-9)

    if rr < MIN_RR_RATIO:
        return {
            "ticket": None,
            "rejection_reason": f"R:R {rr:.2f} below required {MIN_RR_RATIO}.",
        }
    if backtest is None or backtest.win_rate < MIN_BACKTEST_WIN_RATE:
        wr = backtest.win_rate if backtest else 0
        return {
            "ticket": None,
            "rejection_reason": (
                f"Backtest win rate {wr:.0%} below required {MIN_BACKTEST_WIN_RATE:.0%} "
                f"(samples={backtest.samples if backtest else 0})."
            ),
        }

    ticket = TradeTicket(
        asset=state["symbol"],
        bias=trend.bias,
        timeframe="D1 (14–60d swing)",
        strategy=trend.strategy,
        entry_range=(trend.entry_low, trend.entry_high),
        targets=[trend.target_1, trend.target_2],
        stop_loss=trend.stop_loss,
        rr_ratio=rr,
        backtest_win_rate=backtest.win_rate,
        backtest_samples=backtest.samples,
        critic_warning=critic.warning,
        sentiment_summary=state["sentiment"].summary,
    )
    return {"ticket": ticket, "rejection_reason": None}


def build_committee():
    g = StateGraph(CommitteeState)
    g.add_node("trend", _node_trend)
    g.add_node("sentiment", _node_sentiment)
    g.add_node("critic", _node_critic)
    g.add_node("auditor", _node_auditor)
    g.add_node("finalize", _node_finalize)

    g.set_entry_point("trend")
    g.add_edge("trend", "sentiment")
    g.add_edge("sentiment", "critic")
    g.add_edge("critic", "auditor")
    g.add_edge("auditor", "finalize")
    g.add_edge("finalize", END)
    return g.compile()
