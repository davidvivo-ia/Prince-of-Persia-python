"""Tests de integración: verifica que el demo bot completa los niveles fáciles.

El bot es naive (no hace backtracking ni administra recursos), así que
los niveles combate-heavy con RNG (03_guard, 07_duo, 10_patrol, 11_spikes,
14_throne) no entran en este conjunto. La lista cubre los 10 niveles
sin obstáculo de "skill humano" donde el bot debería ganar siempre con
seed 42.

Garantiza que cambios futuros en motor / generador / renderer no rompen
la jugabilidad básica.
"""

from __future__ import annotations

import pytest

from pop2026.application.demo_player import run_to_completion
from pop2026.domain.game import GameStatus, new_game
from pop2026.infrastructure.levels import load_builtin
from pop2026.infrastructure.rng import LfsrRng

EASY_LEVELS: tuple[str, ...] = (
    "01_cell",
    "02_sword",
    "04_traps",
    "05_plate",
    "09_maze",
    "11_spikes",
    "13_shadow",
)
"""Niveles que el bot debe ganar con seed=42 en menos de 12_000 ticks.

Tras el rediseño puzzle-based (`puzzles.md`), los demás niveles
implican: recoger sable + combatir (`03`, `07`, `10`, `12`, `14`, `15`),
identificar caída segura entre suelos sueltos (`06`), o un salto
con ventana estrecha tras pinchos (`08`) — todos jugables por
humano pero fuera del alcance de la IA naive del bot.
"""


@pytest.mark.parametrize("slug", EASY_LEVELS)
def test_bot_wins_easy_level(slug: str) -> None:
    """El bot completa cada nivel fácil con seed determinista."""
    lv = load_builtin(slug)
    g = new_game(lv, level_index=1)
    rng = LfsrRng(42)
    final = run_to_completion(g, rng, max_frames=12_000)
    assert final.status is GameStatus.WON, (
        f"bot no ganó {slug}: status={final.status.name} "
        f"x={final.prince.body.pos.x:.1f} hp={final.prince.hp}"
    )
