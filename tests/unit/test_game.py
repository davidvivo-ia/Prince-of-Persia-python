"""Tests del agregado Game."""

from __future__ import annotations

from dataclasses import replace

from pop2026.domain.game import Game, GameStatus, advance, new_game
from pop2026.domain.input import InputFrame, PlayerCommand
from pop2026.domain.level import Level
from pop2026.domain.ports import Rng


class FakeRng:
    """RNG determinista de tests, ciclo fijo."""

    def __init__(self, values: list[int]) -> None:
        self._v = values
        self._i = 0

    def next_byte(self) -> int:
        b = self._v[self._i % len(self._v)]
        self._i += 1
        return b & 0xFF

    def coin(self, prob: float) -> bool:
        return self.next_byte() < int(prob * 256)

    def randrange(self, n: int) -> int:
        return self.next_byte() % max(1, n)


def _rng() -> Rng:
    return FakeRng([0, 100, 200, 50])


SIMPLE = """
##############
#..@........>#
##############
"""

WITH_HEAL = """
##############
#..@..+.....>#
##############
"""

WITH_GUARD = """
##############
#..@....g...>#
##############
"""


def _run(g: Game, cmd: PlayerCommand, n: int) -> Game:
    rng = _rng()
    inp = InputFrame(command=cmd)
    for _ in range(n):
        if not g.running:
            break
        g = advance(g, inp, rng)
    return g


class TestGameLoop:
    def test_advance_returns_new_game(self) -> None:
        lv = Level.parse(SIMPLE)
        g = new_game(lv, time_limit=600)
        g2 = advance(g, InputFrame(), _rng())
        assert g2 is not g
        assert g2.time_left == g.time_left - 1

    def test_new_game_uses_level_time_when_set(self) -> None:
        lv = replace(Level.parse(SIMPLE), time_limit_ticks=999)
        g = new_game(lv, time_limit=10_000)
        # El tiempo del nivel manda sobre el argumento.
        assert g.time_left == 999

    def test_new_game_falls_back_to_arg_when_level_time_none(self) -> None:
        lv = Level.parse(SIMPLE)
        assert lv.time_limit_ticks is None
        g = new_game(lv, time_limit=4321)
        assert g.time_left == 4321

    def test_reach_exit_wins(self) -> None:
        lv = Level.parse(SIMPLE)
        g = new_game(lv, time_limit=10_000)
        g2 = _run(g, PlayerCommand.RIGHT, 5_000)
        assert g2.status is GameStatus.WON

    def test_timeout_loses(self) -> None:
        lv = Level.parse(SIMPLE)
        g = new_game(lv, time_limit=5)
        g2 = _run(g, PlayerCommand.NONE, 50)
        assert g2.status is GameStatus.LOST_TIMEOUT

    def test_heal_potion_restores_hp(self) -> None:
        lv = Level.parse(WITH_HEAL)
        g = new_game(lv, time_limit=10_000, starting_hp=3)
        # daño previo
        g = replace(g, prince=g.prince.with_damage(2))
        hp_before = g.prince.hp
        g2 = _run(g, PlayerCommand.RIGHT, 200)
        assert g2.prince.hp >= hp_before

    def test_killing_guard_grants_sword(self) -> None:
        lv = Level.parse(WITH_GUARD)
        g = new_game(lv, time_limit=10_000, starting_hp=10)
        g = replace(g, prince=replace(g.prince, has_sword=True, hp=10, max_hp=10))
        g2 = _run(g, PlayerCommand.RIGHT, 4_000)
        assert g2.prince.has_sword
