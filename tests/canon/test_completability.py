"""Completabilidad end-to-end: un bot juega cada nivel con el motor REAL.

BFS sobre macro-acciones (andar, correr, saltar, esperar) ejecutadas
tick a tick con ``advance()``. Si el bot alcanza la exit door, el nivel
es completable de verdad: la física, los saltos, los drops, las plates
y las gates funcionan encadenados.

Simplificaciones (topología, no timing):
- guards fuera (el combate se prueba en test_gameplay),
- chompers neutralizados (pasar es cuestión de timing, no de ruta).

Todo lo demás es el juego real: gravedad, daño por caída, colisiones,
loose floors que caen, gates que abren con plate y cierran solas.
"""

from __future__ import annotations

from collections import deque
from dataclasses import replace

import pytest

from pop2026canon.application.controller import Command
from pop2026canon.application.tick import advance
from pop2026canon.domain.actions import Action
from pop2026canon.domain.game import Game, GameStatus, new_game
from pop2026canon.domain.level import Level
from pop2026canon.domain.levels_canon import CANON_LEVELS
from pop2026canon.domain.room import Room
from pop2026canon.domain.tiles import Tile, encode_tile

_NOOP = Command()
_MAX_SETTLE = 90
_MAX_MACRO_HOLD = 60


def _strip_hazards(level: Level) -> Level:
    """Quita guards y neutraliza chompers (timing, no topología)."""
    new_rooms = []
    for room in level.rooms:
        fg = list(room.fg)
        for i, byte in enumerate(fg):
            if (byte & 0x1F) == int(Tile.CHOMPER):
                fg[i] = encode_tile(Tile.EMPTY, 0)
        new_rooms.append(
            Room(
                id=room.id,
                fg=tuple(fg),
                bg=room.bg,
                link_n=room.link_n,
                link_s=room.link_s,
                link_e=room.link_e,
                link_w=room.link_w,
                guards=(),
            )
        )
    return replace(level, rooms=tuple(new_rooms))


def _settle(game: Game) -> Game | None:
    """Suelta las teclas hasta estado estable (STAND) o terminal."""
    for _ in range(_MAX_SETTLE):
        if game.status is GameStatus.WON_LEVEL:
            return game
        if game.kid.alive >= 0 or not game.running:
            return None
        if game.kid.action is Action.STAND:
            return game
        game = advance(game, _NOOP)
    return None


def _run_macro(game: Game, holds: list[tuple[Command, int]]) -> Game | None:
    """Ejecuta una secuencia de (comando, ticks) y asienta al final."""
    for cmd, ticks in holds:
        for _ in range(ticks):
            game = advance(game, cmd)
            if game.status is GameStatus.WON_LEVEL:
                return game
            if game.kid.alive >= 0 or not game.running:
                return None
    return _settle(game)


_R = Command(right=True)
_L = Command(left=True)
_RU = Command(right=True, up=True)
_LU = Command(left=True, up=True)
_U = Command(up=True)
_US = Command(up=True, shift=True)
_S = Command(shift=True)

_MACROS: list[list[tuple[Command, int]]] = [
    [(_R, 4)],  # paso corto derecha
    [(_L, 4)],  # paso corto izquierda
    [(_R, 10)],  # carrera derecha
    [(_L, 10)],  # carrera izquierda
    [(_R, 7), (_RU, 3), (_R, 14)],  # run-jump derecha
    [(_L, 7), (_LU, 3), (_L, 14)],  # run-jump izquierda
    [(_R, 2), (_RU, 3), (_R, 12)],  # salto corto derecha
    [(_L, 2), (_LU, 3), (_L, 12)],  # salto corto izquierda
    [(_US, 8), (_S, 8), (_U, 20)],  # salto vertical + grab + climb
    [(_NOOP, 16)],  # esperar (loose floors, gates)
]


def _state_key(game: Game) -> tuple:  # type: ignore[type-arg]
    k = game.kid
    return (k.room, k.curr_col, k.curr_row, game.state.open_gates, game.state.fallen_floors)


def _room_distances_to_goal(level: Level, goal_tile: Tile) -> dict[int, int]:
    """Distancia (en salas) de cada sala a la sala objetivo."""
    goal_rooms = {rm.id for rm in level.rooms for byte in rm.fg if (byte & 0x1F) == int(goal_tile)}
    dist = dict.fromkeys(goal_rooms, 0)
    frontier = deque(goal_rooms)
    while frontier:
        rid = frontier.popleft()
        for other in level.rooms:
            for link in (other.link_n, other.link_s, other.link_e, other.link_w):
                if link == rid and other.id not in dist:
                    dist[other.id] = dist[rid] + 1
                    frontier.append(other.id)
    return dist


def solve_level(level: Level, *, max_macros: int = 30000) -> bool:
    """A* de macro-acciones. ``True`` si el bot cruza la exit door.

    La heurística es la distancia de salas hasta la sala del exit —
    dirige la búsqueda sin sacrificar corrección (cada estado guardado
    es un ``Game`` real alcanzado tick a tick).
    """
    import heapq

    stripped = _strip_hazards(level)
    dist = _room_distances_to_goal(stripped, Tile.LEVEL_DOOR_LEFT)
    start = new_game(stripped, starting_hp=10)
    settled = _settle(start)
    if settled is None:
        return False

    def _priority(game: Game) -> int:
        return dist.get(game.kid.room, 99)

    seen: set[tuple] = {_state_key(settled)}  # type: ignore[type-arg]
    counter = 0
    heap: list[tuple[int, int, Game]] = [(_priority(settled), counter, settled)]
    budget = max_macros
    while heap and budget > 0:
        _, _, game = heapq.heappop(heap)
        for macro in _MACROS:
            budget -= 1
            result = _run_macro(game, macro)
            if result is None:
                continue
            if result.status is GameStatus.WON_LEVEL:
                return True
            key = _state_key(result)
            if key in seen:
                continue
            seen.add(key)
            counter += 1
            heapq.heappush(heap, (_priority(result), counter, result))
    return False


@pytest.mark.parametrize("level", CANON_LEVELS[:13], ids=lambda lv: f"L{lv.number}")
def test_level_is_completable_in_engine(level: Level) -> None:
    """El bot llega de spawn a exit door jugando ticks reales."""
    assert solve_level(level), (
        f"L{level.number} ({level.name}): el bot no encontró ruta real hasta la exit door"
    )


def test_l14_princess_reachable_in_engine() -> None:
    """L14: el bot alcanza a la princesa (WON_GAME) con ticks reales."""
    level = _strip_hazards(CANON_LEVELS[13])
    start = _settle(new_game(level, starting_hp=10))
    assert start is not None
    seen = {_state_key(start)}
    queue: deque[Game] = deque([start])
    budget = 3000
    while queue and budget > 0:
        game = queue.popleft()
        for macro in _MACROS:
            budget -= 1
            result = None
            g = game
            won = False
            for cmd, ticks in macro:
                for _ in range(ticks):
                    g = advance(g, cmd)
                    if g.status is GameStatus.WON_GAME:
                        won = True
                        break
                if won:
                    break
            if won:
                return
            if g.kid.alive < 0 and g.running:
                result = _settle(g)
            if result is None:
                continue
            if result.status is GameStatus.WON_GAME:
                return
            key = _state_key(result)
            if key not in seen:
                seen.add(key)
                queue.append(result)
    pytest.fail("L14: el bot no alcanzó a la princesa")
