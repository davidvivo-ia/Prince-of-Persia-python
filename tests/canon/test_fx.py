"""Efectos de presentación: detección de eventos FX y sistemas visuales."""

from __future__ import annotations

import os
from dataclasses import replace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from pop2026canon.application.controller import Command
from pop2026canon.application.tick import advance
from pop2026canon.domain.actions import Seq
from pop2026canon.domain.chars import GuardSpawn
from pop2026canon.domain.game import new_game
from pop2026canon.domain.level import Level
from pop2026canon.domain.levels_canon import CANON_LEVELS
from pop2026canon.domain.room import Room
from pop2026canon.domain.tiles import Tile, encode_tile
from pop2026canon.infrastructure.settings import Settings
from pop2026canon.presentation.fx import (
    FxEvent,
    FxKind,
    Particles,
    detect_fx_events,
    level_is_palace,
    transition_direction,
)

E, F = Tile.EMPTY, Tile.FLOOR


def _level(rows: list[list[Tile]], guards=()) -> Level:  # type: ignore[no-untyped-def]
    fg = tuple(encode_tile(t, 0) for row in rows for t in row)
    room = Room(id=1, fg=fg, bg=tuple([0] * 30), guards=guards)
    return Level(number=2, name="fx", rooms=(room,), start_room=1, start_col=3, start_row=2)


def _kinds(events: list[FxEvent]) -> set[FxKind]:
    return {e.kind for e in events}


class TestDetect:
    def test_hit_on_guard(self) -> None:
        guards = (GuardSpawn(col=5, row=2, direction=-1, skill=0),)
        g = new_game(_level([[E] * 10, [E] * 10, [F] * 10], guards), has_sword=True)
        hurt = replace(
            g,
            others=(replace(g.others[0], curr_seq_id=int(Seq.HIT_BY_SWORD), curr_seq_idx=0),),
        )
        assert FxKind.HIT in _kinds(detect_fx_events(g, hurt))

    def test_parry_sparks(self) -> None:
        g = new_game(_level([[E] * 10, [E] * 10, [F] * 10]))
        parried = replace(g, kid=replace(g.kid, curr_seq_id=int(Seq.ATTACK_PARRIED)))
        assert FxKind.PARRY in _kinds(detect_fx_events(g, parried))

    def test_landing_dust(self) -> None:
        rows = [[E] * 10, [E] * 10, [F] * 10]
        g = new_game(replace(_level(rows), start_row=0))
        events: list[FxEvent] = []
        for _ in range(30):
            prev, g = g, advance(g, Command())
            events += detect_fx_events(prev, g)
        assert FxKind.LAND in _kinds(events)

    def test_tile_crumble_and_crash(self) -> None:
        rows = [[E] * 10, [F] * 10, [F] * 10]
        rows[1][5] = Tile.LOOSE
        g = new_game(replace(_level(rows), start_col=5, start_row=1))
        events: list[FxEvent] = []
        for i in range(60):
            prev = g
            g = advance(g, Command())
            if i == 0:
                g = replace(g, kid=replace(g.kid, curr_col=1))
            events += detect_fx_events(prev, g)
        assert FxKind.CRUMBLE in _kinds(events)
        assert FxKind.CRASH in _kinds(events)

    def test_no_events_across_room_change(self) -> None:
        g = new_game(CANON_LEVELS[0])
        other = replace(g, kid=replace(g.kid, room=g.kid.room % len(g.level.rooms) + 1))
        assert detect_fx_events(g, other) == []


class TestParticles:
    def test_burst_and_decay(self) -> None:
        p = Particles(seed=1)
        p.spawn_for(FxEvent(FxKind.CRASH, 100, 200, 1.5))
        n = len(p.items)
        assert n > 10
        for _ in range(120):
            p.update(1 / 60)
        assert len(p.items) == 0

    def test_deterministic(self) -> None:
        a, b = Particles(seed=7), Particles(seed=7)
        ev = FxEvent(FxKind.PARRY, 50, 50)
        a.spawn_for(ev)
        b.spawn_for(ev)
        assert [(q.vx, q.vy) for q in a.items] == [(q.vx, q.vy) for q in b.items]

    def test_cap(self) -> None:
        p = Particles(seed=1, max_particles=50)
        for _ in range(20):
            p.spawn_for(FxEvent(FxKind.CRASH, 0, 0))
        assert len(p.items) <= 50


class TestMisc:
    def test_palace_levels_match_canon_table(self) -> None:
        assert [n for n in range(1, 15) if level_is_palace(n)] == [4, 5, 6, 10, 11, 14]

    def test_transition_direction(self) -> None:
        lv = CANON_LEVELS[0]
        g = new_game(lv)
        start = lv.room(lv.start_room)
        for link, expected in (
            (start.link_e, (1, 0)),
            (start.link_w, (-1, 0)),
            (start.link_n, (0, -1)),
            (start.link_s, (0, 1)),
        ):
            if link:
                moved = replace(g, kid=replace(g.kid, room=link))
                assert transition_direction(g, moved) == expected


class TestSceneSmoke:
    def test_scene_draws_every_level(self) -> None:
        from pop2026canon.presentation.layout import LAYOUT
        from pop2026canon.presentation.scene import Scene

        pygame.init()
        canvas = pygame.Surface((LAYOUT.window_w, LAYOUT.window_h))
        for lv in CANON_LEVELS:
            g = new_game(lv)
            sc = Scene(Settings())
            sc.on_level_start(g)
            g2 = advance(g, Command())
            sc.on_tick(g, g2)
            sc.update(1 / 60, g2, 0.1)
            sc.draw(canvas, g2, g, 0.5, 0.1, sand=0.5, rewinding=False, show_time=True)
            sc.draw(canvas, g2, g, 1.0, 0.2, sand=None, rewinding=True, show_time=False)
