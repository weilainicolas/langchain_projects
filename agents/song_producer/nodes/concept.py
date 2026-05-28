"""Concept node: theme -> SongBrief."""

from __future__ import annotations

from ..config import CONCEPT_MODEL, PROMPTS_DIR
from ..schema import SongBrief

PROMPT_PATH = PROMPTS_DIR / "concept.md"


def run(theme: str) -> SongBrief:
    raise NotImplementedError("concept node not implemented yet — wire up after first tuning pass.")
