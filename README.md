# langchain_projects

Personal sandbox for building LLM agents. Each agent lives in its own folder under `agents/` and is run as a Python module from the repo root.

## Layout
```
.
├── .env                    # shared secrets (gitignored)
├── requirements.txt        # shared deps for all agents
├── agents/
│   ├── _template/          # starter scaffold — copy to bootstrap a new agent
│   └── news_digest/        # NewsAPI -> OpenAI -> Telegram daily digest
└── (shared/)               # extracted later, when 2+ agents reuse helpers
```

## Setup
```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in keys
```

## Running an agent
Always run from the repo root so package imports resolve:
```
python -m agents.<agent_name>.main
```

## Adding a new agent
1. `cp -r agents/_template agents/<agent_name>`
2. Edit `agents/<agent_name>/main.py` and `README.md`.
3. Add any new keys to `.env` and document them in the agent's README.
4. If a new dependency is needed, append it to the root `requirements.txt`.

## Agents
| Name | What it does | Entrypoint |
|------|--------------|------------|
| [news_digest](agents/news_digest/) | Daily NewsAPI -> OpenAI -> Telegram digest | `python -m agents.news_digest.main` |

## Conventions
- One agent = one folder under `agents/`.
- Each agent has a `main.py` with a `main()` entrypoint and a `README.md`.
- Shared utilities go in `shared/` — but only after the second agent actually reuses something. Don't pre-build it.
- Secrets stay in the root `.env`; each agent's README lists the keys it needs.
