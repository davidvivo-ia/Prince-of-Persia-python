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
from pathlib import Path

import pytest

from pop2026canon.application.controller import Command
from pop2026canon.application.tick import advance
from pop2026canon.domain.actions import Action
from pop2026canon.domain.chars import CharId
from pop2026canon.domain.game import Game, GameStatus, new_game
from pop2026canon.domain.level import Level
from pop2026canon.domain.levels_canon import CANON_LEVELS
from pop2026canon.domain.tiles import Tile
from tests.canon.test_completability import (
    _MACROS,
    _NOOP,
    _room_distances_to_goal,
    _settle,
)

REPLAY_DIR = Path(__file__).parent / "replays"

_STRIKE = Command(strike=True)
_SHIFT = Command(shift=True)
_UP = Command(up=True)
_R = Command(right=True)
_L = Command(left=True)
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
_HUMAN_MACROS = [
    *_MACROS,
    [(_R, 22)],
    [(_L, 22)],
    _FIGHT,
    _PARRY,
    [(_NOOP, 5)],
    [(_NOOP, 9)],
]


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
        guard_micro = [
            (c.repeat, c.curr_seq_id)
            for c in game.others
            if c.charid is CharId.GUARD and c.room == k.room
        ]
        combat = (*guard_micro, k.curr_seq_id, game.tick_count % 16)
    return (
        k.room,
        k.curr_col,
        k.curr_row,
        k.direction,
        k.hp_curr,
        k.has_sword,
        phase,
        game.state.open_gates,
        game.state.fallen_floors,
        guards,
        combat,
    )


def _run_macro_trace(
    game: Game, holds: list[tuple[Command, int]]
) -> tuple[Game | None, list[Command]]:
    """Como ``_run_macro`` pero devuelve también los comandos emitidos."""
    cmds: list[Command] = []
    for cmd, ticks in holds:
        for _ in range(ticks):
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


def solve_level_human_trace(
    level: Level, *, has_sword: bool, max_macros: int = 60000
) -> list[Command] | None:
    """A* en modo humano. Devuelve la secuencia de comandos ganadora."""
    dist = _room_distances_to_goal(level, Tile.LEVEL_DOOR_LEFT)
    start = _settle(new_game(level, starting_hp=campaign_hp(level.number), has_sword=has_sword))
    if start is None:
        return None
    seen = {_key(start)}
    counter = 0
    heap: list[tuple[int, int, Game, list[Command]]] = [
        (dist.get(start.kid.room, 99), counter, start, [])
    ]
    budget = max_macros
    # Cuota por sala: una sala cercana al exit pero sin salida (un duelo
    # que se pierde de mil formas) no puede devorar todo el presupuesto.
    room_quota = max(3000, max_macros // 6)
    room_spent: dict[int, int] = {}
    while heap and budget > 0:
        prio, _, game, trace = heapq.heappop(heap)
        room = game.kid.room
        if room_spent.get(room, 0) > room_quota and prio < 50:
            counter += 1
            heapq.heappush(heap, (prio + 50, counter, game, trace))
            continue
        for macro in _HUMAN_MACROS:
            room_spent[room] = room_spent.get(room, 0) + 1
            budget -= 1
            result, cmds = _run_macro_trace(game, macro)
            if result is None:
                continue
            if result.status is GameStatus.WON_LEVEL:
                return trace + cmds
            key = _key(result)
            if key in seen:
                continue
            seen.add(key)
            counter += 1
            heapq.heappush(heap, (dist.get(result.kid.room, 99), counter, result, trace + cmds))
    return None


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
