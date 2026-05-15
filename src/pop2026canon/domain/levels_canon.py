"""Los 14 niveles canónicos del POP1 original.

**Fuente**: walkthroughs comunidad (popot.org, gamefaqs, popuw.com) y
descripciones canónicas documentadas. NO se ha podido obtener el binario
``LEVELS.DAT`` original (propiedad de Broderbund). Estos layouts son
**fan-recreation fieles a la canon** (mismas mecánicas, progresión y
eventos), pero no byte-perfect.

Nivel a nivel:
- L1  The Dungeon       — sala 1 prince tumbado, drop, ir oeste por
                           sword, volver este, kill guard, plate→exit.
- L2  The Guards        — multi-room, loose floors, chomper, 2 guards.
- L3  The Skeleton      — skeleton wake en sala 1 trigger, multi-room.
- L4  The Mirror        — espejo en sala 4, shadow nace cruzándolo.
- L5  The Thief         — shadow roba la potion en sala 24.
- L6  The Steps         — shadow step trigger frame_43, salto largo.
- L7  The Mountains     — vertical, lattices.
- L8  The Caverns       — cuevas con loose y mouse para gate.
- L9  The Tomb          — múltiples skeletons.
- L10 The Tower         — torre vertical.
- L11 The Tower II      — continúa.
- L12 The Vizier        — sala 15 shadow fusion, vizier (Jaffar) final.
- L13 Final Run         — carrera tras vencer Jaffar.
- L14 Ending            — princess + mouse cinemática.

Los layouts detallados se construyen progresivamente. L1-L3 detallados;
L4-L14 con estructura mínima y eventos correctos (TODO: refinar).
"""

from __future__ import annotations

from pop2026canon.domain.chars import GuardSpawn
from pop2026canon.domain.constants import (
    ROOM_TILES,
    SCREEN_TILECOUNT_X,
    TBL_GUARD_HP,
)
from pop2026canon.domain.level import Event, EventKind, Level
from pop2026canon.domain.room import Room
from pop2026canon.domain.tiles import Tile, encode_tile

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row(tiles: list[Tile | int]) -> list[int]:
    """Convierte una lista de Tile en bytes encode_tile (modifier 0)."""
    if len(tiles) != SCREEN_TILECOUNT_X:
        raise ValueError(f"row debe tener {SCREEN_TILECOUNT_X} tiles")
    return [encode_tile(Tile(t), 0) if isinstance(t, int) else encode_tile(t, 0) for t in tiles]


def _room(
    room_id: int,
    rows: tuple[list[Tile | int], list[Tile | int], list[Tile | int]],
    *,
    link_n: int = 0,
    link_s: int = 0,
    link_e: int = 0,
    link_w: int = 0,
    guards: tuple[GuardSpawn, ...] = (),
    bg_overrides: dict[tuple[int, int], int] | None = None,
) -> Room:
    """Construye un Room desde 3 filas de 10 tiles cada una."""
    fg = []
    for r in rows:
        fg.extend(_row(r))
    bg = [0] * ROOM_TILES
    if bg_overrides:
        for (col, row), val in bg_overrides.items():
            bg[row * SCREEN_TILECOUNT_X + col] = val
    return Room(
        id=room_id,
        fg=tuple(fg),
        bg=tuple(bg),
        link_n=link_n,
        link_s=link_s,
        link_e=link_e,
        link_w=link_w,
        guards=guards,
    )


# Aliases para construir filas legibles
E = Tile.EMPTY
F = Tile.FLOOR
W = Tile.WALL
S = Tile.SPIKE
L = Tile.LOOSE
G = Tile.GATE
P = Tile.OPENER  # plate
C = Tile.CHOMPER
M = Tile.MIRROR
SK = Tile.SKELETON
SW = Tile.SWORD
DL = Tile.LEVEL_DOOR_LEFT
DR = Tile.LEVEL_DOOR_RIGHT
PO = Tile.POTION
T = Tile.TORCH
PI = Tile.PILLAR


# ===========================================================================
# Nivel 1 — The Dungeon
#
# Sala 1: kid spawnea aquí, tumbado. Hay un loose floor a mitad de camino;
#         el kid debe caer al sur (sala 2).
# Sala 2: corredor inferior. Sword al oeste (sala 4), guard al este (sala 3).
# Sala 3: corredor con el primer guard (HP=4). Tras él, exit-door y plate.
# Sala 4: sala oeste con la SWORD en el suelo.
# Sala 5: sala con la plate que abre la exit-door.
#
# Layout:
#                   [1]
#                    ↓
#         [4] ← [2] → [3]
#                    ↓
#                   [5]
#
# Convención: rooms 1-indexed.
# ===========================================================================


