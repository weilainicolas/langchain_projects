"""Lyrics node: SongBrief + MusicSpec -> Lyrics."""

from __future__ import annotations

from ..config import LYRICS_MODEL, PROMPTS_DIR
from ..schema import Lyrics, MusicSpec, SongBrief

PROMPT_PATH = PROMPTS_DIR / "lyrics.md"


def run(brief: SongBrief, music: MusicSpec) -> Lyrics:
    raise NotImplementedError("lyrics node not implemented yet — tune in step 2.")
