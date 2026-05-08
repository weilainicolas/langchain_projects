# news_digest

Pulls top headlines from NewsAPI, asks OpenAI (`gpt-4o`) to rank and summarize the top 10, and sends the digest to Telegram as HTML.

## Run
```
python -m agents.news_digest.main
```

## Required env vars
- `OPENAI_API_KEY`
- `NEWSAPI_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## Notes
- Topics, digest size, and source queries are constants at the top of `main.py`.
- Telegram messages are split at 4096 chars on paragraph boundaries.
