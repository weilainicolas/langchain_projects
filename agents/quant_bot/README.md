# quant_bot — Sentinel Committee

Multi-agent crypto swing-trading committee per `prd.txt`. A LangGraph state machine routes a candidate setup through four specialists; a `TradeTicket` is only emitted on consensus.

## Pipeline

```
        ┌──────────────┐    ┌──────────────────┐    ┌─────────┐    ┌─────────┐    ┌──────────┐
symbol →│ Trend Scout  │ →  │ Sentiment Scout  │ →  │ Critic  │ →  │ Auditor │ →  │ Finalize │ → ticket / rejection
        └──────────────┘    └──────────────────┘    └─────────┘    └─────────┘    └──────────┘
```

- **Trend Scout** — pulls W1/D1/H4 OHLCV via CCXT, computes EMA50/200, RSI, Bollinger, ATR, then asks the LLM to propose entry / target / stop.
- **Sentiment Scout** — fetches recent news (NewsAPI), classifies tone, flags divergence with proposed bias.
- **Adversarial Critic** — Red Team. Hunts for traps (RSI extremes, broken regime, bad R:R math). May veto.
- **Backtest Auditor** — deterministic walk-forward over the last 2 years of daily bars. Finds setups whose RSI/EMA-distance signature matches the proposal and counts target-vs-stop hits within a 60-day window.

## Consensus rules
A ticket is emitted only when **all** of:
- Critic does not veto.
- R:R (T2 vs midpoint vs stop) ≥ **3.0**.
- Backtest win rate ≥ **55%**.

## Run
```
python -m agents.quant_bot.main --asset BTC/USDT --skip-liquidity
python -m agents.quant_bot.main --asset ETH/USDT --exchange kraken
```

Default exchange is **kraken** (binance is geo-blocked from the US). Override with `--exchange` or the `QUANT_BOT_EXCHANGE` env var. The `$100M 24h volume` filter is per-exchange, so smaller venues will fail it — use `--skip-liquidity` for testing.

## Required env vars
- `OPENAI_API_KEY` (gpt-4o for the LLM-driven scouts).
- `NEWSAPI_KEY` *(optional)* — without it the Sentiment Scout returns neutral.

## Tests
Synthetic-data only (no network, no LLM):
```
pytest agents/quant_bot/tests/
```

## Layout
```
quant_bot/
├── main.py                # CLI entrypoint, ticket renderer
├── schema.py              # Pydantic: TrendSignal, SentimentSignal, CriticVerdict, BacktestResult, TradeTicket
├── config.py              # model + thresholds + timeframes
├── tools/
│   ├── market_data.py     # CCXT fetcher (Binance)
│   ├── indicators.py      # EMA, RSI, Bollinger, ATR (hand-rolled)
│   ├── liquidity.py       # >$100M 24h volume gate
│   ├── news.py            # NewsAPI shim (stand-in for Crawl4AI in v1)
│   ├── llm.py             # OpenAI structured-output helper
│   └── backtester.py      # HistoricalValidator: walk-forward simulation
├── scouts/
│   ├── trend.py
│   ├── sentiment.py
│   ├── critic.py
│   └── auditor.py
└── committee/
    ├── state.py           # CommitteeState TypedDict
    └── engine.py          # LangGraph wiring + consensus rules
```

## v1 deviations from PRD
Pragmatic shortcuts to get end-to-end working — clean extension points are left:
- **Sentiment data**: NewsAPI is used instead of Crawl4AI. On-chain "smart money" wallet tracking is not implemented.
- **Vision**: chart-image analysis via Gemini Vision is not wired up. Indicators are read numerically.
- **LLM**: OpenAI `gpt-4o` (single factory in `tools/llm.py`); swap to Gemini by replacing that file.

## Notes
- Backtest "similar setups" = bars within ±5 RSI and ±1% EMA50 distance of the proposed entry. Rough but deterministic.
- The auditor uses *daily* bars only; it's a sanity check, not a high-fidelity execution sim.
- All exchange calls are read-only (CCXT public endpoints). No order placement anywhere.
