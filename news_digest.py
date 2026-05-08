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

import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

NEWSAPI_KEY = os.environ["NEWSAPI_KEY"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

OPENAI_MODEL = "gpt-4o"
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


def rank_stories(articles: list[dict]) -> list[dict]:
    """Use the LLM to pick and summarize the top stories."""
    client = OpenAI()

    system_msg = (
        f"You pick the {DIGEST_SIZE} most important news stories from the last 24 hours "
        f"for a reader who cares about: {TOPICS}. "
        "Rank by (1) topical relevance, (2) cross-source consensus — stories covered by "
        "multiple outlets bubble up, (3) consequence (impact, scope, novelty). "
        "Group similar stories: if multiple outlets cover the same event, list it once "
        "and combine the sources. Skip celebrity gossip, sports, and human-interest unless "
        "genuinely consequential. Summaries must be 1–2 sentences and explain WHY the story "
        "matters, not just WHAT happened."
    )
    user_msg = (
        f"Here are {len(articles)} headlines. Pick and summarize the top {DIGEST_SIZE}.\n\n"
        f"{json.dumps(articles, indent=2)}"
    )

    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "news_digest",
                "schema": DIGEST_SCHEMA,
                "strict": True,
            },
        },
    )

    return json.loads(response.choices[0].message.content)["stories"]


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

    print(f"Asking {OPENAI_MODEL} to rank and summarize...", file=sys.stderr)
    stories = rank_stories(articles)
    print(f"  picked {len(stories)} stories", file=sys.stderr)

    message = format_for_telegram(stories)
    print("Sending to Telegram...", file=sys.stderr)
    send_to_telegram(message)
    print("Done.", file=sys.stderr)


if __name__ == "__main__":
    main()
