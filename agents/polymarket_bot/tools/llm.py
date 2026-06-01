"""Thin OpenAI wrapper. Uses the structured-output `parse()` API: pass a
Pydantic class as `response_format`, get a validated instance back.

Identical pattern to agents/quant_bot/tools/llm.py — kept independent so the
two bots can evolve their LLM stacks separately."""

from __future__ import annotations

from typing import TypeVar

from openai import OpenAI
from pydantic import BaseModel

from agents.polymarket_bot.config import LLM_MODEL

T = TypeVar("T", bound=BaseModel)

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


def structured_call(system: str, user: str, model_cls: type[T]) -> T:
    """Send (system, user) and return a validated `model_cls` instance."""
    resp = _get_client().beta.chat.completions.parse(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format=model_cls,
    )
    parsed = resp.choices[0].message.parsed
    if parsed is None:
        raise RuntimeError(f"OpenAI returned no parsed payload for {model_cls.__name__}.")
    return parsed