_L1_ROOM_1 = _room(
    1,
    rows=(
        [F, F, F, F, F, F, F, F, F, F],  # techo
        [E, E, E, E, E, E, E, E, E, E],  # aire — kid spawnea aquí
        [F, F, F, F, L, L, F, F, F, F],  # suelo con loose en col 4-5
    ),
    link_s=2,
)


_L1_ROOM_2 = _room(
    2,
    rows=(
        [F, F, F, F, F, F, F, F, F, F],
        [E, E, E, E, E, E, E, E, E, E],  # corredor central
        [F, F, F, F, F, F, F, F, F, F],
    ),
    link_n=1,
    link_e=3,
    link_w=4,
)


_L1_ROOM_3 = _room(
    3,
    rows=(
        [F, F, F, F, F, F, F, F, F, F],
        [E, E, E, E, E, E, E, E, DL, DR],  # exit door a la derecha
        [F, F, F, F, F, F, F, F, F, F],
    ),
    link_w=2,
    link_s=5,
    guards=(GuardSpawn(col=4, row=1, direction=-1, skill=0),),
)


_L1_ROOM_4 = _room(
    4,
    rows=(
        [F, F, F, F, F, F, F, F, F, F],
        [E, E, SW, E, E, E, E, E, E, E],  # ESPADA en col 2 row 1
        [F, F, F, F, F, F, F, F, F, F],
    ),
    link_e=2,
)


_L1_ROOM_5 = _room(
    5,
    rows=(
        [F, F, F, F, F, F, F, F, F, F],
        [E, E, P, E, E, E, E, E, E, E],  # plate en col 2
        [F, F, F, F, F, F, F, F, F, F],
    ),
    link_n=3,
)


LEVEL_1 = Level(
    number=1,
    name="The Dungeon",
    rooms=(_L1_ROOM_1, _L1_ROOM_2, _L1_ROOM_3, _L1_ROOM_4, _L1_ROOM_5),
    start_room=1,
    start_col=4,
    start_row=1,
    start_direction=-1,
)


# ===========================================================================
# Nivel 2 — The Guards
#
# Multi-room con dos guards, chomper introductorio, loose floors.
# Layout simple para iteración inicial.
# ===========================================================================


_L2_ROOM_1 = _room(
    1,
    rows=(
        [F, F, F, F, F, F, F, F, F, F],
        [E, E, E, E, E, E, E, E, E, E],
        [F, F, L, L, F, F, F, F, F, F],
    ),
    link_e=2,
)


_L2_ROOM_2 = _room(
    2,
    rows=(
        [F, F, F, F, F, F, F, F, F, F],
        [E, E, E, E, E, E, E, E, E, E],
        [F, F, F, F, F, F, F, F, F, F],
    ),
    link_w=1,
    link_e=3,
    guards=(GuardSpawn(col=5, row=1, direction=-1, skill=1),),
)


_L2_ROOM_3 = _room(
    3,
    rows=(
        [F, F, F, F, F, F, F, F, F, F],
        [E, E, E, E, C, E, E, E, E, E],  # chomper en col 4
        [F, F, F, F, F, F, F, F, F, F],
    ),
    link_w=2,
    link_e=4,
)


_L2_ROOM_4 = _room(
    4,
    rows=(
        [F, F, F, F, F, F, F, F, F, F],
        [E, E, E, E, E, E, E, E, DL, DR],
        [F, F, F, F, F, F, F, F, F, F],
    ),
    link_w=3,
    guards=(GuardSpawn(col=3, row=1, direction=-1, skill=1),),
)


LEVEL_2 = Level(
    number=2,
    name="The Guards",
    rooms=(_L2_ROOM_1, _L2_ROOM_2, _L2_ROOM_3, _L2_ROOM_4),
    start_room=1,
    start_col=2,
    start_row=1,
)


# ===========================================================================
# Nivel 3 — The Skeleton
#
# Sala 1: el esqueleto está tumbado en una celda. Cuando el kid pisa una
# columna específica, se levanta como char `charid_4`.
# ===========================================================================


_L3_ROOM_1 = _room(
    1,
    rows=(
        [F, F, F, F, F, F, F, F, F, F],
        [E, E, E, E, SK, E, E, E, E, E],  # esqueleto en col 4
        [F, F, F, F, F, F, F, F, F, F],
    ),
    link_e=2,
)


_L3_ROOM_2 = _room(
    2,
    rows=(
        [F, F, F, F, F, F, F, F, F, F],
        [E, E, E, E, E, E, E, E, E, E],
        [F, F, L, L, F, F, L, L, F, F],
    ),
    link_w=1,
    link_e=3,
)


