"""Jugabilidad en modo HUMANO: niveles completos, sin simplificaciones.

A diferencia de ``test_completability`` (topología: guards y chompers
fuera), aquí el bot juega el nivel tal cual lo verá una persona:
guards con su IA canon, chompers con su ciclo, 3 HP reales, y la
espada sólo si la campaña ya la ha conseguido. Si el bot llega a la
exit door con estos verbos (correr, saltar, esperar, luchar), un
humano con teclado también puede.
"""

from __future__ import annotations

import heapq

import pytest

from pop2026canon.application.controller import Command
from pop2026canon.domain.chars import CharId
from pop2026canon.domain.game import Game, GameStatus, new_game
from pop2026canon.domain.level import Level
from pop2026canon.domain.levels_canon import CANON_LEVELS
from pop2026canon.domain.tiles import Tile
from tests.canon.test_completability import (
    _MACROS,
    _NOOP,
    _room_distances_to_goal,
    _run_macro,
    _settle,
)

_STRIKE = Command(strike=True)
_SHIFT = Command(shift=True)
# En guardia y tres estocadas espaciadas — lo que hace un jugador novato.
_FIGHT = [(_SHIFT, 1), (_STRIKE, 1), (_NOOP, 6), (_STRIKE, 1), (_NOOP, 6), (_STRIKE, 1), (_NOOP, 8)]
_HUMAN_MACROS = [*_MACROS, _FIGHT, [(_NOOP, 5)], [(_NOOP, 9)]]


def _key(game: Game) -> tuple:  # type: ignore[type-arg]
    k = game.kid
    room = game.level.room(k.room)
    has_chomper = any((b & 0x1F) == int(Tile.CHOMPER) for b in room.fg)
    phase = game.tick_count % 15 if has_chomper else 0
    guards = tuple(
        (c.room, c.curr_col, c.curr_row, c.hp_curr, c.alive >= 0)
        for c in game.others
        if c.charid is CharId.GUARD
    )
    return (
        k.room,
        k.curr_col,
        k.curr_row,
        k.hp_curr,
        k.has_sword,
        phase,
        game.state.open_gates,
        game.state.fallen_floors,
        guards,
    )


def solve_level_human(level: Level, *, has_sword: bool, max_macros: int = 60000) -> bool:
    """A* en modo humano. ``True`` si el bot cruza la exit door."""
    dist = _room_distances_to_goal(level, Tile.LEVEL_DOOR_LEFT)
    start = _settle(new_game(level, starting_hp=3, has_sword=has_sword))
    if start is None:
        return False
    seen = {_key(start)}
    counter = 0
    heap: list[tuple[int, int, Game]] = [(dist.get(start.kid.room, 99), counter, start)]
    budget = max_macros
    while heap and budget > 0:
        _, _, game = heapq.heappop(heap)
        for macro in _HUMAN_MACROS:
            budget -= 1
            result = _run_macro(game, macro)
            if result is None:
                continue
            if result.status is GameStatus.WON_LEVEL:
                return True
            key = _key(result)
            if key in seen:
                continue
            seen.add(key)
            counter += 1
            heapq.heappush(heap, (dist.get(result.kid.room, 99), counter, result))
    return False


@pytest.mark.parametrize("level", CANON_LEVELS[:13], ids=lambda lv: f"L{lv.number}")
def test_level_is_completable_by_a_human(level: Level) -> None:
    """Con guards, chompers y 3 HP: el nivel se puede terminar."""
    assert solve_level_human(level, has_sword=level.number >= 2), (
        f"L{level.number} ({level.name}): no es completable en modo humano"
    )
