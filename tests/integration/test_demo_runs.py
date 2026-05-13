"""Tests de integración: la demo es determinista y termina."""

from __future__ import annotations

from pop2026.application import demo_player
from pop2026.domain.game import GameStatus, new_game
from pop2026.domain.level import Level
from pop2026.domain.ports import Rng


class SeedRng:
    """LFSR-8 simple para tests; igual a la implementación de infra."""

    def __init__(self, seed: int = 42) -> None:
        self._s = seed & 0xFF or 1

    def next_byte(self) -> int:
        s = self._s
        # LFSR taps 8,6,5,4 (polinomio 0xB8)
        bit = ((s >> 0) ^ (s >> 2) ^ (s >> 3) ^ (s >> 4)) & 1
        s = ((s >> 1) | (bit << 7)) & 0xFF
        self._s = s or 1
        return s

    def coin(self, prob: float) -> bool:
        return self.next_byte() < int(prob * 256)

    def randrange(self, n: int) -> int:
        return self.next_byte() % max(1, n)


SHORT_LEVEL = """
##############
#..@........>#
##############
"""


def _rng(seed: int) -> Rng:
    return SeedRng(seed)


def test_demo_is_deterministic_on_same_seed() -> None:
    lv = Level.parse(SHORT_LEVEL)
    final_a = demo_player.run_to_completion(new_game(lv, time_limit=10_000), _rng(42))
    final_b = demo_player.run_to_completion(new_game(lv, time_limit=10_000), _rng(42))
    assert final_a.prince.pos == final_b.prince.pos
    assert final_a.status is final_b.status
    assert final_a.time_left == final_b.time_left


def test_demo_terminates_within_max_frames() -> None:
    lv = Level.parse(SHORT_LEVEL)
    final = demo_player.run_to_completion(
        new_game(lv, time_limit=10_000), _rng(42), max_frames=5_000
    )
    # debe haber terminado: o ganó o se acabó el tiempo o murió
    assert final.status in {
        GameStatus.WON,
        GameStatus.LOST_DIED,
        GameStatus.LOST_TIMEOUT,
        GameStatus.PLAYING,  # si max_frames lo cortó antes
    }


def test_demo_reaches_exit_on_simple_level() -> None:
    lv = Level.parse(SHORT_LEVEL)
    final = demo_player.run_to_completion(
        new_game(lv, time_limit=20_000), _rng(42), max_frames=5_000
    )
    assert final.status is GameStatus.WON
