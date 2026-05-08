"""Daily news digest: NewsAPI -> Claude (rank + summarize) -> Telegram.

Run: python news_digest.py
Requires: .env with ANTHROPIC_API_KEY, NEWSAPI_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
"""

from __future__ import annotations

import html
import json
import os
import sys
from datetime import datetime, timezone

import anthropic
import requests
from dotenv import load_dotenv

load_dotenv()

NEWSAPI_KEY = os.environ["NEWSAPI_KEY"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

TOPICS = "AI / tech, business / markets, world / geopolitics"
DIGEST_SIZE = 10
TELEGRAM_MAX_LEN = 4096


def fetch_headlines() -> list[dict]:
    """Pull top headlines across categories and English-speaking regions."""
    queries = [
        {"country": "us", "category": "technology"},
        {"country": "us", "category": "business"},
        {"country": "us", "category": "general"},
        {"country": "gb", "category": "general"},
    ]
    seen_urls: set[str] = set()
    articles: list[dict] = []
    for q in queries:
        resp = requests.get(
            "https://newsapi.org/v2/top-headlines",
            params={**q, "pageSize": 50, "apiKey": NEWSAPI_KEY},
            timeout=15,
        )
        resp.raise_for_status()
        for art in resp.json().get("articles", []):
            url = art.get("url")
            if not url or url in seen_urls:
                continue
            if not art.get("title") or art["title"] == "[Removed]":
                continue
            seen_urls.add(url)
            articles.append(
                {
                    "title": art["title"],
                    "description": art.get("description") or "",
                    "source": (art.get("source") or {}).get("name", ""),
                    "url": url,
                    "published_at": art.get("publishedAt", ""),
                }
            )
    return articles


DIGEST_SCHEMA = {
    "type": "object",
    "properties": {
        "stories": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "rank": {"type": "integer"},
                    "headline": {"type": "string"},
                    "summary": {
                        "type": "string",
                        "description": "1-2 sentences explaining what happened and why it matters.",
                    },
                    "category": {
                        "type": "string",
                        "enum": ["AI/tech", "business", "geopolitics", "other"],
                    },
                    "sources": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Outlets covering this story (from input).",
                    },
                    "url": {"type": "string"},
                },
                "required": ["rank", "headline", "summary", "category", "sources", "url"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["stories"],
    "additionalProperties": False,
}


def rank_with_claude(articles: list[dict]) -> list[dict]:
    """Use Claude to pick and summarize the top stories."""
    client = anthropic.Anthropic()

    prompt = f"""You are picking the {DIGEST_SIZE} most important news stories from the last 24 hours for a reader who cares about: {TOPICS}.

You have {len(articles)} headlines below as JSON. Rank them by importance using these criteria:
1. Topical relevance (AI/tech, business/markets, world/geopolitics)
2. Cross-source consensus — stories covered by multiple outlets bubble up
3. Your own judgment of consequence (impact, scope, novelty)

Group similar stories: if 5 outlets cover the same event, list it once with all sources combined. Skip celebrity gossip, sports, and human-interest unless genuinely consequential.

Write summaries that explain WHY a story matters, not just WHAT happened. Be tight — 1-2 sentences each.

Headlines:
{json.dumps(articles, indent=2)}
"""

    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=8000,
        thinking={"type": "adaptive"},
        output_config={
            "effort": "high",
            "format": {"type": "json_schema", "schema": DIGEST_SCHEMA},
        },
        messages=[{"role": "user", "content": prompt}],
    )

    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)["stories"]


def format_for_telegram(stories: list[dict]) -> str:
    """Format the digest as Telegram HTML."""
    today = datetime.now(timezone.utc).strftime("%b %d, %Y")
    lines = [f"<b>📰 Daily Digest — {today}</b>", ""]
    cat_emoji = {"AI/tech": "🤖", "business": "💼", "geopolitics": "🌍", "other": "📌"}

    for s in sorted(stories, key=lambda x: x["rank"]):
        emoji = cat_emoji.get(s["category"], "📌")
        headline = html.escape(s["headline"])
        summary = html.escape(s["summary"])
        sources = html.escape(", ".join(s["sources"][:3]))
        url = html.escape(s["url"], quote=True)
        lines.append(f"<b>{s['rank']}. {emoji} {headline}</b>")
        lines.append(summary)
        lines.append(f'<i>{sources}</i> — <a href="{url}">read</a>')
        lines.append("")

    return "\n".join(lines).rstrip()


def send_to_telegram(text: str) -> None:
    """Send text to Telegram, splitting if it exceeds the 4096 char limit."""
    chunks: list[str] = []
    remaining = text
    while len(remaining) > TELEGRAM_MAX_LEN:
        split = remaining.rfind("\n\n", 0, TELEGRAM_MAX_LEN)
        if split == -1:
            split = TELEGRAM_MAX_LEN
        chunks.append(remaining[:split])
        remaining = remaining[split:].lstrip()
    chunks.append(remaining)

    for chunk in chunks:
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": chunk,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=15,
        )
        resp.raise_for_status()


def main() -> None:
    print("Fetching headlines...", file=sys.stderr)
    articles = fetch_headlines()
    print(f"  got {len(articles)} unique articles", file=sys.stderr)

    if not articles:
        print("No articles fetched — check NEWSAPI_KEY or rate limits.", file=sys.stderr)
        sys.exit(1)

    print("Asking Claude to rank and summarize...", file=sys.stderr)
    stories = rank_with_claude(articles)
    print(f"  picked {len(stories)} stories", file=sys.stderr)

    message = format_for_telegram(stories)
    print("Sending to Telegram...", file=sys.stderr)
    send_to_telegram(message)
    print("Done.", file=sys.stderr)


if __name__ == "__main__":
    main()
