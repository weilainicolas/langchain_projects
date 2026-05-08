"""Crypto news fetcher (NewsAPI). Stand-in for Crawl4AI in v1."""

from __future__ import annotations

import os

import requests


def fetch_crypto_news(asset_keyword: str, max_items: int = 25) -> list[dict]:
    """Pull recent English news mentioning the asset. Returns [] on missing key."""
    api_key = os.environ.get("NEWSAPI_KEY")
    if not api_key:
        return []
    resp = requests.get(
        "https://newsapi.org/v2/everything",
        params={
            "q": asset_keyword,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": max_items,
            "apiKey": api_key,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return [
        {
            "title": a.get("title", ""),
            "description": a.get("description") or "",
            "source": (a.get("source") or {}).get("name", ""),
            "published_at": a.get("publishedAt", ""),
        }
        for a in resp.json().get("articles", [])
        if a.get("title") and a["title"] != "[Removed]"
    ]
