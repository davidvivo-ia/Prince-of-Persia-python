"""Tests de integración del game loop completo (tick.advance)."""

from __future__ import annotations

from pop2026canon.application.controller import Command
from pop2026canon.application.tick import advance
from pop2026canon.domain.game import GameStatus, new_game
from pop2026canon.domain.levels_canon import LEVEL_1, LEVEL_3


class TestGameNew:
    def test_new_game_spawns_kid(self) -> None:
        from pop2026canon.domain.chars import CharId

        g = new_game(LEVEL_1)
        assert g.kid.room == LEVEL_1.start_room
        assert g.kid.curr_col == LEVEL_1.start_col
        assert g.kid.charid is CharId.KID
        assert g.kid.hp_curr == 3
        assert g.running is True

    def test_l1_has_one_guard(self) -> None:
        g = new_game(LEVEL_1)
        # Sala 3 tiene 1 guard según L1 canon
        guards = [c for c in g.others if c.room == 3]
        assert len(guards) == 1


class TestTickAdvance:
    def test_idle_tick_advances_tick_count(self) -> None:
        g = new_game(LEVEL_1)
        g2 = advance(g, Command())
        assert g2.tick_count == 1
        assert g2.running

    def test_kid_idle_stays_in_stand(self) -> None:
        g = new_game(LEVEL_1)
        for _ in range(10):
            g = advance(g, Command())
        # El kid sigue stand frame 15
        assert g.kid.frame == 15

    def test_kid_runs_with_right_input(self) -> None:
        g = new_game(LEVEL_1)
        for _ in range(20):
            g = advance(g, Command(right=True))
        # Sigue en la misma sala o cambió, pero algo se movió
        # (kid empieza facing LEFT en L1 — primero hace turn)
        assert g.kid.curr_seq_id != 0  # se está moviendo

    def test_time_decrements(self) -> None:
        g = new_game(LEVEL_1)
        initial_ticks = g.time.ticks
        g = advance(g, Command())
        # Tras 1 tick, el tiempo bajó (719 → 718)
        assert g.time.ticks < initial_ticks or g.time.minutes < 60

    def test_terminated_game_stops_advancing(self) -> None:
        from dataclasses import replace

        g = new_game(LEVEL_1)
        g = replace(g, status=GameStatus.WON_LEVEL)
        g2 = advance(g, Command())
        # Game terminado → no avanza
        assert g2.tick_count == g.tick_count


class TestLevelLoading:
    def test_level_3_has_skeleton_event(self) -> None:
        from pop2026canon.domain.level import EventKind

        g = new_game(LEVEL_3)
        skel_events = [e for e in g.level.events if e.kind == EventKind.SKELETON_WAKE]
        assert len(skel_events) == 1


class TestImmutability:
    def test_advance_returns_new_game(self) -> None:
        g = new_game(LEVEL_1)
        g2 = advance(g, Command(right=True))
        # Ambos válidos, son objetos distintos
        assert g is not g2
        assert g.tick_count == 0
        assert g2.tick_count == 1
