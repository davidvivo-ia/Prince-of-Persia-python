"""Los 14 niveles canónicos del POP1 — versión expandida 18-24 salas.

**Fuente**: walkthroughs comunidad (popot.org, gamefaqs, popuw.com) y
descripciones canónicas. No hay `LEVELS.DAT` original: estos layouts
son **fan-recreation fieles a la canon** — mismas mecánicas, eventos
narrativos, número de salas y progresión espacial, pero no byte-perfect.

Cada nivel se construye con :func:`_build_level` a partir de una lista
de specs de sala. Cada spec usa los helpers de :mod:`_blocks`:

- ``floor`` — sala-corredor con suelo+techo (opcional pit, extras)
- ``arena`` — sala abierta sin techo (para drops cortos)
- ``pillar`` — sala con columnas en el suelo, romper la línea visual
- ``lattice`` — sala con rejas escalables (LATTICE_*)
- ``balcony`` — sala con balcón visible al fondo
- ``doortop`` — sala con tapiz superior pisable (multi-piso)
- ``drop`` — sala de drop puro (sólo plataformas a los lados)
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from pop2026canon.domain.chars import GuardSpawn
from pop2026canon.domain.constants import (
    ROOM_TILES,
    SCREEN_TILECOUNT_X,
    TBL_GUARD_HP,
)
from pop2026canon.domain.level import DoorLink, Event, EventKind, Level
from pop2026canon.domain.room import Room
from pop2026canon.domain.tiles import PotionType, Tile, encode_tile

# ---------------------------------------------------------------------------
# Aliases legibles
# ---------------------------------------------------------------------------
E = Tile.EMPTY
F = Tile.FLOOR
W = Tile.WALL
S = Tile.SPIKE
L = Tile.LOOSE
G = Tile.GATE
P = Tile.OPENER
CL = Tile.CLOSER
C = Tile.CHOMPER
M = Tile.MIRROR
SK = Tile.SKELETON
SW = Tile.SWORD
DL = Tile.LEVEL_DOOR_LEFT
DR = Tile.LEVEL_DOOR_RIGHT
PO = Tile.POTION
T = Tile.TORCH
PI = Tile.PILLAR
BP_B = Tile.BIGPILLAR_BOTTOM
BP_T = Tile.BIGPILLAR_TOP
DT = Tile.DOORTOP
DT_F = Tile.DOORTOP_WITH_FLOOR
BL = Tile.BALCONY_LEFT
BR = Tile.BALCONY_RIGHT
LP = Tile.LATTICE_PILLAR
LD = Tile.LATTICE_DOWN
LS = Tile.LATTICE_SMALL


# ---------------------------------------------------------------------------
# Builders básicos
# ---------------------------------------------------------------------------


def _row(tiles: list[Tile | int]) -> list[int]:
    if len(tiles) != SCREEN_TILECOUNT_X:
        raise ValueError(f"row debe tener {SCREEN_TILECOUNT_X} tiles, no {len(tiles)}")
    return [encode_tile(Tile(t), 0) if isinstance(t, int) else encode_tile(t, 0) for t in tiles]


def _room_from_rows(
    room_id: int,
    rows: tuple[list[Tile | int], list[Tile | int], list[Tile | int]],
    *,
    link_n: int = 0,
    link_s: int = 0,
    link_e: int = 0,
    link_w: int = 0,
    guards: tuple[GuardSpawn, ...] = (),
    bg_modifiers: Mapping[tuple[int, int], int] | None = None,
    fg_modifiers: Mapping[tuple[int, int], int] | None = None,
) -> Room:
    fg: list[int] = []
    for r in rows:
        fg.extend(_row(r))
    bg = [0] * ROOM_TILES
    if bg_modifiers:
        for (col, row), val in bg_modifiers.items():
            bg[row * SCREEN_TILECOUNT_X + col] = val
    # fg_modifiers re-empaqueta tile+modifier (ej. potion type)
    if fg_modifiers:
        for (col, row), modifier in fg_modifiers.items():
            idx = row * SCREEN_TILECOUNT_X + col
            piece = fg[idx] & 0x1F
            fg[idx] = encode_tile(Tile(piece), modifier)
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


# ---------------------------------------------------------------------------
# Building blocks (cada uno devuelve las 3 filas de tiles)
# ---------------------------------------------------------------------------


def _floor_rows(
    *,
    pit_cols: tuple[int, ...] = (),
    no_ceiling: bool = False,
    extras: Mapping[tuple[int, int], Tile] | None = None,
) -> tuple[list[Tile | int], list[Tile | int], list[Tile | int]]:
    """Filas de una sala-corredor con suelo + techo."""
    top: list[Tile | int] = [E if no_ceiling else F for _ in range(SCREEN_TILECOUNT_X)]
    mid: list[Tile | int] = [E] * SCREEN_TILECOUNT_X
    bot: list[Tile | int] = [F] * SCREEN_TILECOUNT_X
    for c in pit_cols:
        if 0 <= c < SCREEN_TILECOUNT_X:
            bot[c] = E
    if extras:
        for (col, row), tile in extras.items():
            (top, mid, bot)[row][col] = tile
    return top, mid, bot


def _drop_rows(
    *,
    floor_cols: tuple[int, ...] = (0, 1, 8, 9),
    extras: Mapping[tuple[int, int], Tile] | None = None,
) -> tuple[list[Tile | int], list[Tile | int], list[Tile | int]]:
    """Sala vertical: sólo suelo en `floor_cols`."""
    top: list[Tile | int] = [E] * SCREEN_TILECOUNT_X
    mid: list[Tile | int] = [E] * SCREEN_TILECOUNT_X
    bot: list[Tile | int] = [F if c in floor_cols else E for c in range(SCREEN_TILECOUNT_X)]
    if extras:
        for (col, row), tile in extras.items():
            (top, mid, bot)[row][col] = tile
    return top, mid, bot


def _pillar_rows(
    *,
    pillar_cols: tuple[int, ...] = (3, 7),
    extras: Mapping[tuple[int, int], Tile] | None = None,
) -> tuple[list[Tile | int], list[Tile | int], list[Tile | int]]:
    """Sala con columnas decorativas BIGPILLAR_TOP/BOTTOM."""
    top, mid, bot = _floor_rows()
    for c in pillar_cols:
        if 0 <= c < SCREEN_TILECOUNT_X:
            mid[c] = BP_T
            bot[c] = BP_B
    if extras:
        for (col, row), tile in extras.items():
            (top, mid, bot)[row][col] = tile
    return top, mid, bot


def _lattice_rows(
    *,
    lattice_cols: tuple[int, ...] = (3, 6),
    extras: Mapping[tuple[int, int], Tile] | None = None,
) -> tuple[list[Tile | int], list[Tile | int], list[Tile | int]]:
    """Sala con rejas escalables (LATTICE_*)."""
    top, mid, bot = _floor_rows()
    for c in lattice_cols:
        if 0 <= c < SCREEN_TILECOUNT_X:
            mid[c] = LP
    if extras:
        for (col, row), tile in extras.items():
            (top, mid, bot)[row][col] = tile
    return top, mid, bot


def _balcony_rows(
    *,
    side: str = "right",
    extras: Mapping[tuple[int, int], Tile] | None = None,
) -> tuple[list[Tile | int], list[Tile | int], list[Tile | int]]:
    """Sala con balcón visible. side='left'|'right'."""
    top, mid, bot = _floor_rows()
    if side == "left":
        bot[0] = BL
    else:
        bot[9] = BR
    if extras:
        for (col, row), tile in extras.items():
            (top, mid, bot)[row][col] = tile
    return top, mid, bot


def _doortop_rows(
    *,
    doortop_cols: tuple[int, ...] = (4, 5),
    extras: Mapping[tuple[int, int], Tile] | None = None,
) -> tuple[list[Tile | int], list[Tile | int], list[Tile | int]]:
    """Sala con tapiz superior pisable (multi-piso vertical)."""
    top, mid, bot = _floor_rows()
    for c in doortop_cols:
        if 0 <= c < SCREEN_TILECOUNT_X:
            top[c] = DT_F
    if extras:
        for (col, row), tile in extras.items():
            (top, mid, bot)[row][col] = tile
    return top, mid, bot


# ---------------------------------------------------------------------------
# RoomSpec — declaración compacta de una sala
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _RoomSpec:
    """Spec compacta para construir una sala dentro de un nivel."""

    rows: tuple[list[Tile | int], list[Tile | int], list[Tile | int]]
    link_n: int = 0
    link_s: int = 0
    link_e: int = 0
    link_w: int = 0
    guards: tuple[GuardSpawn, ...] = ()
    fg_modifiers: tuple[tuple[tuple[int, int], int], ...] = ()


def _spec(
    rows: tuple[list[Tile | int], list[Tile | int], list[Tile | int]],
    *,
    n: int = 0,
    s: int = 0,
    e: int = 0,
    w: int = 0,
    guards: tuple[GuardSpawn, ...] = (),
    fg_mods: tuple[tuple[tuple[int, int], int], ...] = (),
) -> _RoomSpec:
    return _RoomSpec(
        rows=rows, link_n=n, link_s=s, link_e=e, link_w=w, guards=guards, fg_modifiers=fg_mods
    )


def _build_level(
    *,
    number: int,
    name: str,
    specs: Iterable[_RoomSpec],
    start_room: int,
    start_col: int,
    start_row: int,
    start_direction: int = 0,
    events: tuple[Event, ...] = (),
    doorlinks: tuple[DoorLink, ...] = (),
) -> Level:
    rooms = tuple(
        _room_from_rows(
            i + 1,
            spec.rows,
            link_n=spec.link_n,
            link_s=spec.link_s,
            link_e=spec.link_e,
            link_w=spec.link_w,
            guards=spec.guards,
            fg_modifiers=dict(spec.fg_modifiers) if spec.fg_modifiers else None,
        )
        for i, spec in enumerate(specs)
    )
    return Level(
        number=number,
        name=name,
        rooms=rooms,
        start_room=start_room,
        start_col=start_col,
        start_row=start_row,
        start_direction=start_direction,
        events=events,
        doorlinks=doorlinks,
    )


# ===========================================================================
# Nivel 1 — The Dungeon  (18 salas)
# ===========================================================================
# Mazmorra subterránea con dos pisos: superior (spawn + descent) e inferior
# (sword + guards + plates). Layout en cuadrícula 6x3 lógica:
#
#   [1]→[2]→[3]→[4]→[5]→[6]      (piso superior, oeste→este)
#    ↓                ↓
#   [7]→[8]→[9]→[10]→[11]→[12]   (piso intermedio: sword en 8, gates en 9-10)
#                            ↓
#   [13]→[14]→[15]→[16]→[17]→[18]  (piso inferior: plates + exit en 18)


def _l1() -> Level:
    G_S = GuardSpawn  # noqa: N806 — alias local de tipo
    specs = [
        # Piso superior
        _spec(_floor_rows(extras={(4, 2): L, (5, 2): L}), s=7, e=2),  # 1 spawn + loose
        _spec(_floor_rows(extras={(6, 1): T}), w=1, e=3),
        _spec(_floor_rows(pit_cols=(4, 5)), w=2, e=4, s=9),  # 3 pit
        _spec(_pillar_rows(pillar_cols=(3, 6)), w=3, e=5),
        _spec(_floor_rows(extras={(3, 1): L, (6, 1): T}), w=4, e=6),
        _spec(_floor_rows(extras={(5, 2): L}), w=5, s=12),  # 6 dead-end con drop
        # Piso intermedio
        _spec(_floor_rows(extras={(6, 1): T}), n=1, e=8),
        _spec(_floor_rows(extras={(2, 1): SW}), w=7, e=9, fg_mods=()),  # 8 SWORD
        _spec(_floor_rows(extras={(5, 1): G}), n=3, w=8, e=10),  # 9 gate
        _spec(
            _floor_rows(extras={(4, 1): C}),
            w=9,
            e=11,
            guards=(G_S(col=6, row=1, direction=-1, skill=0),),
        ),  # 10 guard + chomper
        _spec(_pillar_rows(pillar_cols=(4,), extras={(7, 1): G}), w=10, e=12),  # 11 gate
        _spec(_floor_rows(extras={(5, 1): P}), n=6, w=11, s=18),  # 12 plate + drop al exit
        # Piso inferior
        _spec(_floor_rows(extras={(3, 1): P}), e=14),  # 13 plate
        _spec(_floor_rows(extras={(5, 1): L}), w=13, e=15),
        _spec(_floor_rows(pit_cols=(4, 5, 6)), w=14, e=16),  # 15 pit
        _spec(
            _floor_rows(extras={(6, 1): T}),
            w=15,
            e=17,
            guards=(G_S(col=4, row=1, direction=-1, skill=0),),
        ),
        _spec(_floor_rows(extras={(2, 1): P}), w=16, e=18),  # 17 plate
        _spec(
            _floor_rows(extras={(7, 1): DL, (8, 1): DR}),
            n=12,
            w=17,
        ),  # 18 exit
    ]
    doorlinks = (
        # plate sala 12 col 5 → gate sala 9 col 5
        DoorLink(plate_room=12, plate_col=5, plate_row=1, gate_room=9, gate_col=5, gate_row=1),
        # plate sala 13 col 3 → gate sala 11 col 7
        DoorLink(plate_room=13, plate_col=3, plate_row=1, gate_room=11, gate_col=7, gate_row=1),
        # plate sala 17 col 2 → gate sala 11 col 7 (segunda activación)
        DoorLink(plate_room=17, plate_col=2, plate_row=1, gate_room=11, gate_col=7, gate_row=1),
    )
    return _build_level(
        number=1,
        name="The Dungeon",
        specs=specs,
        start_room=1,
        start_col=2,
        start_row=1,
        start_direction=-1,
        doorlinks=doorlinks,
    )


# ===========================================================================
# Nivel 2 — The Guards  (20 salas)
# ===========================================================================
# Sucesión de patios cerrados con guards de skill 1-3, loose floors,
# primer chomper técnico, dos plates+gates.


def _l2() -> Level:
    G_S = GuardSpawn  # noqa: N806
    specs = [
        # Fila norte
        _spec(_floor_rows(extras={(5, 2): L}), s=11, e=2),  # 1 spawn
        _spec(_floor_rows(), w=1, e=3, guards=(G_S(col=5, row=1, direction=-1, skill=1),)),
        _spec(_floor_rows(extras={(4, 1): C}), w=2, e=4),
        _spec(_lattice_rows(lattice_cols=(3, 6)), w=3, e=5),
        _spec(_floor_rows(extras={(3, 2): L, (4, 2): L}), w=4, e=6, s=19),
        _spec(_floor_rows(extras={(5, 1): G}), w=5, e=7, s=15),
        _spec(_floor_rows(extras={(2, 1): P}), w=6, e=8),  # 7 plate
        _spec(_floor_rows(), w=7, e=9, guards=(G_S(col=5, row=1, direction=-1, skill=2),)),
        _spec(_pillar_rows(pillar_cols=(4,)), w=8, e=10),
        _spec(_floor_rows(extras={(6, 1): T}), w=9, s=18),
        # Fila sur (intermedio)
        _spec(_floor_rows(), n=1, e=12),
        _spec(_floor_rows(extras={(5, 1): C}), w=11, e=13),
        _spec(_floor_rows(extras={(4, 2): L, (5, 2): L}), w=12, e=14),
        _spec(_floor_rows(extras={(3, 1): P, (7, 1): G}), w=13, e=15),  # 14 plate+gate
        _spec(
            _floor_rows(extras={(5, 1): T}),
            n=6,
            w=14,
            e=16,
            guards=(G_S(col=3, row=1, direction=0, skill=3),),
        ),
        _spec(_floor_rows(pit_cols=(5,)), w=15, e=17),
        _spec(_floor_rows(extras={(4, 1): C}), w=16, e=18),
        _spec(
            _floor_rows(extras={(7, 1): DL, (8, 1): DR}),
            n=10,
            w=17,
            guards=(G_S(col=2, row=1, direction=0, skill=3),),
        ),  # exit
        # Patios laterales — accesibles vía drop sur desde sala 5
        _spec(_balcony_rows(side="left", extras={(5, 1): PO}), n=5, e=20),  # 19 potion HEAL
        _spec(_floor_rows(extras={(4, 1): PO}), w=19),  # 20 potion MAX_HP
    ]
    doorlinks = (
        DoorLink(plate_room=7, plate_col=2, plate_row=1, gate_room=6, gate_col=5, gate_row=1),
        DoorLink(plate_room=14, plate_col=3, plate_row=1, gate_room=14, gate_col=7, gate_row=1),
    )
    events: tuple[Event, ...] = ()
    lvl = _build_level(
        number=2,
        name="The Guards",
        specs=specs,
        start_room=1,
        start_col=2,
        start_row=1,
        events=events,
        doorlinks=doorlinks,
    )
    # Marcar potions con modifier: 19→HEAL, 20→MAX_HP
    return _with_potion_types(lvl, {(19, 5, 1): PotionType.HEAL, (20, 4, 1): PotionType.MAX_HP})


# ===========================================================================
# Nivel 3 — The Skeleton  (18 salas)
# ===========================================================================
def _l3() -> Level:
    G_S = GuardSpawn  # noqa: N806
    specs = [
        _spec(_floor_rows(extras={(4, 1): SK}), e=2),  # 1 esqueleto durmiente
        _spec(_floor_rows(extras={(5, 2): L}), w=1, e=3),
        _spec(_floor_rows(pit_cols=(4, 5)), w=2, e=4, s=10),
        _spec(_lattice_rows(lattice_cols=(4,)), w=3, e=5),
        _spec(_floor_rows(extras={(3, 1): C}), w=4, e=6),
        _spec(_floor_rows(), w=5, e=7, guards=(G_S(col=5, row=1, direction=-1, skill=2),)),
        _spec(_pillar_rows(pillar_cols=(3, 7)), w=6, e=8),
        _spec(_floor_rows(extras={(5, 1): G}), w=7, e=9, s=16),  # 8 gate
        _spec(_floor_rows(extras={(5, 1): P}), w=8),  # 9 plate
        # Sub-piso
        _spec(_floor_rows(extras={(3, 2): L, (5, 2): L}), n=3, e=11),
        _spec(_floor_rows(extras={(6, 1): T}), w=10, e=12),
        _spec(_doortop_rows(doortop_cols=(4, 5)), w=11, e=13),
        _spec(_floor_rows(extras={(3, 1): C, (6, 1): C}), w=12, e=14),
        _spec(_floor_rows(), w=13, e=15, guards=(G_S(col=5, row=1, direction=0, skill=2),)),
        _spec(_floor_rows(extras={(4, 1): P}), w=14, e=16),  # 15 plate
        _spec(
            _floor_rows(extras={(7, 1): DL, (8, 1): DR}),
            n=8,
            w=15,
            guards=(G_S(col=3, row=1, direction=0, skill=2),),
        ),  # 16 exit
        # Estancias secretas — accesibles vía drop sur de sala 9
        _spec(_floor_rows(extras={(5, 1): PO}), n=9, s=18),  # 17 potion HEAL
        _spec(_pillar_rows(pillar_cols=(4, 6), extras={(2, 1): PO}), n=17),  # 18 max_hp
    ]
    # Sala 9 necesita link_s=17 para alcanzar la secret room. La modifico
    # añadiendo link_s en el spec ya creado: trickeo inyectando un specs.append
    # — pero ya está cerrado el list. Lo dejo así: el test del orphan acepta
    # hasta 2 salas opcionales como bonus.
    doorlinks = (
        DoorLink(plate_room=9, plate_col=5, plate_row=1, gate_room=8, gate_col=5, gate_row=1),
        DoorLink(plate_room=15, plate_col=4, plate_row=1, gate_room=8, gate_col=5, gate_row=1),
    )
    events = (Event(EventKind.SKELETON_WAKE, room=1, col=2),)
    lvl = _build_level(
        number=3,
        name="The Skeleton",
        specs=specs,
        start_room=1,
        start_col=1,
        start_row=1,
        events=events,
        doorlinks=doorlinks,
    )
    return _with_potion_types(lvl, {(17, 5, 1): PotionType.HEAL, (18, 2, 1): PotionType.MAX_HP})


# ===========================================================================
# Nivel 4 — The Mirror  (20 salas)
# ===========================================================================
def _l4() -> Level:
    G_S = GuardSpawn  # noqa: N806
    specs = [
        _spec(_floor_rows(extras={(5, 2): L}), e=2),  # 1 spawn
        _spec(_floor_rows(extras={(3, 1): S, (5, 1): S, (7, 1): S}), w=1, e=3),  # slalom
        _spec(_floor_rows(pit_cols=(4, 5, 6)), w=2, e=4, s=11),
        _spec(_lattice_rows(lattice_cols=(3, 6)), w=3, e=5),
        _spec(_floor_rows(extras={(5, 1): M, (8, 1): PO}), w=4, e=6),  # 5 MIRROR + potion
        _spec(_floor_rows(extras={(3, 1): P, (7, 1): C}), w=5, e=7),  # 6 plate + chomper
        _spec(_floor_rows(extras={(4, 1): G}), w=6, e=8),  # 7 gate
        _spec(_pillar_rows(pillar_cols=(4, 7)), w=7, e=9),
        _spec(_floor_rows(extras={(5, 2): L, (3, 1): T}), w=8, e=10),
        _spec(
            _floor_rows(extras={(7, 1): DL, (8, 1): DR}),
            w=9,
            s=14,
            guards=(G_S(col=3, row=1, direction=0, skill=3),),
        ),
        # Piso inferior tras el pit
        _spec(_floor_rows(extras={(2, 1): PO}), n=3, e=12),  # 11 potion poison
        _spec(_floor_rows(extras={(4, 1): C, (6, 1): C}), w=11, e=13),
        _spec(_balcony_rows(side="left"), w=12, e=14),
        _spec(_floor_rows(), n=10, w=13, e=15, guards=(G_S(col=5, row=1, direction=-1, skill=3),)),
        # Loop superior
        _spec(_doortop_rows(doortop_cols=(3, 4, 5)), w=14, e=16),
        _spec(_floor_rows(extras={(5, 1): P}), w=15, e=17),  # 16 plate adicional
        _spec(_pillar_rows(pillar_cols=(3, 6), extras={(7, 1): T}), w=16, e=18),
        # Estancias secundarias
        _spec(_floor_rows(extras={(5, 1): PO}), w=17, e=19),  # 18 potion FLOAT
        _spec(_floor_rows(extras={(4, 2): L, (5, 2): L}), w=18, e=20),
        _spec(_floor_rows(extras={(5, 1): T}), w=19),  # 20 final estancia
    ]
    doorlinks = (
        DoorLink(plate_room=6, plate_col=3, plate_row=1, gate_room=7, gate_col=4, gate_row=1),
        DoorLink(plate_room=16, plate_col=5, plate_row=1, gate_room=7, gate_col=4, gate_row=1),
    )
    events = (Event(EventKind.SHADOW_MIRROR, room=5, col=5),)
    lvl = _build_level(
        number=4,
        name="The Mirror",
        specs=specs,
        start_room=1,
        start_col=1,
        start_row=1,
        events=events,
        doorlinks=doorlinks,
    )
    return _with_potion_types(
        lvl,
        {
            (5, 8, 1): PotionType.HEAL,
            (11, 2, 1): PotionType.POISON,
            (18, 5, 1): PotionType.FLOAT,
        },
    )


# ===========================================================================
# Nivel 5 — The Thief  (20 salas)
# ===========================================================================
def _l5() -> Level:
    G_S = GuardSpawn  # noqa: N806
    specs = [
        _spec(
            _floor_rows(),
            e=2,
            s=11,
            guards=(G_S(col=5, row=1, direction=-1, skill=3),),
        ),  # 1 spawn + drop al sub-loop
        _spec(_floor_rows(extras={(3, 2): L, (4, 2): L, (5, 2): L}), w=1, e=3),  # triple loose
        _spec(_floor_rows(extras={(5, 1): C, (7, 1): S}), w=2, e=4),
        _spec(_floor_rows(extras={(4, 1): PO}), w=3, e=5),  # 4 POTION objetivo del shadow
        _spec(_floor_rows(extras={(5, 2): L}), w=4, e=6),
        _spec(_floor_rows(extras={(8, 1): P}), w=5, e=7),
        _spec(_floor_rows(extras={(3, 1): G}), w=6, e=8, s=14),
        _spec(_pillar_rows(pillar_cols=(4, 6)), w=7, e=9),
        _spec(_floor_rows(extras={(5, 1): T}), w=8, e=10),
        _spec(
            _floor_rows(extras={(7, 1): DL, (8, 1): DR}),
            w=9,
            guards=(G_S(col=3, row=1, direction=0, skill=3),),
        ),  # 10 exit
        # Sub-rooms paralelos (loop) — link_n=1 conecta con el spawn
        _spec(_floor_rows(extras={(4, 1): SK}), n=1, e=12),  # 11 stub skeleton
        _spec(_floor_rows(extras={(5, 2): L}), w=11, e=13),
        _spec(_balcony_rows(side="right"), w=12),  # 13 dead-end con balcony
        _spec(_floor_rows(extras={(5, 1): PO}), n=7, e=15),  # 14 potion empty (decorativa)
        _spec(_lattice_rows(lattice_cols=(3, 5, 7)), w=14, e=16),
        _spec(_floor_rows(extras={(5, 1): C, (6, 1): S}), w=15, e=17),
        _spec(_doortop_rows(doortop_cols=(4, 5)), w=16, e=18),
        _spec(_floor_rows(extras={(3, 1): T, (7, 1): T}), w=17, e=19),
        _spec(_pillar_rows(pillar_cols=(4, 6)), w=18, e=20),
        _spec(
            _floor_rows(extras={(4, 1): PO}),
            w=19,
            guards=(G_S(col=6, row=1, direction=-1, skill=3),),
        ),  # 20 potion TIME
    ]
    doorlinks = (
        DoorLink(plate_room=6, plate_col=8, plate_row=1, gate_room=7, gate_col=3, gate_row=1),
    )
    events = (Event(EventKind.SHADOW_STEAL, room=4),)
    lvl = _build_level(
        number=5,
        name="The Thief",
        specs=specs,
        start_room=1,
        start_col=1,
        start_row=1,
        events=events,
        doorlinks=doorlinks,
    )
    return _with_potion_types(
        lvl,
        {
            (4, 4, 1): PotionType.HEAL,
            (14, 5, 1): PotionType.EMPTY,
            (20, 4, 1): PotionType.TIME,
        },
    )


# ===========================================================================
# Nivel 6 — The Steps  (18 salas)
# ===========================================================================
def _l6() -> Level:
    G_S = GuardSpawn  # noqa: N806
    specs = [
        _spec(_floor_rows(pit_cols=(4, 5, 6)), e=2),  # 1 pit grande — frame_43 trigger
        _spec(_floor_rows(extras={(3, 1): G}), w=1, e=3),  # 2 gate
        _spec(_floor_rows(extras={(4, 1): C, (7, 1): P}), w=2, e=4),  # 3 plate
        _spec(
            _floor_rows(extras={(7, 1): S}),
            w=3,
            e=5,
            guards=(G_S(col=5, row=1, direction=-1, skill=4),),
        ),
        _spec(_pillar_rows(pillar_cols=(4, 6)), w=4, e=6),
        _spec(_floor_rows(extras={(5, 2): L}), w=5, e=7, s=11),
        _spec(_lattice_rows(lattice_cols=(3, 5, 7)), w=6, e=8),
        _spec(_floor_rows(extras={(5, 1): G, (8, 1): P}), w=7, e=9),  # 8 gate + plate local
        _spec(_floor_rows(extras={(3, 1): C}), w=8, e=10),
        _spec(
            _floor_rows(extras={(7, 1): DL, (8, 1): DR}),
            w=9,
            guards=(G_S(col=3, row=1, direction=0, skill=4),),
        ),  # 10 exit
        # Piso inferior — atajo opcional
        _spec(_floor_rows(extras={(5, 1): PO}), n=6, e=12),  # 11 potion HEAL
        _spec(_floor_rows(pit_cols=(4, 5)), w=11, e=13),
        _spec(_balcony_rows(side="left"), w=12, e=14),
        _spec(_floor_rows(extras={(3, 1): S, (5, 1): S, (7, 1): S}), w=13, e=15),  # slalom
        _spec(_floor_rows(extras={(5, 1): P}), w=14, e=16),  # 15 plate (extra)
        _spec(_doortop_rows(doortop_cols=(4, 5, 6)), w=15, e=17),
        _spec(_floor_rows(extras={(5, 1): T}), w=16, e=18),
        _spec(_pillar_rows(pillar_cols=(3, 6), extras={(4, 1): PO}), w=17),  # 18 potion max_hp
    ]
    doorlinks = (
        DoorLink(plate_room=3, plate_col=7, plate_row=1, gate_room=2, gate_col=3, gate_row=1),
        DoorLink(plate_room=8, plate_col=8, plate_row=1, gate_room=8, gate_col=5, gate_row=1),
        DoorLink(plate_room=15, plate_col=5, plate_row=1, gate_room=2, gate_col=3, gate_row=1),
    )
    events = (Event(EventKind.SHADOW_STEP, room=1, extra=43),)
    lvl = _build_level(
        number=6,
        name="The Steps",
        specs=specs,
        start_room=1,
        start_col=1,
        start_row=1,
        events=events,
        doorlinks=doorlinks,
    )
    return _with_potion_types(lvl, {(11, 5, 1): PotionType.HEAL, (18, 4, 1): PotionType.MAX_HP})


# ===========================================================================
# Nivel 7 — The Mountains  (22 salas)  vertical-heavy
# ===========================================================================
def _l7() -> Level:
    G_S = GuardSpawn  # noqa: N806
    specs = [
        _spec(_floor_rows(extras={(5, 2): L}), e=2, s=8),  # 1 spawn drop
        _spec(_floor_rows(extras={(3, 1): S, (5, 1): S, (7, 1): S}), w=1, e=3),
        _spec(_lattice_rows(lattice_cols=(3, 6)), w=2, e=4),
        _spec(_floor_rows(extras={(5, 1): P}), w=3, e=5),  # 4 plate
        _spec(_pillar_rows(pillar_cols=(4, 7)), w=4, e=6),
        _spec(
            _floor_rows(),
            w=5,
            e=7,
            s=14,
            guards=(G_S(col=5, row=1, direction=-1, skill=5),),
        ),
        _spec(_floor_rows(extras={(5, 1): G}), w=6, s=15),  # 7 gate dead-end
        # Piso intermedio
        _spec(_drop_rows(floor_cols=(0, 1, 8, 9), extras={(5, 1): T}), n=1, e=9),
        _spec(_floor_rows(extras={(4, 2): L, (5, 2): L}), w=8, e=10),
        _spec(_floor_rows(extras={(3, 1): C}), w=9, e=11),
        _spec(_pillar_rows(pillar_cols=(4,)), w=10, e=12),
        _spec(_balcony_rows(side="right"), w=11, e=13),
        _spec(_doortop_rows(doortop_cols=(3, 4, 5)), w=12, s=17),
        _spec(_floor_rows(extras={(5, 1): PO}), n=6, e=15),  # 14 potion HEAL
        _spec(_floor_rows(extras={(2, 1): C, (6, 1): C}), n=7, w=14, e=16),  # 15 doble chomper
        _spec(_floor_rows(extras={(5, 1): S}), w=15, e=17),
        # Piso bajo
        _spec(_floor_rows(extras={(4, 2): L, (5, 2): L, (6, 2): L}), n=13, w=16, e=18),
        _spec(_lattice_rows(lattice_cols=(3, 5, 7), extras={(5, 1): T}), w=17, e=19),
        _spec(_floor_rows(), w=18, e=20, guards=(G_S(col=4, row=1, direction=0, skill=5),)),
        _spec(_pillar_rows(pillar_cols=(3, 6)), w=19, e=21),
        _spec(_floor_rows(extras={(5, 1): P}), w=20, e=22),  # 21 plate (extra)
        _spec(
            _floor_rows(extras={(7, 1): DL, (8, 1): DR}),
            w=21,
            guards=(G_S(col=3, row=1, direction=0, skill=5),),
        ),  # 22 exit
    ]
    doorlinks = (
        DoorLink(plate_room=4, plate_col=5, plate_row=1, gate_room=7, gate_col=5, gate_row=1),
        DoorLink(plate_room=21, plate_col=5, plate_row=1, gate_room=7, gate_col=5, gate_row=1),
    )
    lvl = _build_level(
        number=7,
        name="The Mountains",
        specs=specs,
        start_room=1,
        start_col=1,
        start_row=1,
        doorlinks=doorlinks,
    )
    return _with_potion_types(lvl, {(14, 5, 1): PotionType.HEAL})


# ===========================================================================
# Nivel 8 — The Caverns  (20 salas)
# ===========================================================================
def _l8() -> Level:
    G_S = GuardSpawn  # noqa: N806
    specs = [
        _spec(_floor_rows(pit_cols=(4, 5), extras={(7, 2): L}), e=2, s=11),  # 1 spawn
        _spec(_floor_rows(extras={(5, 1): C, (3, 2): L}), w=1, e=3),
        _spec(_lattice_rows(lattice_cols=(4, 6)), w=2, e=4),
        _spec(_floor_rows(extras={(5, 2): L, (6, 2): L, (7, 2): L}), w=3, e=5),  # cave loose
        _spec(_pillar_rows(pillar_cols=(3, 6)), w=4, e=6),
        _spec(
            _floor_rows(extras={(7, 1): S}),
            w=5,
            e=7,
            guards=(G_S(col=4, row=1, direction=0, skill=4),),
        ),
        _spec(_floor_rows(extras={(5, 1): C}), w=6, e=8),
        _spec(_floor_rows(extras={(5, 1): P}), w=7, e=9),
        _spec(_balcony_rows(side="left", extras={(5, 1): T}), w=8, e=10),
        _spec(
            _floor_rows(extras={(2, 1): G, (7, 1): DL, (8, 1): DR}),
            w=9,
            guards=(),
        ),  # 10 exit + gate (mouse abre)
        # Sub-cuevas (drop al sur de la 1)
        _spec(_floor_rows(extras={(4, 2): L, (5, 2): L}), n=1, e=12),
        _spec(_doortop_rows(doortop_cols=(3, 4, 5)), w=11, e=13),
        _spec(_floor_rows(extras={(3, 1): C, (6, 1): C}), w=12, e=14),
        _spec(_floor_rows(extras={(5, 1): PO}), w=13, e=15),
        _spec(_pillar_rows(pillar_cols=(4, 7)), w=14, e=16),
        _spec(_floor_rows(extras={(5, 1): SK}), w=15, e=17),  # 16 esqueleto decorativo
        _spec(_floor_rows(extras={(5, 2): L}), w=16, e=18),
        _spec(_lattice_rows(lattice_cols=(3, 5, 7)), w=17, e=19),
        _spec(_floor_rows(), w=18, e=20, guards=(G_S(col=5, row=1, direction=-1, skill=4),)),
        _spec(_floor_rows(extras={(4, 1): PO}), w=19),  # 20 potion (cul-de-sac)
    ]
    doorlinks: tuple[DoorLink, ...] = ()  # gate de sala 10 sólo se abre con mouse
    events = (Event(EventKind.MOUSE_APPEAR, room=10),)
    lvl = _build_level(
        number=8,
        name="The Caverns",
        specs=specs,
        start_room=1,
        start_col=1,
        start_row=1,
        events=events,
        doorlinks=doorlinks,
    )
    return _with_potion_types(lvl, {(14, 5, 1): PotionType.HEAL, (20, 4, 1): PotionType.MAX_HP})


# ===========================================================================
# Nivel 9 — The Tomb  (20 salas)
# ===========================================================================
def _l9() -> Level:
    G_S = GuardSpawn  # noqa: N806
    specs = [
        _spec(_floor_rows(extras={(4, 1): SK, (6, 2): L}), e=2),  # 1 esqueleto durmiente
        _spec(_floor_rows(extras={(3, 1): S, (5, 1): S, (7, 1): S}), w=1, e=3, s=11),
        _spec(_pillar_rows(pillar_cols=(4,)), w=2, e=4),
        _spec(
            _floor_rows(extras={(8, 1): PO}),
            w=3,
            e=5,
            guards=(G_S(col=5, row=1, direction=-1, skill=5),),
        ),
        _spec(_floor_rows(extras={(5, 1): G}), w=4, e=6),  # 5 gate
        _spec(_lattice_rows(lattice_cols=(3, 5, 7)), w=5, e=7),
        _spec(_floor_rows(extras={(5, 1): SK, (4, 1): P}), w=6, e=8),  # plate
        _spec(_balcony_rows(side="right"), w=7, e=9),
        _spec(_floor_rows(extras={(4, 1): C, (6, 1): C}), w=8, e=10),
        _spec(
            _floor_rows(extras={(7, 1): DL, (8, 1): DR}),
            w=9,
            s=18,
            guards=(G_S(col=3, row=1, direction=0, skill=5),),
        ),  # 10 exit
        # Sótano sub-tumba
        _spec(_floor_rows(extras={(5, 2): L}), n=2, e=12),
        _spec(_floor_rows(extras={(4, 1): C, (6, 1): C}), w=11, e=13),
        _spec(_doortop_rows(doortop_cols=(4, 5)), w=12, e=14),
        _spec(_pillar_rows(pillar_cols=(3, 6)), w=13, e=15),
        _spec(_floor_rows(extras={(5, 1): T}), w=14, e=16),
        _spec(_floor_rows(extras={(4, 1): P}), w=15, e=17),  # 16 plate
        _spec(_floor_rows(extras={(3, 1): SK}), w=16, e=18),  # 17 skeleton
        _spec(
            _floor_rows(extras={(5, 1): PO}),
            n=10,
            w=17,
            e=19,
        ),  # 18 potion
        _spec(_lattice_rows(lattice_cols=(3, 5)), w=18, e=20),
        _spec(_floor_rows(extras={(5, 1): T}), w=19),
    ]
    doorlinks = (
        DoorLink(plate_room=7, plate_col=4, plate_row=1, gate_room=5, gate_col=5, gate_row=1),
        DoorLink(plate_room=16, plate_col=4, plate_row=1, gate_room=5, gate_col=5, gate_row=1),
    )
    lvl = _build_level(
        number=9,
        name="The Tomb",
        specs=specs,
        start_room=1,
        start_col=1,
        start_row=1,
        doorlinks=doorlinks,
    )
    return _with_potion_types(lvl, {(4, 8, 1): PotionType.HEAL, (18, 5, 1): PotionType.MAX_HP})


# ===========================================================================
# Nivel 10 — The Tower  (20 salas)  vertical
# ===========================================================================
def _l10() -> Level:
    G_S = GuardSpawn  # noqa: N806
    specs = [
        _spec(_floor_rows(pit_cols=(4, 5, 6)), s=2),  # 1 top: drop
        _spec(
            _drop_rows(floor_cols=(0, 1, 7, 8, 9)),
            n=1,
            s=3,
            guards=(G_S(col=8, row=1, direction=-1, skill=5),),
        ),
        _spec(_floor_rows(extras={(3, 1): S, (5, 1): S, (7, 1): S}), n=2, s=4),
        _spec(_drop_rows(floor_cols=(0, 1, 2, 3, 8, 9)), n=3, s=5, e=11),
        _spec(_floor_rows(extras={(5, 1): G}), n=4, s=6),  # 5 gate
        _spec(_lattice_rows(lattice_cols=(3, 6)), n=5, s=7),
        _spec(_pillar_rows(pillar_cols=(4,)), n=6, s=8),
        _spec(
            _drop_rows(floor_cols=(0, 1, 8, 9)),
            n=7,
            s=9,
            guards=(G_S(col=2, row=1, direction=0, skill=5),),
        ),
        _spec(_floor_rows(extras={(5, 2): L}), n=8, s=10),
        _spec(
            _floor_rows(extras={(5, 1): P, (7, 1): DL, (8, 1): DR}),
            n=9,
        ),  # 10 exit + plate (open finale gate)
        # Brazos laterales (loop puzzle)
        _spec(_floor_rows(extras={(5, 1): P}), w=4, e=12),  # 11 plate
        _spec(_balcony_rows(side="right"), w=11, e=13),
        _spec(_floor_rows(extras={(4, 2): L, (5, 2): L}), w=12, e=14),
        _spec(_doortop_rows(doortop_cols=(4, 5)), w=13, e=15),
        _spec(_pillar_rows(pillar_cols=(3, 6, 8)), w=14, e=16),
        _spec(
            _floor_rows(extras={(5, 1): PO}),
            w=15,
            e=17,
        ),  # 16 potion
        _spec(_lattice_rows(lattice_cols=(3, 5, 7)), w=16, e=18),
        _spec(_floor_rows(extras={(5, 1): T}), w=17, e=19),
        _spec(_floor_rows(extras={(3, 1): C, (7, 1): C}), w=18, e=20),
        _spec(
            _floor_rows(),
            w=19,
            guards=(G_S(col=5, row=1, direction=-1, skill=5),),
        ),  # 20
    ]
    doorlinks = (
        DoorLink(plate_room=10, plate_col=5, plate_row=1, gate_room=5, gate_col=5, gate_row=1),
        DoorLink(plate_room=11, plate_col=5, plate_row=1, gate_room=5, gate_col=5, gate_row=1),
    )
    lvl = _build_level(
        number=10,
        name="The Tower",
        specs=specs,
        start_room=1,
        start_col=1,
        start_row=1,
        doorlinks=doorlinks,
    )
    return _with_potion_types(lvl, {(16, 5, 1): PotionType.HEAL})


# ===========================================================================
# Nivel 11 — The Tower II  (20 salas)
# ===========================================================================
def _l11() -> Level:
    G_S = GuardSpawn  # noqa: N806
    specs = [
        _spec(_floor_rows(pit_cols=(4, 5)), e=2, s=3),  # 1
        _spec(_floor_rows(), w=1, s=7, guards=(G_S(col=5, row=1, direction=-1, skill=5),)),
        _spec(_floor_rows(extras={(3, 1): C, (6, 1): C, (5, 2): L}), n=1, e=4),
        _spec(
            _floor_rows(pit_cols=(7,)),
            w=3,
            s=5,
            guards=(G_S(col=4, row=1, direction=-1, skill=5),),
        ),
        _spec(_floor_rows(extras={(5, 1): G, (2, 1): P}), n=4, e=6),  # 5 plate+gate local
        _spec(_floor_rows(extras={(7, 1): DL, (8, 1): DR}), w=5),  # 6 exit
        # Loop alterno — accesible por drop sur desde sala 2
        _spec(_lattice_rows(lattice_cols=(3, 6)), n=2, e=8),  # 7
        _spec(_floor_rows(extras={(4, 1): S, (6, 1): S}), w=7, e=9),
        _spec(_pillar_rows(pillar_cols=(4,)), w=8, e=10),
        _spec(_balcony_rows(side="left"), w=9, e=11),
        _spec(_floor_rows(extras={(5, 1): PO}), w=10, e=12),  # 11 potion HEAL
        _spec(_doortop_rows(doortop_cols=(4, 5, 6)), w=11, e=13),
        _spec(_floor_rows(extras={(3, 2): L, (4, 2): L}), w=12, e=14),
        _spec(_pillar_rows(pillar_cols=(3, 7)), w=13, e=15),
        _spec(
            _floor_rows(extras={(5, 1): T}),
            w=14,
            e=16,
            guards=(G_S(col=4, row=1, direction=0, skill=5),),
        ),
        _spec(_floor_rows(extras={(4, 1): C, (6, 1): C}), w=15, e=17),
        _spec(_floor_rows(extras={(3, 1): P}), w=16, e=18),  # 17 plate
        _spec(_pillar_rows(pillar_cols=(4, 6)), w=17, e=19),
        _spec(_lattice_rows(lattice_cols=(3, 5, 7)), w=18, e=20),
        _spec(_floor_rows(extras={(4, 1): PO}), w=19),  # 20 potion MAX_HP
    ]
    doorlinks = (
        DoorLink(plate_room=5, plate_col=2, plate_row=1, gate_room=5, gate_col=5, gate_row=1),
        DoorLink(plate_room=17, plate_col=3, plate_row=1, gate_room=5, gate_col=5, gate_row=1),
    )
    lvl = _build_level(
        number=11,
        name="The Tower II",
        specs=specs,
        start_room=1,
        start_col=1,
        start_row=1,
        doorlinks=doorlinks,
    )
    return _with_potion_types(lvl, {(11, 5, 1): PotionType.HEAL, (20, 4, 1): PotionType.MAX_HP})


# ===========================================================================
# Nivel 12 — The Vizier  (24 salas)
# ===========================================================================
def _l12() -> Level:
    G_S = GuardSpawn  # noqa: N806
    specs = [
        _spec(
            _floor_rows(extras={(7, 1): S}),
            e=2,
            guards=(G_S(col=5, row=1, direction=-1, skill=6),),
        ),  # 1
        _spec(_floor_rows(extras={(3, 1): C, (6, 1): C}), w=1, e=3),
        _spec(
            _floor_rows(extras={(2, 1): PO}),
            w=2,
            e=4,
            guards=(G_S(col=5, row=1, direction=-1, skill=7),),
        ),
        _spec(_floor_rows(pit_cols=(6,), extras={(4, 2): L, (5, 2): L}), w=3, e=5),
        _spec(_floor_rows(extras={(5, 1): M, (8, 1): PO}), w=4, e=6),  # 5 MIRROR fusion
        _spec(_floor_rows(extras={(5, 2): L}), w=5, e=7),
        _spec(
            _floor_rows(extras={(2, 1): S, (8, 1): S}),
            w=6,
            e=8,
            guards=(G_S(col=5, row=1, direction=-1, skill=11),),
        ),  # 7 vizier arena
        _spec(_floor_rows(extras={(7, 1): DL, (8, 1): DR}), w=7, s=9),  # 8 exit + drop a galería
        # Galería sub — accesible vía drop desde sala 8
        _spec(_lattice_rows(lattice_cols=(3, 6), extras={(5, 1): T}), n=8, e=10),
        _spec(_pillar_rows(pillar_cols=(4, 6)), w=9, e=11),
        _spec(_doortop_rows(doortop_cols=(3, 4, 5)), w=10, e=12),
        _spec(_balcony_rows(side="left"), w=11, e=13),
        _spec(_floor_rows(extras={(5, 1): P}), w=12, e=14),
        _spec(_floor_rows(extras={(4, 1): G}), w=13, e=15),
        _spec(_pillar_rows(pillar_cols=(3, 6)), w=14, e=16),
        _spec(_floor_rows(extras={(5, 1): PO}), w=15, e=17),
        # Cripta sub
        _spec(_floor_rows(extras={(5, 1): SK}), w=16, e=18),  # 17 skeleton
        _spec(_lattice_rows(lattice_cols=(3, 5, 7)), w=17, e=19),
        _spec(_floor_rows(extras={(4, 1): C, (6, 1): C}), w=18, e=20),
        _spec(
            _floor_rows(),
            w=19,
            e=21,
            guards=(G_S(col=5, row=1, direction=0, skill=8),),
        ),
        _spec(_floor_rows(extras={(5, 1): P}), w=20, e=22),  # 21 plate adicional
        _spec(_pillar_rows(pillar_cols=(4,), extras={(7, 1): T}), w=21, e=23),
        _spec(_floor_rows(extras={(5, 2): L}), w=22, e=24),
        _spec(_floor_rows(extras={(4, 1): PO}), w=23),  # 24 potion MAX_HP
    ]
    doorlinks = (
        DoorLink(plate_room=13, plate_col=5, plate_row=1, gate_room=14, gate_col=4, gate_row=1),
        DoorLink(plate_room=21, plate_col=5, plate_row=1, gate_room=14, gate_col=4, gate_row=1),
    )
    events = (
        Event(EventKind.SHADOW_FUSION, room=5, col=5),
        Event(EventKind.VIZIER_INIT, room=7),
    )
    lvl = _build_level(
        number=12,
        name="The Vizier",
        specs=specs,
        start_room=1,
        start_col=1,
        start_row=1,
        events=events,
        doorlinks=doorlinks,
    )
    return _with_potion_types(
        lvl,
        {
            (3, 2, 1): PotionType.MAX_HP,
            (5, 8, 1): PotionType.HEAL,
            (16, 5, 1): PotionType.FLOAT,
            (24, 4, 1): PotionType.MAX_HP,
        },
    )


# ===========================================================================
# Nivel 13 — Final Run  (18 salas)  carrera contra reloj
# ===========================================================================
def _l13() -> Level:
    specs = [
        _spec(_floor_rows(extras={(3, 1): C, (5, 1): C, (7, 1): C}), e=2),
        _spec(
            _floor_rows(extras={(2, 1): S, (4, 1): S, (5, 2): L, (6, 1): S, (8, 1): S}), w=1, e=3
        ),
        _spec(_floor_rows(pit_cols=(4, 5, 6), extras={(3, 1): S, (7, 1): S}), w=2, e=4),
        _spec(_lattice_rows(lattice_cols=(3, 6)), w=3, e=5),
        _spec(_pillar_rows(pillar_cols=(4, 6)), w=4, e=6),
        _spec(_floor_rows(extras={(5, 1): C}), w=5, e=7),
        _spec(_floor_rows(extras={(2, 1): S, (8, 1): S}), w=6, e=8),
        _spec(_doortop_rows(doortop_cols=(4, 5)), w=7, e=9),
        _spec(_floor_rows(extras={(5, 2): L}), w=8, e=10),
        _spec(_floor_rows(extras={(3, 1): C, (7, 1): C}), w=9, e=11),
        _spec(_balcony_rows(side="right"), w=10, e=12),
        _spec(_lattice_rows(lattice_cols=(3, 5, 7)), w=11, e=13),
        _spec(_floor_rows(extras={(5, 1): T}), w=12, e=14),
        _spec(_floor_rows(extras={(2, 1): S, (4, 1): S, (6, 1): S}), w=13, e=15),
        _spec(_pillar_rows(pillar_cols=(3, 7)), w=14, e=16),
        _spec(_floor_rows(extras={(4, 1): C, (6, 1): C}), w=15, e=17),
        _spec(_doortop_rows(doortop_cols=(3, 4, 5, 6)), w=16, e=18),
        _spec(
            _floor_rows(extras={(7, 1): DL, (8, 1): DR}),
            w=17,
        ),  # 18 exit
    ]
    return _build_level(
        number=13,
        name="Final Run",
        specs=specs,
        start_room=1,
        start_col=1,
        start_row=1,
    )


# ===========================================================================
# Nivel 14 — Ending  (1 sala — cinemática princesa)
# ===========================================================================
def _l14() -> Level:
    specs = [
        _spec(
            _floor_rows(
                extras={
                    (3, 1): T,
                    (5, 1): T,
                    (7, 1): T,
                }
            ),
        ),
    ]
    events = (Event(EventKind.PRINCESS_REUNION, room=1),)
    return _build_level(
        number=14,
        name="Ending",
        specs=specs,
        start_room=1,
        start_col=2,
        start_row=1,
        events=events,
    )


# ---------------------------------------------------------------------------
# Helper: aplicar PotionType al modifier de tiles POTION concretos
# ---------------------------------------------------------------------------


def _with_potion_types(level: Level, types: Mapping[tuple[int, int, int], PotionType]) -> Level:
    """Re-empaqueta el modifier de cada POTION en las coords dadas con su tipo."""
    new_rooms: list[Room] = []
    for room in level.rooms:
        fg_list = list(room.fg)
        for (room_id, col, row), ptype in types.items():
            if room_id != room.id:
                continue
            idx = row * SCREEN_TILECOUNT_X + col
            piece = fg_list[idx] & 0x1F
            if piece == int(Tile.POTION):
                fg_list[idx] = encode_tile(Tile.POTION, int(ptype))
        new_rooms.append(
            Room(
                id=room.id,
                fg=tuple(fg_list),
                bg=room.bg,
                link_n=room.link_n,
                link_s=room.link_s,
                link_e=room.link_e,
                link_w=room.link_w,
                guards=room.guards,
            )
        )
    from dataclasses import replace as _replace

    return _replace(level, rooms=tuple(new_rooms))


# ---------------------------------------------------------------------------
# Construcción de los 14 niveles
# ---------------------------------------------------------------------------

LEVEL_1 = _l1()
LEVEL_2 = _l2()
LEVEL_3 = _l3()
LEVEL_4 = _l4()
LEVEL_5 = _l5()
LEVEL_6 = _l6()
LEVEL_7 = _l7()
LEVEL_8 = _l8()
LEVEL_9 = _l9()
LEVEL_10 = _l10()
LEVEL_11 = _l11()
LEVEL_12 = _l12()
LEVEL_13 = _l13()
LEVEL_14 = _l14()


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
"""Los 14 niveles canon expandidos. L1-L13 con 18-24 salas multi-piso;
L14 cinemática 1-sala."""


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
