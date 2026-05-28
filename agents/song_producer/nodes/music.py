"""Music node: SongBrief -> MusicSpec."""

from __future__ import annotations

from ..config import MUSIC_BACKEND, MUSIC_MODEL, PROMPTS_DIR
from ..schema import MusicSpec, SongBrief

PROMPT_PATH = PROMPTS_DIR / "music.md"


def run(brief: SongBrief) -> MusicSpec:
    raise NotImplementedError("music node not implemented yet — tune in step 1.")
