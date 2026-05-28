"""Pydantic schemas exchanged between nodes.

SongBrief is the contract the concept node produces and both music + lyrics
nodes read from. Keep it stable — both downstream nodes depend on its shape.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

NarrativePOV = Literal["first_person", "second_person", "third_person", "collective_we"]
SectionKind = Literal["intro", "verse", "pre_chorus", "chorus", "bridge", "outro"]


class EmotionalArc(BaseModel):
    start: str
    turn: str
    end: str


class GenreFrame(BaseModel):
    primary: str
    adjacent: list[str] = Field(min_length=2, max_length=2)
    era_reference: str


class SonicPalette(BaseModel):
    tempo_bpm: tuple[int, int]
    key_suggestion: str
    energy_curve: str
    texture_keywords: list[str] = Field(min_length=3, max_length=3)


class Section(BaseModel):
    section: SectionKind
    bars: int
    purpose: str


class Constraints(BaseModel):
    must_include: list[str] = Field(default_factory=list)
    must_avoid: list[str] = Field(default_factory=list)


class SongBrief(BaseModel):
    """Output of the concept node. Shared frame for music + lyrics."""

    title_options: list[str] = Field(min_length=3, max_length=3)
    one_line_premise: str
    central_image: str
    emotional_arc: EmotionalArc
    narrative_pov: NarrativePOV
    genre: GenreFrame
    sonic_palette: SonicPalette
    structure: list[Section] = Field(min_length=4, max_length=7)
    thematic_anchors: list[str] = Field(min_length=3, max_length=5)
    constraints: Constraints
    listener: str


class MusicSpec(BaseModel):
    """Output of the music node. Backend-agnostic — `backend` tags the format."""

    backend: Literal["suno", "musicgen", "abc"]
    prompt: str = Field(description="The prompt or notation string the backend consumes.")
    tempo_bpm: int
    key: str
    section_map: list[Section] = Field(description="Finalized section list (may refine the brief).")
    notes: str = ""


class Lyrics(BaseModel):
    """Output of the lyrics node."""

    title: str
    sections: list[dict] = Field(description="[{section, lines: [str]}] in performance order.")


class SongBundle(BaseModel):
    """Final artifact returned by the graph."""

    brief: SongBrief
    music: MusicSpec
    lyrics: Lyrics
