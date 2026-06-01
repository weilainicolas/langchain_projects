# polymarket_bot — Prediction Market Committee

Multi-agent research committee that scores a single Polymarket binary market and emits a `BetTicket` when consensus rules pass. Research-only mode: **no order placement, no wallet required**.

Mirrors the [`quant_bot`](../quant_bot/) LangGraph pattern with prediction-market-specific scouts.

## Pipeline

```
       ┌──────────────┐   ┌──────────┐   ┌─────────────┐   ┌────────┐   ┌─────────────┐   ┌──────────┐
slug → │ Load Market  │ → │ Research │ → │ Probability │ → │ Critic │ → │ Calibration │ → │ Finalize │ → ticket / rejection
       └──────────────┘   └──────────┘   └─────────────┘   └────────┘   └─────────────┘   └──────────┘
```

- **Load Market** — pulls metadata via Gamma API + live midprice/spread via CLOB book.
- **Research Scout** — names a reference class for the base rate; pulls news + web evidence; tags each item's directional impact.
- **Probability Scout** — Bayesian walk-through: anchor at base rate, adjust per evidence item, land on P(YES).
- **Adversarial Critic** — assumes the market is right; must articulate what the market is pricing in that we're ignoring. May veto.
- **Calibration Auditor** — pulls the N most semantically similar *resolved* markets, re-asks the probability scout blind, scores Brier vs. naive prior.

## Consensus rules

A `BetTicket` is emitted only when **all** of:
- Liquidity gate passes: `volume_24h ≥ $50k`, `spread ≤ 300bps`, `> 1 day to resolution`.
- Critic does not veto.
- `|our_p - market_p| × 100 ≥ 5pp` edge.
- Calibration auditor's Brier beats the naive 0.5 prior (or returned zero samples).

Sizing: fractional Kelly (25% of full Kelly), capped at 5% of bankroll.

## Run

```
python -m agents.polymarket_bot.main --market <slug-or-condition-id>
```

Examples:
```
python -m agents.polymarket_bot.main --market will-trump-win-2024-presidential-election
python -m agents.polymarket_bot.main --market 0xabc123...
```

## Required env vars

- `OPENAI_API_KEY` — for `gpt-4o` (scouts + embeddings for calibration).
- `NEWSAPI_KEY` *(optional)* — primary research source. Without it, the research scout falls back to an uninformative 0.5 prior.
- `TAVILY_API_KEY` *(optional)* — broader web search for niche markets.

## Layout

```
polymarket_bot/
├── main.py                   # CLI entrypoint, ticket renderer
├── schema.py                 # Pydantic: PolymarketMarket, ResearchSignal, ProbabilityEstimate,
│                             #          CriticVerdict, CalibrationResult, BetTicket
├── config.py                 # thresholds (edge, volume, kelly fraction, etc.)
├── tools/
│   ├── gamma.py              # Polymarket Gamma API (markets, resolved markets)
│   ├── clob.py               # Polymarket CLOB API (orderbook midprice + spread)
│   ├── liquidity.py          # volume + spread + time-to-resolution gate
│   ├── research.py           # NewsAPI + Tavily fetchers
│   ├── calibration.py        # similar-resolved-market Brier scorer
│   └── llm.py                # OpenAI structured-output helper
├── scouts/
│   ├── research.py
│   ├── probability.py
│   ├── critic.py
│   └── auditor.py
└── committee/
    ├── state.py              # CommitteeState TypedDict
    └── engine.py             # LangGraph wiring + consensus rules
```

## Known v1 limitations

- **Calibration is approximate.** We compare our Brier against a naive 0.5 prior, not against the market's actual closing midprice for each resolved market. A stricter audit would snapshot pre-resolution midprices — see TODO in `tools/calibration.py`.
- **No portfolio layer.** Each invocation is one market in isolation. Bankroll allocation across simultaneous bets is the user's job.
- **No order placement.** Adding live trading would require `py_clob_client`, a funded Polygon wallet, and EIP-712 signing — and Polymarket's ToS blocks US persons from trading.
- **Single-pass calibration.** The calibration auditor uses one LLM call per similar market rather than a full committee re-run, for cost reasons.
