"""Smoke test cross-level: cada uno de los 14 niveles avanza N ticks
sin crashear."""

from __future__ import annotations

import pytest

from pop2026canon.application.controller import Command
from pop2026canon.application.tick import advance
from pop2026canon.domain.game import new_game
from pop2026canon.domain.levels_canon import CANON_LEVELS


@pytest.mark.parametrize("level", CANON_LEVELS)
def test_level_advances_100_ticks(level) -> None:  # type: ignore[no-untyped-def]
    """Cada nivel avanza 100 ticks sin excepciones."""
    game = new_game(level)
    for _ in range(100):
        game = advance(game, Command(right=True))
    # No crashes — el game puede haber acabado en cualquier estado válido
    assert game.tick_count >= 1
