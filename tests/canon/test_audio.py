"""Audio sintetizado + puente estado → sonido."""

from __future__ import annotations

import os
from dataclasses import replace

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import numpy as np
import pygame

from pop2026canon.application.audio_bridge import play_transitions
from pop2026canon.domain.actions import Seq
from pop2026canon.domain.game import new_game
from pop2026canon.domain.level import Level
from pop2026canon.domain.levels_canon import LEVEL_1
from pop2026canon.domain.room import Room
from pop2026canon.domain.tiles import Tile, encode_tile
from pop2026canon.infrastructure import audio
from pop2026canon.infrastructure.audio import AudioEngine, Beeper
from pop2026canon.presentation.fx import FxEvent, FxKind


class Recorder:
    def __init__(self) -> None:
        self.played: list[tuple[int, float]] = []

    def play(self, sfx_id: int, pan: float = 0.0, volume: float = 1.0) -> None:
        self.played.append((sfx_id, pan))

    @property
    def ids(self) -> set[int]:
        return {i for i, _ in self.played}


def test_beeper_mute_does_not_crash() -> None:
    pygame.init()
    try:
        beeper = Beeper(mute=True)
        for sfx_id in range(1, 40):
            beeper.play(sfx_id, pan=0.3)
        beeper.music("dungeon")
        beeper.combat(True)
        beeper.update(0.1)
    finally:
        pygame.quit()


def test_sfx_are_clean() -> None:
    recipes = audio._sfx_recipes()
    for sid, buf in recipes.items():
        assert np.isfinite(buf).all(), sid
        assert float(np.max(np.abs(buf))) <= 1.0, sid
        assert len(buf) > 0


def test_music_loops_are_seamless_length() -> None:
    for theme in ("dungeon", "palace"):
        base, combat = audio.music_layers(theme)
        assert len(base) == len(combat)
        assert len(base) / audio.SR > 15
        assert float(np.max(np.abs(base))) <= 0.6


def test_engine_with_dummy_driver() -> None:
    pygame.init()
    try:
        eng = AudioEngine()
        eng.play(audio.SND_CLASH, pan=-0.7)
        eng.music("dungeon")
        eng.combat(True)
        eng.update(1.0)
        eng.loop(audio.SND_REWIND)
        eng.loop(None)
        eng.music(None)
    finally:
        pygame.quit()


def test_play_transitions_no_crash() -> None:
    rec = Recorder()
    prev = new_game(LEVEL_1)
    play_transitions(rec, prev, new_game(LEVEL_1))
    assert rec.played == []


def test_events_map_to_sounds_with_pan() -> None:
    rec = Recorder()
    g = new_game(LEVEL_1)
    play_transitions(
        rec,
        g,
        g,
        [FxEvent(FxKind.PARRY, 600, 200), FxEvent(FxKind.CRASH, 20, 300)],
    )
    by_id = dict(rec.played)
    assert by_id[audio.SND_PARRY] > 0.5, "a la derecha"
    assert by_id[audio.SND_TILE_CRASH] < -0.5, "a la izquierda"


def test_kid_jump_and_chomper_bite() -> None:
    empty, floor = Tile.EMPTY, Tile.FLOOR
    rows = [[empty] * 10, [empty] * 10, [floor] * 10]
    rows[2][7] = Tile.CHOMPER
    fg = tuple(encode_tile(t, 0) for row in rows for t in row)
    lvl = Level(
        number=1,
        name="a",
        rooms=(Room(id=1, fg=fg, bg=tuple([0] * 30)),),
        start_room=1,
        start_col=2,
        start_row=2,
    )
    g = new_game(lvl)
    jumped = replace(g, kid=replace(g.kid, curr_seq_id=int(Seq.STANDING_JUMP)))
    bite = replace(jumped, state=jumped.state.with_state((1, 7, 2), 2))
    rec = Recorder()
    play_transitions(rec, g, bite)
    assert audio.SND_JUMP in rec.ids
    assert audio.SND_CHOMP in rec.ids
