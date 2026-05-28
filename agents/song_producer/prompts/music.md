# Music Agent

Placeholder. Tuned in step 1.

Reads a SongBrief, emits a MusicSpec (see schema.py). Output format depends
on `config.MUSIC_BACKEND` — Suno text prompt, MusicGen text prompt, or ABC
notation. The music node may refine `structure` from the brief; the lyrics
node downstream uses the refined `section_map`, not the original.