_L3_ROOM_3 = _room(
    3,
    rows=(
        [F, F, F, F, F, F, F, F, F, F],
        [E, E, E, E, E, E, E, E, DL, DR],
        [F, F, F, F, F, F, F, F, F, F],
    ),
    link_w=2,
    guards=(GuardSpawn(col=3, row=1, direction=-1, skill=2),),
)


LEVEL_3 = Level(
    number=3,
    name="The Skeleton",
    rooms=(_L3_ROOM_1, _L3_ROOM_2, _L3_ROOM_3),
    start_room=1,
    start_col=1,
    start_row=1,
    events=(
        Event(EventKind.SKELETON_WAKE, room=1, col=2),  # trigger en col 2
    ),
)


# ===========================================================================
# Niveles 4-14 — multi-room canon
#
# Cada nivel tiene 5-12 salas con la mecánica/evento canónico apropiado.
# Los layouts son inspirados en walkthroughs comunidad (no byte-perfect
# vs LEVELS.DAT, pero reconocibles por un fan).
# ===========================================================================


def _corridor(
    room_id: int,
    *,
    link_e: int = 0,
    link_w: int = 0,
    link_s: int = 0,
    link_n: int = 0,
    extras: dict[tuple[int, int], Tile] | None = None,
    guards: tuple[GuardSpawn, ...] = (),
) -> Room:
    """Sala-corredor estándar con techo + suelo + extras opcionales."""
    rows: list[list[Tile | int]] = [
        [F, F, F, F, F, F, F, F, F, F],
        [E, E, E, E, E, E, E, E, E, E],
        [F, F, F, F, F, F, F, F, F, F],
    ]
    if extras:
        for (col, row), tile in extras.items():
            rows[row][col] = tile
    return _room(
        room_id,
        rows=(rows[0], rows[1], rows[2]),
        link_n=link_n,
        link_s=link_s,
        link_e=link_e,
        link_w=link_w,
        guards=guards,
    )


# ---------------------------------------------------------------------------
# Nivel 4 — The Mirror
# ---------------------------------------------------------------------------
# 6 salas: spawn → corredor con pinchos → sala mirror (sala 4) → after-mirror →
# tras pasar el mirror, shadow nace y huye al oeste → exit.

LEVEL_4 = Level(
    number=4,
    name="The Mirror",
    rooms=(
        _corridor(1, link_e=2),
        _corridor(2, link_w=1, link_e=3, extras={(4, 1): S, (5, 1): E}),
        _corridor(3, link_w=2, link_e=4),
        # Sala 4 — MIRROR en col 5 row 1
        _corridor(4, link_w=3, link_e=5, extras={(5, 1): M}),
        _corridor(5, link_w=4, link_e=6, extras={(4, 1): P}),  # plate
        _corridor(6, link_w=5, extras={(7, 1): DL, (8, 1): DR}),  # exit
    ),
    start_room=1,
    start_col=1,
    start_row=1,
    events=(Event(EventKind.SHADOW_MIRROR, room=4, col=5),),
)


# ---------------------------------------------------------------------------
# Nivel 5 — The Thief
# ---------------------------------------------------------------------------
# 7 salas: shadow roba potion en sala "24" (en nuestro layout, la sala con
# la potion central).

LEVEL_5 = Level(
    number=5,
    name="The Thief",
    rooms=(
        _corridor(1, link_e=2, guards=(GuardSpawn(col=4, row=1, direction=-1, skill=3),)),
        _corridor(2, link_w=1, link_e=3, extras={(3, 1): L, (4, 1): L}),
        _corridor(3, link_w=2, link_e=4, extras={(5, 1): C}),
        _corridor(4, link_w=3, link_e=5, extras={(4, 1): PO}),
        _corridor(5, link_w=4, link_e=6),
        _corridor(6, link_w=5, link_e=7, extras={(3, 1): P}),
        _corridor(7, link_w=6, extras={(7, 1): DL, (8, 1): DR}),
    ),
    start_room=1,
    start_col=1,
    start_row=1,
    events=(Event(EventKind.SHADOW_STEAL, room=4),),
)


# ---------------------------------------------------------------------------
# Nivel 6 — The Steps
# ---------------------------------------------------------------------------
# 5 salas: en sala 1 hay un salto largo con un pit; cuando el kid
# está en frame_43 (mid-runjump), el shadow aparece desde el otro lado.

