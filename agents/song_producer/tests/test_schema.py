"""Smoke tests for schema constraints."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agents.song_producer.schema import (
    Constraints,
    EmotionalArc,
    GenreFrame,
    Section,
    SongBrief,
    SonicPalette,
)


def _valid_brief_kwargs() -> dict:
    return dict(
        title_options=["A", "B", "C"],
        one_line_premise="A short premise.",
        central_image="a kitchen at 2am",
        emotional_arc=EmotionalArc(start="numb", turn="cracks open", end="quiet relief"),
        narrative_pov="first_person",
        genre=GenreFrame(primary="indie folk", adjacent=["slowcore", "ambient pop"], era_reference="late-90s"),
        sonic_palette=SonicPalette(
            tempo_bpm=(82, 90),
            key_suggestion="A minor",
            energy_curve="low -> builds -> drops",
            texture_keywords=["warm", "tape", "spacious"],
        ),
        structure=[
            Section(section="intro", bars=4, purpose="set scene"),
            Section(section="verse", bars=16, purpose="introduce narrator"),
            Section(section="chorus", bars=8, purpose="anchor image"),
            Section(section="outro", bars=4, purpose="dissolve"),
        ],
        thematic_anchors=["kitchen light", "unfinished tea", "phone face-down"],
        constraints=Constraints(),
        listener="late-night insomniacs in their late 20s",
    )


def test_song_brief_minimal_ok() -> None:
    SongBrief(**_valid_brief_kwargs())


def test_title_options_must_be_three() -> None:
    kw = _valid_brief_kwargs()
    kw["title_options"] = ["A", "B"]
    with pytest.raises(ValidationError):
        SongBrief(**kw)


def test_structure_min_four_sections() -> None:
    kw = _valid_brief_kwargs()
    kw["structure"] = kw["structure"][:3]
    with pytest.raises(ValidationError):
        SongBrief(**kw)
