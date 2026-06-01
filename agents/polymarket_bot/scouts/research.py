"""Research Scout: gathers evidence and proposes a reference-class base rate.

The base rate is the most important number the committee produces — it
anchors the probability scout's final estimate. We force the scout to *name*
the reference class explicitly so the critic can attack a bad choice."""

from __future__ import annotations

import json

from agents.polymarket_bot.config import MAX_LLM_DATA_ITEMS
from agents.polymarket_bot.schema import PolymarketMarket, ResearchSignal
from agents.polymarket_bot.tools.llm import structured_call
from agents.polymarket_bot.tools.research import gather_evidence


SYSTEM_PROMPT = """You are the Research Scout on a Polymarket prediction-market
committee. For a binary YES/NO market you must:

1. Name the most appropriate REFERENCE CLASS for a base rate — what is the
   historical frequency of YES-type outcomes for events of this kind? Be
   specific: "incumbent governors winning re-election 2000–2024" beats
   "political races". If no good reference class exists, name the closest
   analogue and set base_rate near 0.5.

2. Extract 3–8 pieces of EVIDENCE from the supplied news / web results that
   would move a Bayesian's prior on this question. For each: name the source,
   include the URL when available, give a one-sentence summary, and label its
   directional_impact (supports_yes / supports_no / neutral / mixed).

3. Write a 2–3 sentence summary of the state of the world relative to the
   question.

Discard items that don't actually bear on the question. Quality > quantity."""


def run_research_scout(market: PolymarketMarket) -> ResearchSignal:
    items = gather_evidence(market.question, max_news=25, max_web=10)
    items = items[:MAX_LLM_DATA_ITEMS]

    if not items:
        return ResearchSignal(
            base_rate_reference="No external research available (no NEWSAPI_KEY/TAVILY_API_KEY).",
            base_rate=0.5,
            evidence=[],
            summary="No news/search keys configured; falling back to uninformative prior.",
            items_considered=0,
        )

    user = (
        f"Polymarket question: {market.question}\n"
        f"Resolution date: {market.end_date_iso}\n"
        f"Market description: {market.description[:1500]}\n\n"
        f"Recent news + web results (most recent first):\n{json.dumps(items, indent=2)}"
    )
    out = structured_call(SYSTEM_PROMPT, user, ResearchSignal)
    out.items_considered = len(items)
    return out