LEVEL_6 = Level(
    number=6,
    name="The Steps",
    rooms=(
        _corridor(1, link_e=2, extras={(5, 2): E, (6, 2): E}),  # pit central
        _corridor(2, link_w=1, link_e=3, extras={(3, 1): G}),  # gate
        _corridor(3, link_w=2, link_e=4, extras={(7, 1): P}),  # plate
        _corridor(4, link_w=3, link_e=5, guards=(GuardSpawn(col=5, row=1, direction=-1, skill=4),)),
        _corridor(5, link_w=4, extras={(7, 1): DL, (8, 1): DR}),
    ),
    start_room=1,
    start_col=1,
    start_row=1,
    events=(Event(EventKind.SHADOW_STEP, room=1, extra=43),),
)


# ---------------------------------------------------------------------------
# Nivel 7 — The Mountains
# ---------------------------------------------------------------------------

LEVEL_7 = Level(
    number=7,
    name="The Mountains",
    rooms=(
        _corridor(1, link_e=2, link_s=4),
        _corridor(2, link_w=1, link_e=3, extras={(4, 1): S, (5, 1): E, (6, 1): S}),
        _corridor(3, link_w=2, link_s=5, guards=(GuardSpawn(col=5, row=1, direction=-1, skill=5),)),
        _corridor(4, link_n=1, link_e=5, extras={(3, 1): L, (4, 1): L}),
        _corridor(5, link_n=3, link_w=4, link_e=6, extras={(2, 1): C}),
        _corridor(6, link_w=5, extras={(7, 1): DL, (8, 1): DR}),
    ),
    start_room=1,
    start_col=1,
    start_row=1,
)


# ---------------------------------------------------------------------------
# Nivel 8 — The Caverns
# ---------------------------------------------------------------------------
# Mouse aparece en sala 24 (en nuestro layout, sala 6) para abrir la última gate

LEVEL_8 = Level(
    number=8,
    name="The Caverns",
    rooms=(
        _corridor(1, link_e=2, link_s=3),
        _corridor(2, link_w=1, link_e=4, extras={(5, 1): C}),
        _corridor(3, link_n=1, link_e=5, guards=(GuardSpawn(col=5, row=1, direction=-1, skill=4),)),
        _corridor(4, link_w=2, link_s=6, extras={(3, 1): L, (4, 1): L, (5, 1): L}),
        _corridor(5, link_w=3, link_e=6),
        _corridor(6, link_n=4, link_w=5, extras={(2, 1): G, (7, 1): DL, (8, 1): DR}),
    ),
    start_room=1,
    start_col=1,
    start_row=1,
    events=(Event(EventKind.MOUSE_APPEAR, room=6),),
)


# ---------------------------------------------------------------------------
# Nivel 9 — The Tomb
# ---------------------------------------------------------------------------

LEVEL_9 = Level(
    number=9,
    name="The Tomb",
    rooms=(
        _corridor(1, link_e=2, extras={(4, 1): SK}),  # skeleton tile
        _corridor(2, link_w=1, link_e=3, link_s=4, extras={(3, 1): S, (4, 1): E, (5, 1): S}),
        _corridor(3, link_w=2, link_e=5, guards=(GuardSpawn(col=5, row=1, direction=-1, skill=5),)),
        _corridor(4, link_n=2, link_e=6, extras={(2, 1): C, (6, 1): C}),
        _corridor(5, link_w=3, link_s=6, extras={(5, 1): SK}),  # another skel
        _corridor(6, link_n=5, link_w=4, extras={(7, 1): DL, (8, 1): DR}),
    ),
    start_room=1,
    start_col=1,
    start_row=1,
)


# ---------------------------------------------------------------------------
# Nivel 10 — The Tower
# ---------------------------------------------------------------------------
# Vertical: spawn arriba, baja por gaps hasta el exit.

LEVEL_10 = Level(
    number=10,
    name="The Tower",
    rooms=(
        _corridor(1, link_s=2, extras={(5, 2): E}),  # gap en suelo
        _corridor(2, link_n=1, link_s=3, guards=(GuardSpawn(col=5, row=1, direction=-1, skill=5),)),
        _corridor(3, link_n=2, link_s=4, extras={(3, 1): S, (5, 1): S, (7, 1): S}),
        _corridor(4, link_n=3, link_e=5, guards=(GuardSpawn(col=4, row=1, direction=-1, skill=5),)),
        _corridor(5, link_w=4, extras={(7, 1): DL, (8, 1): DR}),
    ),
    start_room=1,
    start_col=1,
    start_row=1,
)


# ---------------------------------------------------------------------------
# Nivel 11 — The Tower II
# ---------------------------------------------------------------------------

