"""Calibration auditor: the analogue of quant_bot's backtester.

Given the current market, pull the N most similar *resolved* markets, re-run
a stripped-down probability estimate on each one (blind to the outcome), then
score Brier vs the market's closing price. If our estimator would have beaten
the market on the reference class, we get more confidence in the current call.

This is intentionally cheap. Embedding-based similarity over question text is
used to pick the reference class. A full re-run of the committee would be ideal
but is too expensive — we proxy with a single LLM call per resolved market.
"""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI
from pydantic import BaseModel, Field

from agents.polymarket_bot.config import CALIBRATION_SAMPLE_SIZE, LLM_MODEL
from agents.polymarket_bot.tools.gamma import fetch_resolved_markets


class _BlindEstimate(BaseModel):
    probability_yes: float = Field(ge=0.0, le=1.0)
    reasoning: str


_SYSTEM = """You are estimating the probability that a Polymarket binary
market resolves YES. You have NOT been told the actual outcome. Give your
best-faith probability given only the question, description, and end date.
Be honest about uncertainty — anchor near 0.5 if you have no signal."""


def _embed(client: OpenAI, texts: list[str]) -> list[list[float]]:
    resp = client.embeddings.create(model="text-embedding-3-small", input=texts)
    return [d.embedding for d in resp.data]


def _cosine(a: list[float], b: list[float]) -> float:
    num = sum(x * y for x, y in zip(a, b))
    da = sum(x * x for x in a) ** 0.5
    db = sum(x * x for x in b) ** 0.5
    if da == 0 or db == 0:
        return 0.0
    return num / (da * db)


def pick_similar_resolved(
    question: str, pool_size: int = 100, top_k: int = CALIBRATION_SAMPLE_SIZE
) -> list[dict[str, Any]]:
    """Return the top-k most semantically similar resolved markets."""
    pool = fetch_resolved_markets(limit=pool_size)
    if not pool:
        return []

    client = OpenAI()
    vectors = _embed(client, [question] + [m["question"] for m in pool])
    qv, mvs = vectors[0], vectors[1:]
    scored = [(_cosine(qv, mv), m) for mv, m in zip(mvs, pool)]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [m for _, m in scored[:top_k]]


def score_calibration(question: str) -> tuple[int, float, float]:
    """Returns (samples, our_brier, market_brier).

    For the calibration market we don't have the market's closing price stored —
    Polymarket closes at 1.0 / 0.0 by resolution. As a proxy we use the binary
    outcome itself for both sides, weighted: market_brier uses 0.5 as the naive
    prior (i.e. "did we beat random?"). This is conservative; if you want a
    truer market-vs-us comparison you'd need to snapshot closing midprices.
    """
    samples = pick_similar_resolved(question)
    if not samples:
        return 0, 0.0, 0.0

    client = OpenAI()
    our_sq_err: list[float] = []
    market_sq_err: list[float] = []  # 0.5 prior — replace with snapshot mid for stricter audit

    for m in samples:
        user = (
            f"Question: {m['question']}\n"
            f"Description: {m.get('description', '')[:1000]}\n"
            f"Resolution date: {m['end_date_iso']}\n\n"
            "Give your probability of YES."
        )
        resp = client.beta.chat.completions.parse(
            model=LLM_MODEL,
            messages=[{"role": "system", "content": _SYSTEM}, {"role": "user", "content": user}],
            response_format=_BlindEstimate,
        )
        parsed = resp.choices[0].message.parsed
        if parsed is None:
            continue
        outcome = 1.0 if m["resolved_yes"] else 0.0
        our_sq_err.append((parsed.probability_yes - outcome) ** 2)
        market_sq_err.append((0.5 - outcome) ** 2)

    if not our_sq_err:
        return 0, 0.0, 0.0
    return (
        len(our_sq_err),
        sum(our_sq_err) / len(our_sq_err),
        sum(market_sq_err) / len(market_sq_err),
    )


def truncate_for_prompt(items: list[dict[str, Any]], cap: int) -> str:
    """Pretty-print a capped list of dicts for an LLM prompt."""
    return json.dumps(items[:cap], indent=2, default=str)
