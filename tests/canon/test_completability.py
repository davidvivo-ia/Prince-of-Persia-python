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
from collections.abc import Callable
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
                fg[i] = encode_tile(Tile.FLOOR, 0)  # geometría canon: es suelo
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
_S = Command(shift=True)
_D = Command(down=True)
_RS = Command(right=True, shift=True)
_LS = Command(left=True, shift=True)

_MACROS: list[list[tuple[Command, int]]] = [
    [(_R, 4)],  # paso corto derecha
    [(_L, 4)],  # paso corto izquierda
    [(_R, 10)],  # carrera derecha
    [(_L, 10)],  # carrera izquierda
    [(_R, 7), (_RU, 3), (_R, 14)],  # run-jump derecha
    [(_L, 7), (_LU, 3), (_L, 14)],  # run-jump izquierda
    [(_R, 22)],  # carrera larga (las gates se cierran: hay que correr)
    [(_L, 22)],
    [(_R, 7), (_RU, 3), (_R, 24)],  # run-jump y seguir corriendo
    [(_L, 7), (_LU, 3), (_L, 24)],
    # Run-jump + SHIFT: si el salto se queda corto, las manos agarran la
    # cornisa de enfrente (canon: libra 4 celdas colgándose); ↑ trepa.
    [(_R, 7), (_RU, 3), (_RS, 16), (_U, 1), (_S, 18)],
    [(_L, 7), (_LU, 3), (_LS, 16), (_U, 1), (_S, 18)],
    [(_R, 2), (_RU, 3), (_R, 12)],  # salto corto derecha
    [(_L, 2), (_LU, 3), (_L, 12)],  # salto corto izquierda
    # Salto largo desde parado (↑+dir): libra 2 celdas sin carrerilla —
    # imprescindible en plataformas de una celda. Si el kid mira al otro
    # lado, sólo se gira (el salto no arranca durante el TURN).
    [(_RU, 2), (_NOOP, 14)],
    [(_LU, 2), (_NOOP, 14)],
    # ↑: agarra la cornisa (si hay), SHIFT mantiene el agarre mientras
    # dura la animación, ↑ trepa. Sin cornisa es un salto vertical.
    [(_U, 1), (_S, 7), (_U, 1), (_S, 16)],
    [(_D, 1), (_NOOP, 14)],  # ↓ de espaldas al borde: descolgarse y soltarse
    [(_D, 1), (_NOOP, 10), (_S, 12)],  # bajar un pozo: soltarse y agarrar la siguiente
    [(_NOOP, 16)],  # esperar (loose floors, gates)
]