LEVEL_11 = Level(
    number=11,
    name="The Tower II",
    rooms=(
        _corridor(1, link_e=2, link_s=3),
        _corridor(2, link_w=1, guards=(GuardSpawn(col=5, row=1, direction=-1, skill=5),)),
        _corridor(3, link_n=1, link_e=4, extras={(3, 1): C, (6, 1): C}),
        _corridor(4, link_w=3, link_s=5, guards=(GuardSpawn(col=5, row=1, direction=-1, skill=5),)),
        _corridor(5, link_n=4, link_e=6, extras={(5, 1): G, (2, 1): P}),
        _corridor(6, link_w=5, extras={(7, 1): DL, (8, 1): DR}),
    ),
    start_room=1,
    start_col=1,
    start_row=1,
)


# ---------------------------------------------------------------------------
# Nivel 12 — The Vizier
# ---------------------------------------------------------------------------
# Shadow fusion en sala 5; vizier en sala 7 (último combate).
# (Canon real: sala 15 y 23, pero adaptamos a nuestro tamaño 8 salas.)

LEVEL_12 = Level(
    number=12,
    name="The Vizier",
    rooms=(
        _corridor(1, link_e=2, guards=(GuardSpawn(col=5, row=1, direction=-1, skill=6),)),
        _corridor(2, link_w=1, link_e=3, extras={(3, 1): C, (6, 1): C}),
        _corridor(3, link_w=2, link_e=4, guards=(GuardSpawn(col=5, row=1, direction=-1, skill=7),)),
        _corridor(4, link_w=3, link_e=5, extras={(4, 1): L, (5, 1): L}),
        # Sala 5 — fusion shadow
        _corridor(5, link_w=4, link_e=6, extras={(5, 1): M}),  # mirror para fusión
        _corridor(6, link_w=5, link_e=7),
        # Sala 7 — vizier (Jaffar) combate final
        _corridor(
            7, link_w=6, link_e=8, guards=(GuardSpawn(col=5, row=1, direction=-1, skill=11),)
        ),
        _corridor(8, link_w=7, extras={(7, 1): DL, (8, 1): DR}),
    ),
    start_room=1,
    start_col=1,
    start_row=1,
    events=(
        Event(EventKind.SHADOW_FUSION, room=5, col=5),
        Event(EventKind.VIZIER_INIT, room=7),
    ),
)


# ---------------------------------------------------------------------------
# Nivel 13 — Final Run (carrera tras vencer Jaffar)
# ---------------------------------------------------------------------------

LEVEL_13 = Level(
    number=13,
    name="Final Run",
    rooms=(
        _corridor(1, link_e=2, extras={(4, 1): C, (6, 1): C}),
        _corridor(2, link_w=1, link_e=3, extras={(3, 1): S, (5, 1): S, (7, 1): S}),
        _corridor(3, link_w=2, extras={(7, 1): DL, (8, 1): DR}),
    ),
    start_room=1,
    start_col=1,
    start_row=1,
)


# ---------------------------------------------------------------------------
# Nivel 14 — Ending (cinemática princesa)
# ---------------------------------------------------------------------------

LEVEL_14 = Level(
    number=14,
    name="Ending",
    rooms=(
        _corridor(1, extras={(5, 1): T}),  # antorcha, princesa
    ),
    start_room=1,
    start_col=2,
    start_row=1,
    events=(Event(EventKind.PRINCESS_REUNION, room=1),),
)


# ---------------------------------------------------------------------------
# Tabla canónica de los 14 niveles
# ---------------------------------------------------------------------------

CANON_LEVELS: tuple[Level, ...] = (
    LEVEL_1,
    LEVEL_2,
    LEVEL_3,
    LEVEL_4,
    LEVEL_5,
    LEVEL_6,
    LEVEL_7,
    LEVEL_8,
    LEVEL_9,
    LEVEL_10,
    LEVEL_11,
    LEVEL_12,
    LEVEL_13,
    LEVEL_14,
)
"""Los 14 niveles canónicos. Niveles 1-3 detallados; 4-14 stubs con
eventos correctos. Refinamiento progresivo en FASE 3.3."""


def load_canon(level_number: int) -> Level:
    """Devuelve el ``Level`` canónico para ``level_number`` (1..14)."""
    if not (1 <= level_number <= 14):
        raise ValueError(f"level_number {level_number} fuera de [1, 14]")
    return CANON_LEVELS[level_number - 1]


def guard_hp_for_level(level_number: int) -> int:
    """HP del guard estándar en ese nivel — desde `TBL_GUARD_HP`."""
    if not (1 <= level_number <= 14):
        raise ValueError(f"level_number {level_number} fuera de [1, 14]")
    return TBL_GUARD_HP[level_number - 1]
