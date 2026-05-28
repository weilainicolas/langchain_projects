# song_producer

Theme -> structured song brief -> music spec + lyrics. Three-node LangGraph:
concept -> music -> lyrics. Music output is a backend-agnostic spec (Suno
prompt, MusicGen prompt, or chord chart) selected in `config.py`.

## Run
```
python -m agents.song_producer.main --theme "quiet desperation in a kitchen at 2am"
```

## Tuning
Iterate on each node's prompt with human-in-the-loop ratings:
```
python -m agents.song_producer.tuning.tune --node concept
```
Each run appends to `tuning/feedback.jsonl` and dumps raw I/O to `tuning/runs/`.

Once a prompt is good, the markdown in `prompts/<node>.md` is what gets
lifted into a Claude Code Skill.

## Required env vars
- `OPENAI_API_KEY`

## Layout
- `prompts/` — node prompts as markdown (Skill-ready)
- `nodes/` — LangGraph nodes, one per agent
- `graph.py` — wiring
- `schema.py` — Pydantic types passed between nodes
- `tuning/` — feedback log + interactive tuner (gitignored runs)

## Music backend
Set `MUSIC_BACKEND` in `config.py` to one of: `suno`, `musicgen`, `abc`.
This only changes how the music node serializes its output — the upstream
`SongBrief` is identical.
