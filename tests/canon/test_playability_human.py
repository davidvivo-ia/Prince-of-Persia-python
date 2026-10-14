"""Jugabilidad en modo HUMANO: niveles completos, sin simplificaciones.

A diferencia de ``test_completability`` (topología: guards y chompers
fuera), aquí el nivel se juega tal cual lo verá una persona: guards con
su IA canon, chompers con su ciclo, HP medio de campaña, y la espada
sólo si la campaña ya la ha conseguido.

Funciona con **replays dorados** (como SDLPoP): el solver A* encuentra
una vez la secuencia de teclas que gana el nivel y la guarda en
``tests/canon/replays/L<n>.txt``; el test la reproduce tick a tick con
``advance()`` y exige WON_LEVEL. Es rápido (segundos) y honesto (son
ticks reales del motor). Si un cambio de gameplay rompe un replay:

    POP_REGEN_REPLAYS=1 pytest tests/canon/test_playability_human.py -k L7

vuelve a resolver ese nivel y reescribe el replay. Un replay que no
puede regenerarse significa que el nivel YA NO es completable por un
humano — eso es el bug.
"""

from __future__ import annotations

import heapq
import os
from collections.abc import Callable
from pathlib import Path

import pytest

from pop2026canon.application.controller import Command
from pop2026canon.application.tick import advance
from pop2026canon.domain.actions import Action, Seq, SwordStatus
from pop2026canon.domain.chars import Char, CharId
from pop2026canon.domain.combat import PARRY_FRAMES, READY_FRAMES, char_opp_dist, is_hostile
from pop2026canon.domain.game import Game, GameStatus, new_game
from pop2026canon.domain.level import Level
from pop2026canon.domain.levels_canon import CANON_LEVELS
from pop2026canon.domain.tiles import Tile
from tests.canon.routes import OPEN_EXIT, ROUTE_HINTS
from tests.canon.test_completability import (
    _MACROS,
    _NOOP,
    ROOM_COST_TICKS,
    _exit_goal,
    _link_gates,
    _priority_to_room,
    _room_distances_to_goal,
    _room_distances_to_goal_rooms,
    _settle,
    make_priority,
)

REPLAY_DIR = Path(__file__).parent / "replays"

_STRIKE = Command(strike=True)
_SHIFT = Command(shift=True)
_UP = Command(up=True)
_R = Command(right=True)
_L = Command(left=True)
_RU = Command(right=True, up=True)
_LU = Command(left=True, up=True)
# En guardia y tres estocadas espaciadas — lo que hace un jugador novato.
_FIGHT = [(_SHIFT, 1), (_STRIKE, 1), (_NOOP, 6), (_STRIKE, 1), (_NOOP, 6), (_STRIKE, 1), (_NOOP, 8)]
# Parada (ARRIBA en guardia) y contraataque — lo que aprende cualquier
# jugador de POP en el segundo nivel.
_PARRY = [
    (_SHIFT, 1),
    (_UP, 1),
    (_NOOP, 2),
    (_STRIKE, 1),
    (_NOOP, 4),
    (_UP, 1),
    (_NOOP, 2),
    (_STRIKE, 1),
    (_NOOP, 4),
]
# Carrera larga: cruzar un pasillo de chompers sin frenar dentro de uno.


