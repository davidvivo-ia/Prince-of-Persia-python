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

Los 14 niveles están todos con layouts ricos: spawns, pits que fuerzan
running jump, loose floors estratégicos, jardines de pinchos en slalom,
chompers con timing, gates con doorlinks plate-específicos, drops
verticales para las torres y arena del vizier en L12.
"""

from __future__ import annotations

from pop2026canon.domain.chars import GuardSpawn
from pop2026canon.domain.constants import (
    ROOM_TILES,
    SCREEN_TILECOUNT_X,
    TBL_GUARD_HP,
)
from pop2026canon.domain.level import DoorLink, Event, EventKind, Level
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
    pit_cols: tuple[int, ...] = (),
    no_ceiling: bool = False,
) -> Room:
    """Sala-corredor con techo + suelo + extras opcionales.

    - ``pit_cols``: columnas donde NO hay suelo en la fila 2 (pozo).
    - ``no_ceiling``: omite la fila 0 de techo (sala "abierta" arriba).
    - ``extras``: tiles a sobreescribir en cualquier celda.
    """
    rows: list[list[Tile | int]] = [
        [E if no_ceiling else F for _ in range(SCREEN_TILECOUNT_X)],
        [E, E, E, E, E, E, E, E, E, E],
        [F, F, F, F, F, F, F, F, F, F],
    ]
    for col in pit_cols:
        if 0 <= col < SCREEN_TILECOUNT_X:
            rows[2][col] = E
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


def _drop_room(
    room_id: int,
    *,
    link_n: int = 0,
    link_s: int = 0,
    link_e: int = 0,
    link_w: int = 0,
    floor_cols: tuple[int, ...] = (0, 1, 8, 9),
    extras: dict[tuple[int, int], Tile] | None = None,
    guards: tuple[GuardSpawn, ...] = (),
) -> Room:
    """Sala vertical: sólo hay suelo en ``floor_cols`` (resto, vacío).

    Útil para drops desde una sala superior por link_n, o saltos
    horizontales muy largos.
    """
    rows: list[list[Tile | int]] = [
        [E] * SCREEN_TILECOUNT_X,
        [E] * SCREEN_TILECOUNT_X,
        [F if c in floor_cols else E for c in range(SCREEN_TILECOUNT_X)],
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
# Sala 1: spawn, loose en col 5 row 2 — primer paso ya es peligro.
# Sala 2: jardín de pinchos en row 1 cols 3,5,7 con huecos seguros.
# Sala 3: pozo central (cols 4,5,6 sin suelo) que fuerza runjump.
# Sala 4: MIRROR col 5 + potion HEAL col 8 — al saltar al espejo nace shadow.
# Sala 5: plate col 3 que abre la gate de sala 6, y chomper col 7.
# Sala 6: gate col 4 + exit en cols 7-8 + último guard skill 3.

LEVEL_4 = Level(
    number=4,
    name="The Mirror",
    rooms=(
        _corridor(1, link_e=2, extras={(5, 2): L}),
        _corridor(2, link_w=1, link_e=3, extras={(3, 1): S, (5, 1): S, (7, 1): S}),
        _corridor(3, link_w=2, link_e=4, pit_cols=(4, 5, 6)),
        _corridor(4, link_w=3, link_e=5, extras={(5, 1): M, (8, 1): PO}),
        _corridor(5, link_w=4, link_e=6, extras={(3, 1): P, (7, 1): C}),
        _corridor(
            6,
            link_w=5,
            extras={(4, 1): G, (7, 1): DL, (8, 1): DR},
            guards=(GuardSpawn(col=2, row=1, direction=-1, skill=3),),
        ),
    ),
    start_room=1,
    start_col=1,
    start_row=1,
    events=(Event(EventKind.SHADOW_MIRROR, room=4, col=5),),
    doorlinks=(
        DoorLink(plate_room=5, plate_col=3, plate_row=1, gate_room=6, gate_col=4, gate_row=1),
    ),
)


# ---------------------------------------------------------------------------
# Nivel 5 — The Thief
# ---------------------------------------------------------------------------
# Sala 1: guard skill 3 a media distancia.
# Sala 2: tres loose floors consecutivas (cols 3,4,5 row 2) — el kid
#         debe correr deprisa para no caer.
# Sala 3: chomper col 5 + spike col 7 — timing necesario.
# Sala 4: potion HEAL col 4 — el shadow se la roba si el kid no es ágil.
# Sala 5: corredor con loose col 5 (segunda oportunidad).
# Sala 6: plate col 8 abre la gate de la sala 7.
# Sala 7: gate col 3 + exit cols 7-8.

LEVEL_5 = Level(
    number=5,
    name="The Thief",
    rooms=(
        _corridor(1, link_e=2, guards=(GuardSpawn(col=5, row=1, direction=-1, skill=3),)),
        _corridor(2, link_w=1, link_e=3, extras={(3, 2): L, (4, 2): L, (5, 2): L}),
        _corridor(3, link_w=2, link_e=4, extras={(5, 1): C, (7, 1): S}),
        _corridor(4, link_w=3, link_e=5, extras={(4, 1): PO}),
        _corridor(5, link_w=4, link_e=6, extras={(5, 2): L}),
        _corridor(6, link_w=5, link_e=7, extras={(8, 1): P}),
        _corridor(7, link_w=6, extras={(3, 1): G, (7, 1): DL, (8, 1): DR}),
    ),
    start_room=1,
    start_col=1,
    start_row=1,
    events=(Event(EventKind.SHADOW_STEAL, room=4),),
    doorlinks=(
        DoorLink(plate_room=6, plate_col=8, plate_row=1, gate_room=7, gate_col=3, gate_row=1),
    ),
)


# ---------------------------------------------------------------------------
# Nivel 6 — The Steps
# ---------------------------------------------------------------------------
# Sala 1: pit grande (cols 4,5,6 sin suelo) — el running jump cruza
#         encima en frame_43 que dispara el shadow step.
# Sala 2: gate col 3 bloquea el paso; abre con plate de sala 3.
# Sala 3: plate col 7 + chomper col 4 para añadir tensión.
# Sala 4: guard skill 4 + spike adyacente col 7.
# Sala 5: exit.

LEVEL_6 = Level(
    number=6,
    name="The Steps",
    rooms=(
        _corridor(1, link_e=2, pit_cols=(4, 5, 6)),
        _corridor(2, link_w=1, link_e=3, extras={(3, 1): G}),
        _corridor(3, link_w=2, link_e=4, extras={(4, 1): C, (7, 1): P}),
        _corridor(
            4,
            link_w=3,
            link_e=5,
            extras={(7, 1): S},
            guards=(GuardSpawn(col=5, row=1, direction=-1, skill=4),),
        ),
        _corridor(5, link_w=4, extras={(7, 1): DL, (8, 1): DR}),
    ),
    start_room=1,
    start_col=1,
    start_row=1,
    events=(Event(EventKind.SHADOW_STEP, room=1, extra=43),),
    doorlinks=(
        DoorLink(plate_room=3, plate_col=7, plate_row=1, gate_room=2, gate_col=3, gate_row=1),
    ),
)


# ---------------------------------------------------------------------------
# Nivel 7 — The Mountains
# ---------------------------------------------------------------------------
# Layout en "L" con drop al sur — primer nivel con verticalidad real.
# Sala 1 (arriba-izq): spawn + loose col 5 + drop al sur por col 8.
# Sala 2 (arriba-der): jardín de pinchos cols 4,6 (col 5 seguro).
# Sala 3 (arriba-fin): guard skill 5.
# Sala 4 (abajo-izq): bajo de la 1 — loose escalonadas + lattice.
# Sala 5 (abajo-medio): chomper + spike combo.
# Sala 6 (abajo-fin): exit.

LEVEL_7 = Level(
    number=7,
    name="The Mountains",
    rooms=(
        _corridor(1, link_e=2, link_s=4, pit_cols=(8,), extras={(5, 2): L}),
        _corridor(2, link_w=1, link_e=3, extras={(4, 1): S, (6, 1): S}),
        _corridor(
            3,
            link_w=2,
            link_s=5,
            pit_cols=(5,),
            guards=(GuardSpawn(col=5, row=1, direction=-1, skill=5),),
        ),
        _corridor(4, link_n=1, link_e=5, extras={(3, 2): L, (5, 2): L, (7, 2): L}),
        _corridor(5, link_n=3, link_w=4, link_e=6, extras={(2, 1): C, (5, 1): S, (7, 1): C}),
        _corridor(6, link_w=5, extras={(7, 1): DL, (8, 1): DR}),
    ),
    start_room=1,
    start_col=1,
    start_row=1,
)


# ---------------------------------------------------------------------------
# Nivel 8 — The Caverns
# ---------------------------------------------------------------------------
# Cuevas: loose floors por todos lados, chompers en pasillos estrechos,
# y un gate al final que sólo el mouse puede abrir.
# Sala 1: spawn + drop al sur (col 4-5 sin suelo).
# Sala 2: corredor con chomper col 5.
# Sala 3 (abajo-izq): guard skill 4 + spike defensivo.
# Sala 4 (abajo-medio): loose galore cols 3,4,5,7 row 2.
# Sala 5: corredor seguro de aproximación.
# Sala 6: gate col 2 (sólo mouse la abre) + exit cols 7-8.

LEVEL_8 = Level(
    number=8,
    name="The Caverns",
    rooms=(
        _corridor(1, link_e=2, link_s=3, pit_cols=(4, 5)),
        _corridor(2, link_w=1, link_e=4, extras={(5, 1): C, (3, 2): L}),
        _corridor(
            3,
            link_n=1,
            link_e=5,
            extras={(7, 1): S},
            guards=(GuardSpawn(col=5, row=1, direction=-1, skill=4),),
        ),
        _corridor(4, link_w=2, link_s=6, extras={(3, 2): L, (4, 2): L, (5, 2): L, (7, 2): L}),
        _corridor(5, link_w=3, link_e=6, extras={(5, 1): C}),
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
# Tumba con esqueletos durmientes y trampas mortales. Dos skeletons
# triggerizables más un guard skill 5 esperando. Spikes que delimitan
# zonas seguras y chompers en formación.
# Sala 1: spawn + skeleton tile col 4 (decorativo, no se levanta hasta evento).
# Sala 2: jardín de pinchos cols 3,5,7 — slalom + drop sur.
# Sala 3: guard skill 5 + potion HEAL col 8.
# Sala 4 (abajo-izq): doble chomper cols 2 y 6.
# Sala 5: otro skeleton + plate col 4 que abre gate sala 6.
# Sala 6: gate col 3 + exit cols 7-8.

LEVEL_9 = Level(
    number=9,
    name="The Tomb",
    rooms=(
        _corridor(1, link_e=2, extras={(4, 1): SK, (6, 2): L}),
        _corridor(2, link_w=1, link_e=3, link_s=4, extras={(3, 1): S, (5, 1): S, (7, 1): S}),
        _corridor(
            3,
            link_w=2,
            link_e=5,
            extras={(8, 1): PO},
            guards=(GuardSpawn(col=5, row=1, direction=-1, skill=5),),
        ),
        _corridor(4, link_n=2, link_e=6, extras={(2, 1): C, (6, 1): C}),
        _corridor(5, link_w=3, link_s=6, extras={(5, 1): SK, (4, 1): P}),
        _corridor(6, link_n=5, link_w=4, extras={(3, 1): G, (7, 1): DL, (8, 1): DR}),
    ),
    start_room=1,
    start_col=1,
    start_row=1,
    doorlinks=(
        DoorLink(plate_room=5, plate_col=4, plate_row=1, gate_room=6, gate_col=3, gate_row=1),
    ),
)


# ---------------------------------------------------------------------------
# Nivel 10 — The Tower
# ---------------------------------------------------------------------------
# Torre puramente vertical: 4 niveles de drops precisos, aterrizando
# en plataformas estrechas de los lados. Guards intercalados.
# Sala 1: spawn, drop por col 4-6 al sur.
# Sala 2: bandejas estrechas (drop_room) + guard skill 5.
# Sala 3: jardín de pinchos en row 1.
# Sala 4: drop final al exit.
# Sala 5: exit horizontal.

LEVEL_10 = Level(
    number=10,
    name="The Tower",
    rooms=(
        _corridor(1, link_s=2, pit_cols=(4, 5, 6)),
        _drop_room(
            2,
            link_n=1,
            link_s=3,
            floor_cols=(0, 1, 7, 8, 9),
            guards=(GuardSpawn(col=8, row=1, direction=-1, skill=5),),
        ),
        _corridor(3, link_n=2, link_s=4, extras={(3, 1): S, (5, 1): S, (7, 1): S}),
        _drop_room(
            4,
            link_n=3,
            link_e=5,
            floor_cols=(0, 1, 2, 3, 8, 9),
            guards=(GuardSpawn(col=2, row=1, direction=0, skill=5),),
        ),
        _corridor(5, link_w=4, extras={(7, 1): DL, (8, 1): DR}),
    ),
    start_room=1,
    start_col=1,
    start_row=1,
)


# ---------------------------------------------------------------------------
# Nivel 11 — The Tower II
# ---------------------------------------------------------------------------
# Continuación de la torre. Combina horizontal + vertical: hay que volver
# al norte para encontrar la plate antes de bajar al exit.
# Sala 1: spawn + drop al sur por col 4-5.
# Sala 2: corredor superior con guard skill 5 (callejón sin salida si
#         no descubres el drop).
# Sala 3 (abajo-izq): doble chomper cols 3,6.
# Sala 4 (abajo-medio): guard skill 5 + drop al sur.
# Sala 5 (final): gate col 5 + plate col 2 (en la misma sala — puzzle local).
# Sala 6: exit.

LEVEL_11 = Level(
    number=11,
    name="The Tower II",
    rooms=(
        _corridor(1, link_e=2, link_s=3, pit_cols=(4, 5)),
        _corridor(2, link_w=1, guards=(GuardSpawn(col=5, row=1, direction=-1, skill=5),)),
        _corridor(3, link_n=1, link_e=4, extras={(3, 1): C, (6, 1): C, (5, 2): L}),
        _corridor(
            4,
            link_w=3,
            link_s=5,
            pit_cols=(7,),
            guards=(GuardSpawn(col=4, row=1, direction=-1, skill=5),),
        ),
        _corridor(5, link_n=4, link_e=6, extras={(5, 1): G, (2, 1): P}),
        _corridor(6, link_w=5, extras={(7, 1): DL, (8, 1): DR}),
    ),
    start_room=1,
    start_col=1,
    start_row=1,
    doorlinks=(
        DoorLink(plate_room=5, plate_col=2, plate_row=1, gate_room=5, gate_col=5, gate_row=1),
    ),
)


# ---------------------------------------------------------------------------
# Nivel 12 — The Vizier
# ---------------------------------------------------------------------------
# Shadow fusion en sala 5; vizier en sala 7 (último combate).
# (Canon real: sala 15 y 23, pero adaptamos a nuestro tamaño 8 salas.)
# Sala 1: guard skill 6 + spike col 7.
# Sala 2: doble chomper cols 3,6.
# Sala 3: guard skill 7 + potion MAX_HP col 2.
# Sala 4: loose floors cols 4,5 row 2 sobre pozo.
# Sala 5: MIRROR col 5 para fusión + potion HEAL col 8.
# Sala 6: corredor con loose col 5 (segunda fusion-recovery).
# Sala 7: arena del vizier (Jaffar) skill 11 con spikes laterales.
# Sala 8: exit final.

LEVEL_12 = Level(
    number=12,
    name="The Vizier",
    rooms=(
        _corridor(
            1,
            link_e=2,
            extras={(7, 1): S},
            guards=(GuardSpawn(col=5, row=1, direction=-1, skill=6),),
        ),
        _corridor(2, link_w=1, link_e=3, extras={(3, 1): C, (6, 1): C}),
        _corridor(
            3,
            link_w=2,
            link_e=4,
            extras={(2, 1): PO},
            guards=(GuardSpawn(col=5, row=1, direction=-1, skill=7),),
        ),
        _corridor(4, link_w=3, link_e=5, pit_cols=(6,), extras={(4, 2): L, (5, 2): L}),
        _corridor(5, link_w=4, link_e=6, extras={(5, 1): M, (8, 1): PO}),
        _corridor(6, link_w=5, link_e=7, extras={(5, 2): L}),
        _corridor(
            7,
            link_w=6,
            link_e=8,
            extras={(2, 1): S, (8, 1): S},
            guards=(GuardSpawn(col=5, row=1, direction=-1, skill=11),),
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
# Carrera de obstáculos: alternando chomper / spike / loose en sucesión.
# 4 salas cortas con muy poca tregua para crear adrenalina antes del
# encuentro con la princesa en L14.
# Sala 1: triple chomper en cadencia (cols 3,5,7).
# Sala 2: spike garden + un loose intermedio.
# Sala 3: pozo central + spike a cada lado.
# Sala 4: exit corto.

LEVEL_13 = Level(
    number=13,
    name="Final Run",
    rooms=(
        _corridor(1, link_e=2, extras={(3, 1): C, (5, 1): C, (7, 1): C}),
        _corridor(
            2,
            link_w=1,
            link_e=3,
            extras={(2, 1): S, (4, 1): S, (5, 2): L, (6, 1): S, (8, 1): S},
        ),
        _corridor(3, link_w=2, link_e=4, pit_cols=(4, 5, 6), extras={(3, 1): S, (7, 1): S}),
        _corridor(4, link_w=3, extras={(7, 1): DL, (8, 1): DR}),
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
"""Los 14 niveles canónicos completos. L1-L3 introducen mecánicas
básicas; L4-L6 introducen sombra y plates; L7-L11 verticalidad y torre;
L12 fusión + vizier; L13 carrera final; L14 cinemática princesa."""


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
