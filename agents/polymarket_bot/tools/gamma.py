"""Polymarket Gamma API client (read-only).

Gamma serves market + event metadata: question, slug, end date, volume,
liquidity, outcome token ids, and (for resolved markets) the winning outcome.
All endpoints are public — no auth required for the calls we make here.

If the upstream JSON shape changes, isolate the breakage here. The rest of
the bot only touches the typed dicts returned by these functions.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import requests

from agents.polymarket_bot.config import GAMMA_API

_TIMEOUT = 20


def _get(path: str, params: dict[str, Any] | None = None) -> Any:
    resp = requests.get(f"{GAMMA_API}{path}", params=params, timeout=_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _parse_token_ids(raw: Any) -> list[str]:
    """Gamma returns clobTokenIds as either a JSON-encoded string or a list."""
    if isinstance(raw, str):
        try:
            return list(json.loads(raw))
        except json.JSONDecodeError:
            return []
    if isinstance(raw, list):
        return [str(x) for x in raw]
    return []


def _parse_outcome_prices(raw: Any) -> list[float]:
    """Gamma returns outcomePrices as either a JSON-encoded string or a list of strings."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return []
    if isinstance(raw, list):
        out = []
        for x in raw:
            try:
                out.append(float(x))
            except (TypeError, ValueError):
                out.append(0.0)
        return out
    return []


def _days_until(end_iso: str) -> float:
    if not end_iso:
        return 0.0
    try:
        dt = datetime.fromisoformat(end_iso.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    delta = dt - datetime.now(timezone.utc)
    return delta.total_seconds() / 86400


def fetch_market(slug_or_condition: str) -> dict[str, Any]:
    """Look up a single binary market by slug or condition_id. Raises if not found
    or if the market is not a binary YES/NO market.
    """
    raw = _get("/markets", params={"slug": slug_or_condition, "limit": 1})
    if not raw:
        raw = _get("/markets", params={"condition_ids": slug_or_condition, "limit": 1})
    if not raw:
        raise LookupError(f"No Polymarket market found for '{slug_or_condition}'.")

    m = raw[0] if isinstance(raw, list) else raw
    token_ids = _parse_token_ids(m.get("clobTokenIds"))
    prices = _parse_outcome_prices(m.get("outcomePrices"))
    if len(token_ids) != 2 or len(prices) != 2:
        raise ValueError(
            f"Market '{slug_or_condition}' is not a binary YES/NO market "
            f"(found {len(token_ids)} outcomes)."
        )

    return {
        "condition_id": m.get("conditionId") or m.get("condition_id", ""),
        "slug": m.get("slug", ""),
        "question": m.get("question", ""),
        "description": m.get("description", "") or "",
        "end_date_iso": m.get("endDate") or m.get("end_date_iso", ""),
        "yes_token_id": token_ids[0],
        "no_token_id": token_ids[1],
        "gamma_price_yes": prices[0],
        "gamma_price_no": prices[1],
        "volume_24h_usd": float(m.get("volume24hr") or m.get("volumeNum") or 0.0),
        "liquidity_usd": float(m.get("liquidityNum") or 0.0),
        "closed": bool(m.get("closed", False)),
        "days_to_resolution": _days_until(m.get("endDate", "")),
    }


def fetch_resolved_markets(limit: int = 100, tag: str | None = None) -> list[dict[str, Any]]:
    """Pull recently-closed binary markets. Used by the calibration auditor to
    score the probability scout's blind estimates against known outcomes.
    """
    params: dict[str, Any] = {"closed": "true", "limit": limit, "order": "endDate", "ascending": "false"}
    if tag:
        params["tag"] = tag
    raw = _get("/markets", params=params)
    out: list[dict[str, Any]] = []
    for m in raw if isinstance(raw, list) else []:
        token_ids = _parse_token_ids(m.get("clobTokenIds"))
        prices = _parse_outcome_prices(m.get("outcomePrices"))
        if len(token_ids) != 2 or len(prices) != 2:
            continue
        # Polymarket encodes the winner as the outcome with price == 1.0 after close.
        if prices[0] not in (0.0, 1.0) or prices[1] not in (0.0, 1.0):
            continue
        out.append({
            "condition_id": m.get("conditionId", ""),
            "slug": m.get("slug", ""),
            "question": m.get("question", ""),
            "description": m.get("description", "") or "",
            "end_date_iso": m.get("endDate", ""),
            "resolved_yes": prices[0] == 1.0,
        })
    return out
