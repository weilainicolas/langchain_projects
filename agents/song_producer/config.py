"""Static config for song_producer."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

MusicBackend = Literal["suno", "musicgen", "abc"]

MUSIC_BACKEND: MusicBackend = "suno"

CONCEPT_MODEL = "gpt-4o-mini"
MUSIC_MODEL = "gpt-4o-mini"
LYRICS_MODEL = "gpt-4o-mini"

PROMPTS_DIR = Path(__file__).parent / "prompts"
TUNING_RUNS_DIR = Path(__file__).parent / "tuning" / "runs"
FEEDBACK_LOG = Path(__file__).parent / "tuning" / "feedback.jsonl"
