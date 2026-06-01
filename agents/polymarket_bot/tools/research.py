"""Research fetchers: news + optional web search.

NewsAPI is the primary source (same pattern as quant_bot). If a Tavily key is
present we also pull a few web-search results to broaden coverage beyond the
news APIs' indexed sources — useful for niche / political / sports markets.

All fetchers degrade gracefully: missing key → empty list, never an exception.
"""

from __future__ import annotations

import os
from typing import Any

import requests

_NEWSAPI_TIMEOUT = 15
_TAVILY_TIMEOUT = 20


def fetch_news(query: str, max_items: int = 25) -> list[dict[str, Any]]:
    """Recent English news mentioning the query. [] on missing NEWSAPI_KEY."""
    api_key = os.environ.get("NEWSAPI_KEY")
    if not api_key:
        return []
    resp = requests.get(
        "https://newsapi.org/v2/everything",
        params={
            "q": query,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": max_items,
            "apiKey": api_key,
        },
        timeout=_NEWSAPI_TIMEOUT,
    )
    resp.raise_for_status()
    return [
        {
            "title": a.get("title", ""),
            "description": a.get("description") or "",
            "url": a.get("url", ""),
            "source": (a.get("source") or {}).get("name", ""),
            "published_at": a.get("publishedAt", ""),
        }
        for a in resp.json().get("articles", [])
        if a.get("title") and a["title"] != "[Removed]"
    ]


def fetch_web_search(query: str, max_items: int = 10) -> list[dict[str, Any]]:
    """Tavily web search. [] on missing TAVILY_API_KEY."""
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return []
    resp = requests.post(
        "https://api.tavily.com/search",
        json={
            "api_key": api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": max_items,
            "include_answer": False,
        },
        timeout=_TAVILY_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    return [
        {
            "title": r.get("title", ""),
            "description": r.get("content", "")[:500],
            "url": r.get("url", ""),
            "source": "tavily",
            "published_at": r.get("published_date", ""),
        }
        for r in data.get("results", [])
    ]


def gather_evidence(query: str, max_news: int = 25, max_web: int = 10) -> list[dict[str, Any]]:
    """Convenience: news first, then web search, deduped by URL."""
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in fetch_news(query, max_news) + fetch_web_search(query, max_web):
        url = item.get("url", "")
        key = url or item.get("title", "")
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out
