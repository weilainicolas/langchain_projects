"""Interactive tuning loop.

End-to-end: theme -> SongBundle, then prompt the user for a rating + notes.
Appends to feedback.jsonl and dumps the raw bundle to runs/<timestamp>/.

Run:
    python -m agents.song_producer.tuning.tune --theme "..."

Stub — fill in once the concept node is wired.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from ..config import FEEDBACK_LOG, TUNING_RUNS_DIR


def log_feedback(entry: dict) -> None:
    FEEDBACK_LOG.parent.mkdir(parents=True, exist_ok=True)
    with FEEDBACK_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def new_run_dir() -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    d = TUNING_RUNS_DIR / ts
    d.mkdir(parents=True, exist_ok=True)
    return d


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--theme", required=True)
    args = parser.parse_args()

    print(f"theme: {args.theme}", file=sys.stderr)
    raise NotImplementedError("tuner not wired yet — depends on graph.run().")


if __name__ == "__main__":
    main()
