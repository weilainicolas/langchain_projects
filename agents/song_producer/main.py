"""Theme -> SongBundle (brief + music spec + lyrics).

Run from repo root:
    python -m agents.song_producer.main --theme "..."

Requires: .env with OPENAI_API_KEY
"""

from __future__ import annotations

import argparse
import json
import sys

from dotenv import load_dotenv

load_dotenv()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--theme", required=True, help="Free-form creative brief.")
    args = parser.parse_args()

    from .graph import run

    bundle = run(theme=args.theme)
    json.dump(bundle.model_dump(), sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
