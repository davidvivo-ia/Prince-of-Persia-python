"""Tests de integración: demo bot pasa una muestra de niveles 1..100.

El bot no tiene que ganar todos: los niveles narrativos de combate
intenso (3, 7, 10) y boss (12) son retos humanos. El test garantiza
que **no se atasca** (status sale de PLAYING en frames razonables).
"""

from __future__ import annotations

import pytest

from pop2026.application import demo_player
from pop2026.application.level_source import load_level
from pop2026.domain.game import GameStatus, new_game
from pop2026.infrastructure.rng import LfsrRng

# Muestra representativa: primero de cada acto, mitad y último.
SAMPLE_LEVELS: tuple[int, ...] = (1, 13, 26, 38, 51, 63, 76, 88, 99)


@pytest.mark.parametrize("level_index", SAMPLE_LEVELS)
def test_demo_does_not_get_stuck(level_index: int) -> None:
    """El bot debe terminar (WON o LOST_DIED) en 8 000 frames."""
    level = load_level(level_index, seed=42)
    game = new_game(level, level_index=level_index, time_limit=8000)
    rng = LfsrRng(42)
    final = demo_player.run_to_completion(game, rng, max_frames=8000)
    assert final.status is not GameStatus.PLAYING, (
        f"L{level_index}: el bot no terminó en 8000 frames"
    )


def test_demo_first_act_is_winnable() -> None:
    """El primer nivel siempre lo gana el bot (sanity)."""
    level = load_level(1, seed=42)
    game = new_game(level, level_index=1, time_limit=10_000)
    final = demo_player.run_to_completion(game, LfsrRng(42), max_frames=5000)
    assert final.status is GameStatus.WON