def campaign_hp(level_number: int) -> int:
    """HP con el que un jugador medio llega al nivel: 3 de base más una
    poción grande cada dos niveles (tope canon 10)."""
    return min(10, 3 + level_number // 2)


# ---------------------------------------------------------------------------
# Codificación de replays: un carácter por tick (L R U D S A y '.' = nada)
# ---------------------------------------------------------------------------

_FLAGS = (
    ("left", "L"),
    ("right", "R"),
    ("up", "U"),
    ("down", "D"),
    ("shift", "S"),
    ("strike", "A"),
)


def encode_commands(cmds: list[Command]) -> str:
    out = []
    for c in cmds:
        token = "".join(ch for attr, ch in _FLAGS if getattr(c, attr))
        out.append(token or ".")
    return " ".join(out)


def decode_commands(text: str) -> list[Command]:
    cmds = []
    for token in text.split():
        if token == ".":
            cmds.append(_NOOP)
            continue
        cmds.append(Command(**{attr: ch in token for attr, ch in _FLAGS}))
    return cmds


# ---------------------------------------------------------------------------
# Solver A* que devuelve la traza ganadora
# ---------------------------------------------------------------------------


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
    in_combat = any(
        c.charid is CharId.GUARD and c.room == k.room and c.alive < 0 for c in game.others
    )
    combat: tuple = ()  # type: ignore[type-arg]
    if in_combat:
        # En combate la posición en píxeles decide si la hoja alcanza
        # (canon: 12..28 px), así que forma parte del estado.
        guard_micro = [
            (c.x, c.frame, c.refrac)
            for c in game.others
            if c.charid is CharId.GUARD and c.room == k.room
        ]
        combat = (*guard_micro, k.x, k.frame, game.tick_count % 16)
    return (
        k.room,
        k.curr_col,
        k.curr_row,
        k.direction,
        k.hp_curr,
        k.has_sword,
        phase,
        tuple(sorted((coord, game.state.state_at(coord) // 24) for coord in game.state.open_gates)),
        game.state.fallen_floors,
        guards,
        combat,
    )


Policy = Callable[[Game], Command | None]
"""Macro reactiva: decide el comando tick a tick (``None`` = terminar)."""


def _nearest_enemy(game: Game) -> Char | None:
    k = game.kid
    best = None
    for c in game.others:
        if not is_hostile(c) or c.alive >= 0 or c.room != k.room or c.curr_row != k.curr_row:
            continue
        if best is None or abs(char_opp_dist(k, c)) < abs(char_opp_dist(k, best)):
            best = c
    return best


_PARRY_AT: tuple[int, ...] = (152, 153)
"""Frames de la estocada rival en los que se pulsa ARRIBA para parar."""


def _duel_policy(game: Game) -> Command | None:
    """Lo que hace un jugador en un duelo: para cuando el guard lanza la
    estocada (frames 152/153), pincha cuando está a distancia de hoja
    (12..28 px) y en guardia, se acerca si está lejos y retrocede si lo
    tiene encima. Termina cuando no queda rival en la fila."""
    k = game.kid
    enemy = _nearest_enemy(game)
    if enemy is None:
        return None
    if k.sword != SwordStatus.DRAWN:
        return Command(up=True, shift=True)  # desenvainar al verle
    if k.curr_seq_id == int(Seq.STAND):
        return _SHIFT  # en guardia ANTES de que llegue: si no, su primera
        # estocada te alcanza de pie (y en el borde de la sala te empuja a
        # la anterior, donde el duelo se enreda)
    d = char_opp_dist(k, enemy)
    # Acaba de parar: réplica inmediata (canon blocktostrike) — es la
    # única forma de alcanzar a un rival que bloquea siempre (el visir).
    if k.frame in PARRY_FRAMES and 8 <= d < 29:
        return _STRIKE
    if k.curr_seq_id != int(Seq.ENGARDE) or k.frame not in READY_FRAMES:
        return _NOOP
    if enemy.frame in _PARRY_AT:
        return _UP
    if enemy.frame in (168, 151, 152, 153):
        return _NOOP
    if d < 0:
        return _L if k.direction == 0 else _R  # el rival a la espalda: girarse
    forward = _R if k.direction == 0 else _L
    backward = _L if k.direction == 0 else _R
    if 12 <= d < 29:
        return _STRIKE
    if d >= 29:
        return forward
    return backward


_DUEL: list[tuple[Policy, int]] = [(_duel_policy, 48)]
_DUEL_FULL: list[tuple[Policy, int]] = [(_duel_policy, 600)]
"""El duelo entero de una vez (la política termina sola cuando no queda
rival): un jugador no deja un combate a medias para dar un paso, y así
la búsqueda no se pierde entre miles de posturas intermedias."""

_COMBAT_MACROS: list[list[tuple[Command | Policy, int]]] = [
    _DUEL_FULL,
    [(_R, 22)],
    [(_L, 22)],
    [(_R, 7), (_RU, 3), (_R, 14)],
    [(_L, 7), (_LU, 3), (_L, 14)],
]
"""Con un enemigo armado a la vista: batirse hasta el final, o huir
(correr, saltar, pasar de largo — imprescindible ante el esqueleto, que
no muere). Sin pasitos ni esperas: con el rival encima cada postura es
un estado distinto y la búsqueda se perdería entre miles de ellas."""


def _in_combat(game: Game) -> bool:
    enemy = _nearest_enemy(game)
    return enemy is not None and abs(char_opp_dist(game.kid, enemy)) < 90


HP_COST_TICKS = 150
"""Un punto de vida perdido "cuesta" como 150 ticks de camino: el bot
prefiere la ruta que llega entero (un kid a 1 HP muere de cualquier
estocada)."""


def _with_hp_cost(priority: Callable[[Game], int]) -> Callable[[Game], int]:
    def _f(game: Game) -> int:
        return priority(game) + HP_COST_TICKS * (game.kid.hp_max - game.kid.hp_curr)

    return _f


_HUMAN_MACROS: list[list[tuple[Command | Policy, int]]] = [
    *_MACROS,
    _DUEL_FULL,
    _DUEL,
    [(_R, 22)],
    [(_L, 22)],
    _FIGHT,
    _PARRY,
    [(_NOOP, 5)],
    [(_NOOP, 9)],
]


def _run_macro_trace(
    game: Game, holds: list[tuple[Command | Policy, int]]
) -> tuple[Game | None, list[Command]]:
    """Como ``_run_macro`` pero devuelve también los comandos emitidos.
    Un elemento puede ser una política (callable) que decide cada tick."""
    cmds: list[Command] = []
    for item, ticks in holds:
        for _ in range(ticks):
            if callable(item):
                decided = item(game)
                if decided is None:
                    break
                cmd = decided
            else:
                cmd = item
            game = advance(game, cmd)
            cmds.append(cmd)
            if game.status is GameStatus.WON_LEVEL:
                return game, cmds
            if game.kid.alive >= 0 or not game.running:
                return None, cmds
    for _ in range(90):
        if game.status is GameStatus.WON_LEVEL:
            return game, cmds
        if game.kid.alive >= 0 or not game.running:
            return None, cmds
        if game.kid.action is Action.STAND:
            return game, cmds
        game = advance(game, _NOOP)
        cmds.append(_NOOP)
    return None, cmds


def _search_trace(
    start: Game,
    start_trace: list[Command],
    *,
    priority: Callable[[Game], int],
    goal: Callable[[Game], bool],
    budget: int,
) -> tuple[Game | None, list[Command], int]:
    """A* con traza (como ``_search`` de topología, con macros humanas y
    cuota por sala). Devuelve ``(estado, comandos, presupuesto)``."""
    best: dict[tuple, int] = {_key(start): start.tick_count}  # type: ignore[type-arg]
    counter = 0
    heap: list[tuple[int, int, Game, list[Command]]] = [
        (priority(start), counter, start, start_trace)
    ]
    # Cuota por sala: una sala cercana al exit pero sin salida (un duelo
    # que se pierde de mil formas) no puede devorar todo el presupuesto.
    room_quota = max(3000, budget // 6)
    room_spent: dict[int, int] = {}
    while heap and budget > 0:
        prio, _, game, trace = heapq.heappop(heap)
        if game.tick_count > best.get(_key(game), game.tick_count):
            continue
        room = game.kid.room
        if room_spent.get(room, 0) > room_quota and prio < 10**6:
            counter += 1
            heapq.heappush(heap, (prio + 10**6, counter, game, trace))
            continue
        for macro in _COMBAT_MACROS if _in_combat(game) else _HUMAN_MACROS:
            room_spent[room] = room_spent.get(room, 0) + 1
            budget -= 1
            result, cmds = _run_macro_trace(game, macro)
            if result is None:
                continue
            if goal(result):
                return result, trace + cmds, budget
            key = _key(result)
            if result.tick_count >= best.get(key, 10**9):
                continue
            best[key] = result.tick_count
            counter += 1
            heapq.heappush(heap, (priority(result), counter, result, trace + cmds))
    return None, [], budget


def _sword_coord(level: Level) -> tuple[int, int, int] | None:
    for rm in level.rooms:
        for i, b in enumerate(rm.fg):
            if (b & 0x1F) == int(Tile.SWORD):
                return rm.id, i % 10, i // 10
    return None


def _priority_to_cell(level: Level, cell: tuple[int, int, int]) -> Callable[[Game], int]:
    """f = ticks + distancia (consciente de gates) a la sala de ``cell``,
    con media sala extra si se está en esa sala pero en otra fila."""
    link_gates = _link_gates(level)
    cache: dict[frozenset[tuple[int, int, int]], dict[int, int]] = {}

    def _f(game: Game) -> int:
        gates = frozenset(game.state.open_gates)
        d = cache.get(gates)
        if d is None:
            d = _room_distances_to_goal_rooms(level, {cell[0]}, gates, link_gates)
            cache[gates] = d
        k = game.kid
        h = ROOM_COST_TICKS * d.get(k.room, 30)
        if k.room == cell[0] and k.curr_row != cell[2]:
            h += ROOM_COST_TICKS // 2
        return game.tick_count + h

    return _f


def solve_level_human_trace(
    level: Level, *, has_sword: bool, max_macros: int = 60000
) -> list[Command] | None:
    """A* en modo humano (dos fases: abrir la exit door, llegar a ella).
    Devuelve la secuencia de comandos ganadora."""
    dist = _room_distances_to_goal(level, Tile.LEVEL_DOOR_LEFT)
    start = _settle(new_game(level, starting_hp=campaign_hp(level.number), has_sword=has_sword))
    if start is None:
        return None
    priority = _with_hp_cost(make_priority(level, dist))
    exit_coord, plate_coord = _exit_goal(level)

    def _won(game: Game) -> bool:
        return game.status is GameStatus.WON_LEVEL

    budget = max_macros
    trace: list[Command] = []
    # Fase 0: sin espada no se pasa a un guard — si el nivel tiene una,
    # primero ir a por ella (L1 original: la espada está al otro lado del
    # nivel respecto al guard y la salida).
    sword = _sword_coord(level)
    if not has_sword and sword is not None:
        sword_priority = _with_hp_cost(_priority_to_cell(level, sword))

        def _armed(game: Game) -> bool:
            return _won(game) or game.kid.has_sword

        armed, trace, budget = _search_trace(
            start, [], priority=sword_priority, goal=_armed, budget=budget
        )
        if armed is None:
            return None
        if _won(armed):
            return trace
        start = armed
    door_done = exit_coord is None or plate_coord is None

    def _door_open(game: Game) -> bool:
        return _won(game) or exit_coord in game.state.open_gates

    def _open_door(
        start: Game, trace: list[Command], budget: int
    ) -> tuple[Game | None, list[Command], int]:
        return _search_trace(start, trace, priority=priority, goal=_door_open, budget=budget)

    for room in ROUTE_HINTS.get(level.number, ()):
        if room == OPEN_EXIT:
            if door_done:
                continue
            opened, trace, budget = _open_door(start, trace, budget)
            if opened is None:
                return None
            if _won(opened):
                return trace
            start, door_done = opened, True
            continue

        def _reached(game: Game, room: int = room) -> bool:
            return _won(game) or game.kid.room == room

        reached, trace, budget = _search_trace(
            start,
            trace,
            priority=_with_hp_cost(_priority_to_room(level, room)),
            goal=_reached,
            budget=budget,
        )
        if reached is None:
            return None
        if _won(reached):
            return trace
        start = reached
    if not door_done:
        opened, trace, budget = _open_door(start, trace, budget)
        if opened is None:
            return None
        if _won(opened):
            return trace
        start = opened
    final, trace, _ = _search_trace(start, trace, priority=priority, goal=_won, budget=budget)
    return trace if final is not None else None


def solve_level_human(level: Level, *, has_sword: bool, max_macros: int = 60000) -> bool:
    """``True`` si el bot humano gana el nivel."""
    return solve_level_human_trace(level, has_sword=has_sword, max_macros=max_macros) is not None


# ---------------------------------------------------------------------------
# Replay
# ---------------------------------------------------------------------------


def replay_wins(level: Level, cmds: list[Command], *, has_sword: bool) -> bool:
    """Reproduce la traza con el motor real y dice si cruza la exit door."""
    game = new_game(level, starting_hp=campaign_hp(level.number), has_sword=has_sword)
    for cmd in cmds:
        game = advance(game, cmd)
        if game.status is GameStatus.WON_LEVEL:
            return True
        if not game.running:
            return False
    # margen: suelta las teclas por si la victoria llega al asentarse
    for _ in range(30):
        game = advance(game, _NOOP)
        if game.status is GameStatus.WON_LEVEL:
            return True
        if not game.running:
            return False
    return False


def _replay_path(level: Level) -> Path:
    return REPLAY_DIR / f"L{level.number}.txt"


@pytest.mark.parametrize("level", CANON_LEVELS[:13], ids=lambda lv: f"L{lv.number}")
def test_level_is_completable_by_a_human(level: Level) -> None:
    """Con guards, chompers y el HP medio de campaña: el nivel se puede
    terminar. Reproduce el replay dorado; si no existe o se pide
    regenerar, lo resuelve el bot y lo guarda."""
    has_sword = level.number >= 2
    path = _replay_path(level)
    regen = os.environ.get("POP_REGEN_REPLAYS") == "1"
    if path.exists() and not regen:
        cmds = decode_commands(path.read_text(encoding="utf-8"))
        assert replay_wins(level, cmds, has_sword=has_sword), (
            f"L{level.number} ({level.name}): el replay dorado ya no gana — el gameplay "
            f"cambió. Regenera con POP_REGEN_REPLAYS=1 (si el bot no puede, el nivel "
            f"dejó de ser completable)."
        )
        return
    trace = solve_level_human_trace(level, has_sword=has_sword, max_macros=200000)
    assert trace is not None, f"L{level.number} ({level.name}): no es completable en modo humano"
    assert replay_wins(level, trace, has_sword=has_sword)
    REPLAY_DIR.mkdir(exist_ok=True)
    path.write_text(encode_commands(trace) + "\n", encoding="utf-8")
