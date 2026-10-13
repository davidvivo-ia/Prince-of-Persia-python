"""Ayudas del modo moderno: rebobinado y punto de control por sala."""

from __future__ import annotations

from dataclasses import replace

from pop2026canon.application.assist import (
    SAND_MAX,
    SAND_REFILL_EVERY,
    RoomCheckpoint,
    TimeRewind,
    is_safe_checkpoint,
)
from pop2026canon.application.controller import Command
from pop2026canon.application.tick import advance
from pop2026canon.domain.game import GameStatus, new_game
from pop2026canon.domain.level import Level
from pop2026canon.domain.room import Room
from pop2026canon.domain.tiles import Tile, encode_tile

E, F = Tile.EMPTY, Tile.FLOOR


def _pit_level() -> Level:
    """Suelo con un pozo mortal (sin sala debajo) en la columna 6."""
    bot = [F] * 10
    bot[6] = E
    fg = tuple(encode_tile(t, 0) for row in [[E] * 10, [E] * 10, bot] for t in row)
    room = Room(id=1, fg=fg, bg=tuple([0] * 30))
    return Level(number=1, name="pit", rooms=(room,), start_room=1, start_col=2, start_row=2)


class TestTimeRewind:
    def test_rewind_restores_exact_states(self) -> None:
        g = new_game(_pit_level())
        tw = TimeRewind()
        states = [g]
        for _ in range(10):
            tw.record(g)
            g = advance(g, Command(right=True))
            states.append(g)
        for expected in reversed(states[:-1]):
            assert tw.step_back() == expected

    def test_rewind_undoes_a_fatal_fall(self) -> None:
        g = new_game(_pit_level())
        tw = TimeRewind()
        for _ in range(60):
            tw.record(g)
            g = advance(g, Command(right=True))
            if g.kid.alive >= 0:
                break
        assert g.kid.alive >= 0, "el kid corre al pozo y muere"
        while g.kid.alive >= 0 or g.kid.curr_col >= 6:
            back = tw.step_back()
            assert back is not None
            g = back
        assert g.kid.alive < 0
        assert g.status is GameStatus.PLAYING

    def test_sand_limits_and_refills(self) -> None:
        g = new_game(_pit_level())
        tw = TimeRewind(sand=2)
        for _ in range(5):
            tw.record(g)
        refilled = 2 + 5 // SAND_REFILL_EVERY
        assert tw.sand == refilled
        for _ in range(refilled):
            assert tw.step_back() is not None
        assert tw.step_back() is None, "sin arena no se rebobina"
        assert not tw.can_rewind

    def test_sand_capped(self) -> None:
        tw = TimeRewind()
        g = new_game(_pit_level())
        for _ in range(SAND_REFILL_EVERY * 10):
            tw.record(g)
        assert tw.sand == SAND_MAX

    def test_reset_forgets_history_keeps_sand(self) -> None:
        tw = TimeRewind(sand=10)
        tw.record(new_game(_pit_level()))
        tw.reset()
        assert tw.history_len == 0
        assert tw.sand == 10


class TestRoomCheckpoint:
    def test_spawn_is_the_first_checkpoint(self) -> None:
        g = new_game(_pit_level())
        cp = RoomCheckpoint()
        cp.reset(g)
        dead = replace(g, kid=replace(g.kid, hp_curr=0, alive=30), status=GameStatus.LOST_DIED)
        back = cp.respawn(dead)
        assert back is not None
        assert back.status is GameStatus.PLAYING
        assert back.kid.alive < 0
        assert back.kid.hp_curr == back.kid.hp_max

    def test_clock_is_not_refunded(self) -> None:
        g = new_game(_pit_level())
        cp = RoomCheckpoint()
        cp.reset(g)
        later = g
        for _ in range(50):
            later = advance(later, Command())
        back = cp.respawn(replace(later, status=GameStatus.LOST_DIED))
        assert back is not None
        assert back.time == later.time

    def test_only_safe_states_become_checkpoints(self) -> None:
        g = new_game(_pit_level())
        assert is_safe_checkpoint(g)
        assert not is_safe_checkpoint(replace(g, kid=replace(g.kid, alive=0)))

    def test_new_room_updates_checkpoint(self) -> None:
        g = new_game(_pit_level())
        cp = RoomCheckpoint()
        cp.reset(g)
        moved = replace(g, kid=replace(g.kid, room=2))
        cp.observe(moved)
        assert cp.room == 2
        assert cp.snapshot is moved