def _state_key(game: Game) -> tuple:  # type: ignore[type-arg]
    k = game.kid
    # La dirección importa: los verbos de cornisa (↑ de espaldas al pozo,
    # ↓ de espaldas al borde) dependen de hacia dónde mira el kid.
    # Las gates abiertas se cierran solas (canon ~18 s): el tiempo que
    # les queda forma parte del estado, en tramos gruesos, para que una
    # ruta lenta no "gaste" el estado que una ruta rápida necesita.
    gates = tuple(
        sorted((coord, game.state.state_at(coord) // 24) for coord in game.state.open_gates)
    )
    return (
        k.room,
        k.curr_col,
        k.curr_row,
        k.direction,
        gates,
        game.state.fallen_floors,
    )


def _room_distances_to_goal(level: Level, goal_tile: Tile) -> dict[int, int]:
    """Distancia (en salas) de cada sala a la sala objetivo."""
    goal_rooms = {rm.id for rm in level.rooms for byte in rm.fg if (byte & 0x1F) == int(goal_tile)}
    # Niveles originales: la puerta de la sala de spawn es la ENTRADA, no
    # un objetivo (si hay otra puerta en otra sala).
    if len(goal_rooms) > 1:
        goal_rooms.discard(level.start_room)
    return _room_distances_to_goal_rooms(level, goal_rooms)


def _room_distances_to_goal_rooms(level: Level, goal_rooms: set[int]) -> dict[int, int]:
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


ROOM_COST_TICKS = 120
"""Peso de la heurística: una sala de distancia "vale" ~120 ticks."""


def _exit_goal(level: Level) -> tuple[tuple[int, int, int] | None, tuple[int, int, int] | None]:
    """``(exit_coord, plate_coord)``: la exit door (de otra sala que la de
    spawn si hay varias) y la plate que la abre, si tiene doorlink."""
    exits = [
        (rm.id, i % 10, i // 10)
        for rm in level.rooms
        for i, b in enumerate(rm.fg)
        if (b & 0x1F) == int(Tile.LEVEL_DOOR_LEFT)
    ]
    if len(exits) > 1:
        exits = [e for e in exits if e[0] != level.start_room] or exits
    if not exits:
        return None, None
    exit_coord = exits[0]
    plates = level.plates_for_gate(exit_coord)
    return exit_coord, (plates[0] if plates else None)


def make_priority(level: Level, dist: dict[int, int]) -> Callable[[Game], int]:
    """f = ticks + heurística. Mientras la exit door esté cerrada y tenga
    plate, el objetivo es la plate (su sala y su FILA: en la sala
    objetivo, estar en otra fila cuesta media sala); abierta, la puerta."""
    exit_coord, plate_coord = _exit_goal(level)
    plate_dist = _room_distances_to_goal_rooms(level, {plate_coord[0]}) if plate_coord else {}

    def _f(game: Game) -> int:
        k = game.kid
        door_open = exit_coord is None or exit_coord in game.state.open_gates
        if door_open or plate_coord is None:
            goal_room, goal_row, d = (
                (exit_coord[0], exit_coord[2], dist) if exit_coord else (None, None, dist)
            )
        else:
            goal_room, goal_row, d = plate_coord[0], plate_coord[2], plate_dist
        h = ROOM_COST_TICKS * d.get(k.room, 99)
        if goal_room is not None and k.room == goal_room and k.curr_row != goal_row:
            h += ROOM_COST_TICKS // 2
        return game.tick_count + h

    return _f


def _search(
    start: Game,
    *,
    priority: Callable[[Game], int],
    goal: Callable[[Game], bool],
    budget: int,
) -> tuple[Game | None, int]:
    """A* de macro-acciones desde ``start`` hasta un estado que cumpla
    ``goal``. Devuelve ``(estado, presupuesto restante)``.

    f = ticks transcurridos + heurística. El tiempo cuenta de verdad: las
    gates se cierran solas (~18 s canon), así que entre dos formas de
    llegar a la misma celda se expande antes la más rápida, y un estado
    ya visto sólo se descarta si no mejora el tiempo con que se alcanzó
    (dedup al sacar de la cola, no al meter)."""
    import heapq

    best: dict[tuple, int] = {_state_key(start): start.tick_count}  # type: ignore[type-arg]
    counter = 0
    heap: list[tuple[int, int, Game]] = [(priority(start), counter, start)]
    while heap and budget > 0:
        _, _, game = heapq.heappop(heap)
        if game.tick_count > best.get(_state_key(game), game.tick_count):
            continue  # ya se sacó una versión más rápida de este estado
        for macro in _MACROS:
            budget -= 1
            result = _run_macro(game, macro)
            if result is None:
                continue
            if goal(result):
                return result, budget
            key = _state_key(result)
            if result.tick_count >= best.get(key, 10**9):
                continue
            best[key] = result.tick_count
            counter += 1
            heapq.heappush(heap, (priority(result), counter, result))
    return None, budget


def solve_level(level: Level, *, max_macros: int = 30000) -> bool:
    """``True`` si el bot cruza la exit door jugando ticks reales.

    Dos fases cuando la exit door tiene plate: primero llegar a abrirla
    (objetivo: la plate), después, desde ese estado, llegar a la puerta.
    Así el recorrido de vuelta no compite con todo lo explorado antes.
    """
    stripped = _strip_hazards(level)
    dist = _room_distances_to_goal(stripped, Tile.LEVEL_DOOR_LEFT)
    settled = _settle(new_game(stripped, starting_hp=10))
    if settled is None:
        return False
    priority = make_priority(stripped, dist)
    exit_coord, plate_coord = _exit_goal(stripped)

    def _won(game: Game) -> bool:
        return game.status is GameStatus.WON_LEVEL

    budget = max_macros
    if exit_coord is not None and plate_coord is not None:

        def _door_open(game: Game) -> bool:
            return _won(game) or exit_coord in game.state.open_gates

        opened, budget = _search(settled, priority=priority, goal=_door_open, budget=budget)
        if opened is None:
            return False
        if _won(opened):
            return True
        settled = opened
    final, _ = _search(settled, priority=priority, goal=_won, budget=budget)
    return final is not None


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
