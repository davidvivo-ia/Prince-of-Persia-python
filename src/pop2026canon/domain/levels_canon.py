"""Los 14 niveles canónicos del POP1 — versión expandida 18-24 salas.

**Fuente**: walkthroughs comunidad (popot.org, gamefaqs, popuw.com) y
descripciones canónicas. No hay `LEVELS.DAT` original: estos layouts
son **fan-recreation fieles a la canon** — mismas mecánicas, eventos
narrativos, número de salas y progresión espacial, pero no byte-perfect.

Cada nivel se construye con :func:`_build_level` a partir de una lista
de specs de sala **y un mapa de cuadrícula** (``grid``). El grid es un
string multilinea donde cada token es el id de una sala (o ``.`` para
vacío); los links N/S/E/W se derivan automáticamente de la adyacencia,
igual que en el juego original, donde las salas son ventanas sobre un
mapa continuo. Esto garantiza por construcción:

- links recíprocos (si A está al este de B, B está al oeste de A),
- geometría planar (ninguna sala ocupa dos posiciones),
- que caer al sur / trepar al norte siempre lleva a la sala correcta.

Cada spec usa los helpers de :mod:`_blocks`:

- ``floor`` — sala-corredor con suelo+techo (opcional pit, extras)
- ``arena`` — sala abierta sin techo (para drops cortos)
- ``pillar`` — sala con columnas en el suelo, romper la línea visual
- ``lattice`` — sala con rejas escalables (LATTICE_*)
- ``balcony`` — sala con balcón visible al fondo
- ``doortop`` — sala con tapiz superior pisable (multi-piso)
- ``drop`` — sala de drop puro (sólo plataformas a los lados)
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
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
# Grid de salas → links automáticos
# ---------------------------------------------------------------------------


def _grid_links(grid: str, n_rooms: int) -> dict[int, tuple[int, int, int, int]]:
    """Parsea un mapa 2D de ids de sala y deriva los links por adyacencia.

    ``grid`` es un string multilinea: cada token es un id de sala (int)
    o ``.`` para celda vacía. Devuelve ``{room_id: (n, s, e, w)}``.

    Lanza ``ValueError`` si algún id está repetido, falta, o sobra —
    así un typo en el mapa rompe el import en vez de producir geometría
    imposible en runtime.
    """
    coords: dict[int, tuple[int, int]] = {}
    occupied: dict[tuple[int, int], int] = {}
    for y, line in enumerate(grid.strip().splitlines()):
        for x, token in enumerate(line.split()):
            if token == ".":
                continue
            rid = int(token)
            if rid in coords:
                raise ValueError(f"grid: sala {rid} aparece dos veces")
            coords[rid] = (x, y)
            occupied[(x, y)] = rid
    expected = set(range(1, n_rooms + 1))
    if set(coords) != expected:
        missing = expected - set(coords)
        extra = set(coords) - expected
        raise ValueError(f"grid: ids incorrectos — faltan {missing or '∅'}, sobran {extra or '∅'}")
    links: dict[int, tuple[int, int, int, int]] = {}
    for rid, (x, y) in coords.items():
        links[rid] = (
            occupied.get((x, y - 1), 0),  # n
            occupied.get((x, y + 1), 0),  # s
            occupied.get((x + 1, y), 0),  # e
            occupied.get((x - 1, y), 0),  # w
        )
    return links


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


def _platform_rows(
    *,
    platform_cols: tuple[int, ...] = (4, 5),
    pit_cols: tuple[int, ...] = (),
    extras: Mapping[tuple[int, int], Tile] | None = None,
) -> tuple[list[Tile | int], list[Tile | int], list[Tile | int]]:
    """Sala con plataforma flotante en row 1 (suelo intermedio en `platform_cols`).

    El kid puede saltar al tile DOORTOP_WITH_FLOOR en row 1 para usarlo
    como suelo, dando un segundo piso interno a la sala.
    """
    top, mid, bot = _floor_rows()
    for c in platform_cols:
        if 0 <= c < SCREEN_TILECOUNT_X:
            mid[c] = DT_F
    for c in pit_cols:
        if 0 <= c < SCREEN_TILECOUNT_X:
            bot[c] = E
    if extras:
        for (col, row), tile in extras.items():
            (top, mid, bot)[row][col] = tile
    return top, mid, bot


def _split_rows(
    *,
    upper_cols: tuple[int, ...] = (0, 1, 2, 3),
    lower_cols: tuple[int, ...] = (6, 7, 8, 9),
    pit_cols: tuple[int, ...] = (),
    extras: Mapping[tuple[int, int], Tile] | None = None,
) -> tuple[list[Tile | int], list[Tile | int], list[Tile | int]]:
    """Sala "escalonada": plataforma elevada en ``upper_cols`` (row 1) que
    cubre un lado, y suelo completo en row 2 (excepto ``pit_cols``).

    ``lower_cols`` se mantiene por compatibilidad pero ya no afecta —
    el suelo es continuo salvo pit explícito.
    """
    _ = lower_cols  # parámetro retenido por compatibilidad
    top: list[Tile | int] = [F] * SCREEN_TILECOUNT_X
    mid: list[Tile | int] = [E] * SCREEN_TILECOUNT_X
    bot: list[Tile | int] = [F] * SCREEN_TILECOUNT_X
    for c in upper_cols:
        if 0 <= c < SCREEN_TILECOUNT_X:
            mid[c] = DT_F
    for c in pit_cols:
        if 0 <= c < SCREEN_TILECOUNT_X:
            bot[c] = E
    if extras:
        for (col, row), tile in extras.items():
            (top, mid, bot)[row][col] = tile
    return top, mid, bot


def _arena_rows(
    *,
    pillar_pair: tuple[int, int] = (2, 7),
    extras: Mapping[tuple[int, int], Tile] | None = None,
) -> tuple[list[Tile | int], list[Tile | int], list[Tile | int]]:
    """Sala-arena: suelo completo, dos columnas grandes flanqueando el
    centro para el combate."""
    top, mid, bot = _floor_rows()
    for c in pillar_pair:
        if 0 <= c < SCREEN_TILECOUNT_X:
            mid[c] = BP_T
            bot[c] = BP_B
    if extras:
        for (col, row), tile in extras.items():
            (top, mid, bot)[row][col] = tile
    return top, mid, bot


# ---------------------------------------------------------------------------
# RoomSpec — declaración compacta de una sala (los links vienen del grid)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _RoomSpec:
    """Spec compacta para construir una sala dentro de un nivel."""

    rows: tuple[list[Tile | int], list[Tile | int], list[Tile | int]]
    guards: tuple[GuardSpawn, ...] = ()
    fg_modifiers: tuple[tuple[tuple[int, int], int], ...] = ()


def _spec(
    rows: tuple[list[Tile | int], list[Tile | int], list[Tile | int]],
    *,
    guards: tuple[GuardSpawn, ...] = (),
    fg_mods: tuple[tuple[tuple[int, int], int], ...] = (),
) -> _RoomSpec:
    return _RoomSpec(rows=rows, guards=guards, fg_modifiers=fg_mods)


def _carve_vertical_openings(rooms: tuple[Room, ...]) -> tuple[Room, ...]:
    """Alinea los huecos verticales entre pisos.

    Principio del mapa continuo: un agujero en el suelo (row 2 EMPTY o
    LOOSE) de una sala ES un agujero en el techo (row 0) de la sala de
    abajo. Sin esto, los drops aterrizan encima del techo del piso
    inferior y ningún descenso funciona.

    Sólo se perfora FLOOR liso — plataformas (DOORTOP_WITH_FLOOR) y
    tiles especiales del techo se respetan.
    """
    by_id = {r.id: r for r in rooms}
    carve: dict[int, set[int]] = {}
    for room in rooms:
        south_id = room.link_s
        if not south_id or south_id not in by_id:
            continue
        south = by_id[south_id]
        for c in range(SCREEN_TILECOUNT_X):
            bottom_piece = Tile(room.fg[2 * SCREEN_TILECOUNT_X + c] & 0x1F)
            if bottom_piece not in (Tile.EMPTY, Tile.LOOSE):
                continue
            top_piece = Tile(south.fg[c] & 0x1F)
            if top_piece is Tile.FLOOR:
                carve.setdefault(south_id, set()).add(c)
    if not carve:
        return rooms
    new_rooms = []
    for room in rooms:
        cols = carve.get(room.id)
        if not cols:
            new_rooms.append(room)
            continue
        fg = list(room.fg)
        for c in cols:
            fg[c] = encode_tile(Tile.EMPTY, 0)
        new_rooms.append(
            Room(
                id=room.id,
                fg=tuple(fg),
                bg=room.bg,
                link_n=room.link_n,
                link_s=room.link_s,
                link_e=room.link_e,
                link_w=room.link_w,
                guards=room.guards,
            )
        )
    return tuple(new_rooms)


def _build_level(
    *,
    number: int,
    name: str,
    specs: Sequence[_RoomSpec],
    grid: str,
    start_room: int,
    start_col: int,
    start_row: int,
    start_direction: int = 0,
    events: tuple[Event, ...] = (),
    doorlinks: tuple[DoorLink, ...] = (),
) -> Level:
    links = _grid_links(grid, len(specs))
    rooms = tuple(
        _room_from_rows(
            i + 1,
            spec.rows,
            link_n=links[i + 1][0],
            link_s=links[i + 1][1],
            link_e=links[i + 1][2],
            link_w=links[i + 1][3],
            guards=spec.guards,
            fg_modifiers=dict(spec.fg_modifiers) if spec.fg_modifiers else None,
        )
        for i, spec in enumerate(specs)
    )
    rooms = _carve_vertical_openings(rooms)
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
# Mazmorra subterránea en cuadrícula 6x3: piso superior (spawn + descent),
# piso intermedio (sword + guards + gates) y piso inferior (plates + exit).


def _l1() -> Level:
    G_S = GuardSpawn  # noqa: N806 — alias local de tipo
    grid = """
     1  2  3  4  5  6
     7  8  9 10 11 12
    13 14 15 16 17 18
    """
    specs = [
        # Piso superior
        _spec(_floor_rows(extras={(4, 2): L, (5, 2): L})),  # 1 spawn + loose
        _spec(_floor_rows(extras={(6, 1): T})),
        _spec(_floor_rows(pit_cols=(4, 5))),  # 3 pit → drop a 9
        _spec(_platform_rows(platform_cols=(4, 5), extras={(7, 1): T})),  # 4 plataforma
        _spec(_split_rows(upper_cols=(0, 1, 2), lower_cols=(5, 6, 7, 8, 9))),  # 5 split
        _spec(_floor_rows(extras={(5, 2): L})),  # 6 dead-end con drop a 12
        # Piso intermedio
        _spec(_floor_rows(extras={(6, 1): T})),
        _spec(
            _platform_rows(platform_cols=(2, 3), extras={(2, 1): SW, (5, 1): T, (7, 1): P}),
        ),  # 8 SWORD + plate que abre la gate de 9
        _spec(_floor_rows(extras={(5, 1): G})),  # 9 gate
        _spec(
            _floor_rows(extras={(4, 1): C}),
            guards=(G_S(col=6, row=1, direction=-1, skill=0),),
        ),  # 10 guard + chomper
        _spec(
            _pillar_rows(pillar_cols=(4,), extras={(2, 1): P, (7, 1): G}),
        ),  # 11 plate propia + gate
        _spec(_floor_rows(extras={(5, 1): P, (5, 2): L})),  # 12 plate + loose drop al exit
        # Piso inferior
        _spec(_floor_rows(extras={(3, 1): P})),  # 13 plate
        _spec(_floor_rows(extras={(5, 1): L})),
        _spec(_floor_rows(pit_cols=(4, 5, 6))),  # 15 pit
        _spec(
            _floor_rows(extras={(6, 1): T}),
            guards=(G_S(col=4, row=1, direction=-1, skill=0),),
        ),
        _spec(_floor_rows(extras={(2, 1): P})),  # 17 plate
        _spec(_floor_rows(extras={(7, 1): DL, (8, 1): DR})),  # 18 exit
    ]
    doorlinks = (
        # plate sala 8 col 7 (junto a la sword) → gate sala 9 col 5
        DoorLink(plate_room=8, plate_col=7, plate_row=1, gate_room=9, gate_col=5, gate_row=1),
        # plate sala 11 col 2 → gate sala 11 col 7 (misma sala)
        DoorLink(plate_room=11, plate_col=2, plate_row=1, gate_room=11, gate_col=7, gate_row=1),
        # plate sala 12 col 5 → gate sala 9 col 5 (reapertura desde el este)
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
        grid=grid,
        start_room=1,
        start_col=2,
        start_row=1,
        start_direction=-1,
        doorlinks=doorlinks,
    )


# ===========================================================================
# Nivel 2 — The Guards  (20 salas)
# ===========================================================================
# Dos filas de patios: la norte con guards de skill 1-3 y trampas; la sur
# con el exit (sala 18) y las potions bonus al este del exit (19-20).
# El descenso es por los loose floors del spawn (sala 1 → 11).


def _l2() -> Level:
    G_S = GuardSpawn  # noqa: N806
    grid = """
     1  2  3  4  5  6  7  8  9 10
    11 12 13 14 15 16 17 18 19 20
    """
    specs = [
        # Fila norte
        _spec(_floor_rows(extras={(5, 2): L})),  # 1 spawn — loose drop a 11
        _spec(
            _floor_rows(extras={(2, 1): T, (7, 1): T}),
            guards=(G_S(col=5, row=1, direction=-1, skill=1),),
        ),  # 2 patio con antorchas
        _spec(_floor_rows(extras={(4, 1): C})),
        _spec(_platform_rows(platform_cols=(4, 5), pit_cols=(7,))),  # 4 plataforma + pit
        _spec(_split_rows(upper_cols=(0, 1, 2, 3), lower_cols=(5, 6, 7, 8, 9))),  # 5 split
        _spec(_floor_rows(extras={(5, 1): G})),
        _spec(_floor_rows(extras={(2, 1): P})),  # 7 plate
        _spec(
            _arena_rows(pillar_pair=(2, 7)),
            guards=(G_S(col=5, row=1, direction=-1, skill=2),),
        ),  # 8 arena
        _spec(_pillar_rows(pillar_cols=(4,))),
        _spec(_floor_rows(extras={(6, 1): T})),
        # Fila sur — camino al exit
        _spec(_floor_rows(extras={(5, 1): T})),  # 11 antorcha
        _spec(_floor_rows(extras={(5, 1): C})),
        _spec(_floor_rows(extras={(4, 2): L, (5, 2): L})),
        _spec(_floor_rows(extras={(3, 1): P, (7, 1): G})),  # 14 plate+gate
        _spec(
            _floor_rows(extras={(5, 1): T}),
            guards=(G_S(col=3, row=1, direction=0, skill=3),),
        ),
        _spec(_pillar_rows(pillar_cols=(4, 6), extras={(5, 0): DT})),  # 16 con pillars
        _spec(_floor_rows(extras={(4, 1): C})),
        _spec(
            _floor_rows(extras={(7, 1): DL, (8, 1): DR}),
            guards=(G_S(col=2, row=1, direction=0, skill=3),),
        ),  # 18 exit
        # Bonus al este del exit
        _spec(_balcony_rows(side="left", extras={(5, 1): PO})),  # 19 potion HEAL
        _spec(_floor_rows(extras={(4, 1): PO})),  # 20 potion MAX_HP
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
        grid=grid,
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
# Fila norte 1-9; sub-piso 10-17 (el pit de la sala 3 cae en los loose de
# la 10); estancias secretas 17-18 bajo la sala 9 del plate.


def _l3() -> Level:
    G_S = GuardSpawn  # noqa: N806
    grid = """
     1  2  3  4  5  6  7  8  9
     . 11 10 12 13 14 15 16 17
     .  .  .  .  .  .  .  . 18
    """
    specs = [
        _spec(_floor_rows(extras={(4, 1): SK})),  # 1 esqueleto durmiente
        _spec(_floor_rows(extras={(5, 2): L})),
        _spec(_platform_rows(platform_cols=(4, 5), pit_cols=(4, 5))),  # 3 plataforma sobre pit
        _spec(_lattice_rows(lattice_cols=(4,))),
        _spec(_floor_rows(extras={(3, 1): C})),
        _spec(
            _arena_rows(pillar_pair=(2, 7)),
            guards=(G_S(col=5, row=1, direction=-1, skill=2),),
        ),  # 6 arena
        _spec(_pillar_rows(pillar_cols=(3, 7))),
        _spec(_floor_rows(extras={(5, 1): G})),  # 8 gate
        _spec(_floor_rows(extras={(5, 1): P})),  # 9 plate — bajo ella, la secret room 17
        # Sub-piso
        _spec(_floor_rows(extras={(3, 2): L, (5, 2): L})),  # 10 — recibe el drop del pit de 3
        _spec(_floor_rows(extras={(6, 1): T})),  # 11 antorcha (oeste de 10)
        _spec(_doortop_rows(doortop_cols=(4, 5))),
        _spec(_floor_rows(extras={(3, 1): C, (6, 1): C})),
        _spec(
            _arena_rows(pillar_pair=(2, 7)),
            guards=(G_S(col=5, row=1, direction=0, skill=2),),
        ),  # 14 arena
        _spec(_floor_rows(extras={(4, 1): P})),  # 15 plate
        _spec(
            _floor_rows(extras={(7, 1): DL, (8, 1): DR}),
            guards=(G_S(col=3, row=1, direction=0, skill=2),),
        ),  # 16 exit
        # Estancias secretas — drop desde la sala 9
        _spec(_floor_rows(extras={(5, 1): PO})),  # 17 potion HEAL
        _spec(_pillar_rows(pillar_cols=(4, 6), extras={(2, 1): PO})),  # 18 max_hp
    ]
    doorlinks = (
        DoorLink(plate_room=9, plate_col=5, plate_row=1, gate_room=8, gate_col=5, gate_row=1),
        DoorLink(plate_room=15, plate_col=4, plate_row=1, gate_room=8, gate_col=5, gate_row=1),
    )
    events = (Event(EventKind.SKELETON_WAKE, room=1, col=2),)
    lvl = _build_level(
        number=3,
        name="The Skeleton",
        specs=specs,
        grid=grid,
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
# Fila norte 1-10 con el MIRROR en 5 y el exit en 10; sub-piso 11-18
# (el pit de la 3 cae en la potion poison de la 11); rincón 19-20.


def _l4() -> Level:
    G_S = GuardSpawn  # noqa: N806
    grid = """
     1  2  3  4  5  6  7  8  9 10
     .  . 11 12 13 14 15 16 17 18
     .  .  .  .  .  .  .  . 19 20
    """
    specs = [
        _spec(_floor_rows(extras={(5, 2): L})),  # 1 spawn
        _spec(_floor_rows(extras={(3, 1): S, (5, 1): S, (7, 1): S})),  # slalom
        _spec(_floor_rows(pit_cols=(4, 5, 6))),  # 3 pit → drop a 11
        _spec(_lattice_rows(lattice_cols=(3, 6))),
        _spec(_floor_rows(extras={(5, 1): M, (8, 1): PO})),  # 5 MIRROR + potion
        _spec(_floor_rows(extras={(3, 1): P, (7, 1): C})),  # 6 plate + chomper
        _spec(_floor_rows(extras={(4, 1): G})),  # 7 gate
        _spec(_pillar_rows(pillar_cols=(4, 7))),
        _spec(_floor_rows(extras={(5, 2): L, (3, 1): T})),
        _spec(
            _floor_rows(extras={(7, 1): DL, (8, 1): DR}),
            guards=(G_S(col=3, row=1, direction=0, skill=3),),
        ),  # 10 exit — drop al 18
        # Sub-piso
        _spec(_floor_rows(extras={(2, 1): PO})),  # 11 potion poison
        _spec(_floor_rows(extras={(4, 1): C, (6, 1): C})),
        _spec(_balcony_rows(side="left")),
        _spec(_floor_rows(), guards=(G_S(col=5, row=1, direction=-1, skill=3),)),
        _spec(_doortop_rows(doortop_cols=(3, 4, 5))),
        _spec(_floor_rows(extras={(5, 1): P})),  # 16 plate adicional
        _spec(_pillar_rows(pillar_cols=(3, 6), extras={(7, 1): T})),
        _spec(_floor_rows(extras={(5, 1): PO})),  # 18 potion FLOAT
        # Rincón sur-este
        _spec(_floor_rows(extras={(4, 2): L, (5, 2): L})),
        _spec(_floor_rows(extras={(5, 1): T})),  # 20 final estancia
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
        grid=grid,
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
    grid = """
     1  2  3  4  5  6  7  8  9 10  .  .  .
    11 12 13  .  .  . 14 15 16 17 18 19 20
    """
    specs = [
        _spec(
            _floor_rows(),
            guards=(G_S(col=5, row=1, direction=-1, skill=3),),
        ),  # 1 spawn + drop al sub-loop
        _spec(_floor_rows(extras={(3, 2): L, (4, 2): L, (5, 2): L})),  # triple loose
        _spec(
            _split_rows(upper_cols=(0, 1, 2, 3), lower_cols=(6, 7, 8, 9), extras={(7, 1): S}),
        ),  # 3 escalonada
        _spec(_platform_rows(platform_cols=(3, 4, 5), extras={(4, 1): PO})),  # 4 POTION
        _spec(_floor_rows(extras={(5, 2): L})),
        _spec(_floor_rows(extras={(8, 1): P})),
        _spec(_floor_rows(extras={(3, 1): G})),  # 7 gate — drop al 14
        _spec(_arena_rows(pillar_pair=(2, 7))),  # 8 arena
        _spec(_platform_rows(platform_cols=(4, 5, 6), extras={(5, 1): T})),
        _spec(
            _floor_rows(extras={(7, 1): DL, (8, 1): DR}),
            guards=(G_S(col=3, row=1, direction=0, skill=3),),
        ),  # 10 exit
        # Sub-rooms bajo el spawn
        _spec(_floor_rows(extras={(4, 1): SK})),  # 11 stub skeleton
        _spec(_floor_rows(extras={(5, 2): L})),
        _spec(_balcony_rows(side="right")),  # 13 dead-end con balcony
        _spec(_floor_rows(extras={(5, 1): PO})),  # 14 potion empty (decorativa)
        _spec(_lattice_rows(lattice_cols=(3, 5, 7))),
        _spec(_floor_rows(extras={(5, 1): C, (6, 1): S})),
        _spec(_doortop_rows(doortop_cols=(4, 5))),
        _spec(_floor_rows(extras={(3, 1): T, (7, 1): T})),
        _spec(_pillar_rows(pillar_cols=(4, 6))),
        _spec(
            _floor_rows(extras={(4, 1): PO}),
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
        grid=grid,
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
    grid = """
     1  2  3  4  5  6  7  8  9 10  .  .  .
     .  .  .  .  . 11 12 13 14 15 16 17 18
    """
    specs = [
        _spec(_floor_rows(pit_cols=(4, 5, 6))),  # 1 pit grande — frame_43 trigger
        _spec(_floor_rows(extras={(1, 1): P, (3, 1): G})),  # 2 plate + gate
        _spec(_floor_rows(extras={(4, 1): C, (7, 1): P})),  # 3 plate
        _spec(
            _floor_rows(extras={(7, 1): S}),
            guards=(G_S(col=5, row=1, direction=-1, skill=4),),
        ),
        _spec(_arena_rows(pillar_pair=(3, 7))),  # 5 arena combat
        _spec(_platform_rows(platform_cols=(4, 5, 6), extras={(5, 2): L})),  # 6 drop al 11
        _spec(_lattice_rows(lattice_cols=(3, 5, 7))),
        _spec(_floor_rows(extras={(5, 1): G, (8, 1): P})),  # 8 gate + plate local
        _spec(
            _split_rows(upper_cols=(0, 1, 2), lower_cols=(5, 6, 7, 8, 9), extras={(3, 1): C}),
        ),
        _spec(
            _floor_rows(extras={(7, 1): DL, (8, 1): DR}),
            guards=(G_S(col=3, row=1, direction=0, skill=4),),
        ),  # 10 exit
        # Piso inferior — atajo opcional
        _spec(_floor_rows(extras={(5, 1): PO})),  # 11 potion HEAL
        _spec(_floor_rows(pit_cols=(4, 5))),
        _spec(_balcony_rows(side="left")),
        _spec(_floor_rows(extras={(3, 1): S, (5, 1): S, (7, 1): S})),  # slalom
        _spec(_floor_rows(extras={(5, 1): P})),  # 15 plate (extra)
        _spec(_doortop_rows(doortop_cols=(4, 5, 6))),
        _spec(_floor_rows(extras={(5, 1): T})),
        _spec(_pillar_rows(pillar_cols=(3, 6), extras={(4, 1): PO})),  # 18 potion max_hp
    ]
    doorlinks = (
        DoorLink(plate_room=2, plate_col=1, plate_row=1, gate_room=2, gate_col=3, gate_row=1),
        DoorLink(plate_room=3, plate_col=7, plate_row=1, gate_room=2, gate_col=3, gate_row=1),
        DoorLink(plate_room=8, plate_col=8, plate_row=1, gate_room=8, gate_col=5, gate_row=1),
        DoorLink(plate_room=15, plate_col=5, plate_row=1, gate_room=2, gate_col=3, gate_row=1),
    )
    events = (Event(EventKind.SHADOW_STEP, room=1, extra=43),)
    lvl = _build_level(
        number=6,
        name="The Steps",
        specs=specs,
        grid=grid,
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
# Tres pisos completos 7 salas + exit colgado al este del piso bajo.
# Descensos reales: loose del spawn (1→8), loose de la 9 (→16),
# potion bajo la arena 6 (→13) y trampa de chompers bajo la gate 7 (→14).


def _l7() -> Level:
    G_S = GuardSpawn  # noqa: N806
    grid = """
     1  2  3  4  5  6  7  .
     8  9 10 11 12 13 14  .
    15 16 17 18 19 20 21 22
    """
    specs = [
        _spec(_floor_rows(extras={(5, 2): L})),  # 1 spawn drop
        _spec(_floor_rows(extras={(3, 1): S, (5, 1): S, (7, 1): S})),
        _spec(_lattice_rows(lattice_cols=(3, 6))),
        _spec(_platform_rows(platform_cols=(3, 4, 5), extras={(5, 1): P})),  # 4 plate
        _spec(_pillar_rows(pillar_cols=(4, 7))),
        _spec(
            _arena_rows(pillar_pair=(2, 7)),
            guards=(G_S(col=5, row=1, direction=-1, skill=5),),
        ),  # 6 arena
        _spec(_floor_rows(extras={(5, 1): G})),  # 7 gate dead-end
        # Piso intermedio
        _spec(_drop_rows(floor_cols=(0, 1, 8, 9), extras={(5, 1): T})),  # 8 pozo
        _spec(_floor_rows(extras={(4, 2): L, (5, 2): L})),  # 9 loose → drop a 16
        _spec(_floor_rows(extras={(3, 1): C})),
        _spec(_pillar_rows(pillar_cols=(4,))),
        _spec(_balcony_rows(side="right")),
        _spec(_floor_rows(extras={(5, 1): PO})),  # 13 potion HEAL (bajo la arena 6)
        _spec(_floor_rows(extras={(2, 1): C, (6, 1): C})),  # 14 doble chomper (bajo la gate 7)
        # Piso bajo
        _spec(_floor_rows(extras={(5, 1): S})),  # 15 spike
        _spec(_doortop_rows(doortop_cols=(3, 4, 5))),
        _spec(_floor_rows(extras={(4, 2): L, (5, 2): L, (6, 2): L})),
        _spec(_lattice_rows(lattice_cols=(3, 5, 7), extras={(5, 1): T})),
        _spec(_floor_rows(), guards=(G_S(col=4, row=1, direction=0, skill=5),)),
        _spec(_pillar_rows(pillar_cols=(3, 6))),
        _spec(_floor_rows(extras={(5, 1): P})),  # 21 plate (extra)
        _spec(
            _floor_rows(extras={(7, 1): DL, (8, 1): DR}),
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
        grid=grid,
        start_room=1,
        start_col=1,
        start_row=1,
        doorlinks=doorlinks,
    )
    return _with_potion_types(lvl, {(13, 5, 1): PotionType.HEAL})


# ===========================================================================
# Nivel 8 — The Caverns  (20 salas)
# ===========================================================================
def _l8() -> Level:
    G_S = GuardSpawn  # noqa: N806
    grid = """
     1  2  3  4  5  6  7  8  9 10
    11 12 13 14 15 16 17 18 19 20
    """
    specs = [
        _spec(_floor_rows(pit_cols=(4, 5), extras={(7, 2): L})),  # 1 spawn — drop a 11
        _spec(_floor_rows(extras={(5, 1): C, (3, 2): L})),
        _spec(_lattice_rows(lattice_cols=(4, 6))),
        _spec(_floor_rows(extras={(5, 2): L, (6, 2): L, (7, 2): L})),  # cave loose
        _spec(_pillar_rows(pillar_cols=(3, 6))),
        _spec(
            _floor_rows(extras={(7, 1): S}),
            guards=(G_S(col=4, row=1, direction=0, skill=4),),
        ),
        _spec(_floor_rows(extras={(5, 1): C})),
        _spec(_floor_rows(extras={(5, 1): P})),
        _spec(_balcony_rows(side="left", extras={(5, 1): T})),
        _spec(
            _floor_rows(extras={(2, 1): G, (7, 1): DL, (8, 1): DR}),
        ),  # 10 exit + gate (mouse abre)
        # Sub-cuevas
        _spec(_floor_rows(extras={(4, 2): L, (5, 2): L})),
        _spec(_doortop_rows(doortop_cols=(3, 4, 5))),
        _spec(_floor_rows(extras={(3, 1): C, (6, 1): C})),
        _spec(_floor_rows(extras={(5, 1): PO})),
        _spec(_pillar_rows(pillar_cols=(4, 7))),
        _spec(_floor_rows(extras={(5, 1): SK})),  # 16 esqueleto decorativo
        _spec(_floor_rows(extras={(5, 2): L})),
        _spec(_lattice_rows(lattice_cols=(3, 5, 7))),
        _spec(_floor_rows(), guards=(G_S(col=5, row=1, direction=-1, skill=4),)),
        _spec(_floor_rows(extras={(4, 1): PO})),  # 20 potion (cul-de-sac)
    ]
    doorlinks: tuple[DoorLink, ...] = ()  # gate de sala 10 sólo se abre con mouse
    events = (Event(EventKind.MOUSE_APPEAR, room=10),)
    lvl = _build_level(
        number=8,
        name="The Caverns",
        specs=specs,
        grid=grid,
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
# Fila norte 1-10 con el exit en 10; sótano 11-20 bajo ella. La potion
# MAX_HP (19) queda justo bajo el exit; 20 es el rincón final.


def _l9() -> Level:
    G_S = GuardSpawn  # noqa: N806
    grid = """
     1  2  3  4  5  6  7  8  9 10  .
     . 11 12 13 14 15 16 17 18 19 20
    """
    specs = [
        _spec(_floor_rows(extras={(4, 1): SK, (6, 2): L})),  # 1 esqueleto durmiente
        _spec(_floor_rows(extras={(3, 1): S, (5, 1): S, (7, 1): S})),  # 2 — drop a 11
        _spec(_pillar_rows(pillar_cols=(4,))),
        _spec(
            _arena_rows(pillar_pair=(2, 7), extras={(8, 1): PO}),
            guards=(G_S(col=5, row=1, direction=-1, skill=5),),
        ),  # 4 arena con potion
        _spec(_floor_rows(extras={(2, 1): P, (5, 1): G})),  # 5 plate + gate
        _spec(_lattice_rows(lattice_cols=(3, 5, 7))),
        _spec(
            _platform_rows(platform_cols=(4, 5, 6), extras={(5, 1): SK, (4, 1): P}),
        ),  # 7 plate alto
        _spec(_balcony_rows(side="right")),
        _spec(_split_rows(upper_cols=(0, 1, 2), extras={(4, 1): C, (6, 1): C})),
        _spec(
            _floor_rows(extras={(7, 1): DL, (8, 1): DR}),
            guards=(G_S(col=3, row=1, direction=0, skill=5),),
        ),  # 10 exit — drop a 19
        # Sótano sub-tumba
        _spec(_floor_rows(extras={(5, 2): L})),
        _spec(_floor_rows(extras={(4, 1): C, (6, 1): C})),
        _spec(_doortop_rows(doortop_cols=(4, 5))),
        _spec(_pillar_rows(pillar_cols=(3, 6))),
        _spec(_floor_rows(extras={(5, 1): T})),
        _spec(_floor_rows(extras={(4, 1): P})),  # 16 plate
        _spec(_floor_rows(extras={(3, 1): SK})),  # 17 skeleton
        _spec(_lattice_rows(lattice_cols=(3, 5))),
        _spec(_floor_rows(extras={(5, 1): PO})),  # 19 potion MAX_HP bajo el exit
        _spec(_floor_rows(extras={(5, 1): T})),  # 20 rincón final
    ]
    doorlinks = (
        DoorLink(plate_room=5, plate_col=2, plate_row=1, gate_room=5, gate_col=5, gate_row=1),
        DoorLink(plate_room=7, plate_col=4, plate_row=1, gate_room=5, gate_col=5, gate_row=1),
        DoorLink(plate_room=16, plate_col=4, plate_row=1, gate_room=5, gate_col=5, gate_row=1),
    )
    lvl = _build_level(
        number=9,
        name="The Tomb",
        specs=specs,
        grid=grid,
        start_room=1,
        start_col=1,
        start_row=1,
        doorlinks=doorlinks,
    )
    return _with_potion_types(lvl, {(4, 8, 1): PotionType.HEAL, (19, 5, 1): PotionType.MAX_HP})


# ===========================================================================
# Nivel 10 — The Tower  (20 salas)  vertical
# ===========================================================================
# Pozo vertical de 10 salas (1 arriba → 10 abajo con el exit) y galería
# lateral 11-20 colgada del nivel de la sala 4.


def _l10() -> Level:
    G_S = GuardSpawn  # noqa: N806
    grid = """
     1  .  .  .  .  .  .  .  .  .  .
     2  .  .  .  .  .  .  .  .  .  .
     3  .  .  .  .  .  .  .  .  .  .
     4 11 12 13 14 15 16 17 18 19 20
     5  .  .  .  .  .  .  .  .  .  .
     6  .  .  .  .  .  .  .  .  .  .
     7  .  .  .  .  .  .  .  .  .  .
     8  .  .  .  .  .  .  .  .  .  .
     9  .  .  .  .  .  .  .  .  .  .
    10  .  .  .  .  .  .  .  .  .  .
    """
    # El pozo baja en zigzag: cada sala tiene su hueco desplazado respecto
    # al de arriba, de modo que cada caída es de UN piso (aterrizas en
    # suelo firme y caminas hasta el siguiente hueco).
    specs = [
        _spec(_floor_rows(pit_cols=(4, 5, 6))),  # 1 top: drop
        _spec(
            _drop_rows(floor_cols=(0, 1, 4, 5, 6, 9)),  # huecos en 2,3,7,8
            guards=(G_S(col=9, row=1, direction=-1, skill=5),),
        ),
        _spec(_floor_rows(pit_cols=(8, 9), extras={(3, 1): S, (5, 1): S})),  # 3 spikes + hueco este
        _spec(
            _drop_rows(floor_cols=(0, 1, 2, 3, 4, 5, 8, 9))
        ),  # 4 huecos 6,7 (al este de la gate de abajo) + galería al este
        _spec(_floor_rows(pit_cols=(8, 9), extras={(5, 1): G})),  # 5 gate + hueco este
        _spec(_lattice_rows(lattice_cols=(3, 6), extras={(4, 2): E, (5, 2): E})),  # 6
        _spec(_pillar_rows(pillar_cols=(4,), extras={(8, 2): E, (9, 2): E})),  # 7
        _spec(
            _drop_rows(floor_cols=(0, 1, 2, 3, 8, 9)),  # huecos 4-7
            guards=(G_S(col=2, row=1, direction=0, skill=5),),
        ),
        _spec(_floor_rows(extras={(0, 2): E, (1, 2): E, (5, 2): L})),  # 9 hueco oeste + loose
        _spec(
            _floor_rows(extras={(5, 1): P, (7, 1): DL, (8, 1): DR}),
        ),  # 10 exit + plate (open finale gate)
        # Galería lateral (loop puzzle)
        _spec(_floor_rows(extras={(5, 1): P})),  # 11 plate
        _spec(_balcony_rows(side="right")),
        _spec(_floor_rows(extras={(4, 2): L, (5, 2): L})),
        _spec(_doortop_rows(doortop_cols=(4, 5))),
        _spec(_pillar_rows(pillar_cols=(3, 6, 8))),
        _spec(_floor_rows(extras={(5, 1): PO})),  # 16 potion
        _spec(_lattice_rows(lattice_cols=(3, 5, 7))),
        _spec(_floor_rows(extras={(5, 1): T})),
        _spec(_floor_rows(extras={(3, 1): C, (7, 1): C})),
        _spec(
            _floor_rows(),
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
        grid=grid,
        start_room=1,
        start_col=1,
        start_row=1,
        doorlinks=doorlinks,
    )
    return _with_potion_types(lvl, {(16, 5, 1): PotionType.HEAL})


# ===========================================================================
# Nivel 11 — The Tower II  (20 salas)
# ===========================================================================
# Bloque superior 2x2 (1-2 / 3-4), galería larga 7-20 como tercer piso
# y cámara final 5-6 colgada bajo la galería: los loose floors de la
# sala 13 son la única entrada a la sala de la gate (5) y el exit (6).


def _l11() -> Level:
    G_S = GuardSpawn  # noqa: N806
    grid = """
     1  2  .  .  .  .  .  .  .  .  .  .  .  .
     3  4  .  .  .  .  .  .  .  .  .  .  .  .
     7  8  9 10 11 12 13 14 15 16 17 18 19 20
     .  .  .  .  .  . 5  6  .  .  .  .  .  .
    """
    specs = [
        _spec(
            _platform_rows(platform_cols=(4, 5, 6), pit_cols=(4, 5), extras={(2, 1): T}),
        ),  # 1 spawn — el pit baja a 3
        _spec(
            _arena_rows(pillar_pair=(2, 7)),
            guards=(G_S(col=5, row=1, direction=-1, skill=5),),
        ),  # 2 arena
        _spec(_floor_rows(extras={(3, 1): C, (6, 1): C, (5, 2): L})),  # 3 — loose baja a 7
        _spec(
            _platform_rows(platform_cols=(3, 4, 5), pit_cols=(7,)),
            guards=(G_S(col=4, row=1, direction=-1, skill=5),),
        ),  # 4 plataforma — el pit baja a 8
        _spec(_floor_rows(extras={(5, 1): G, (2, 1): P})),  # 5 plate+gate local
        _spec(_floor_rows(extras={(7, 1): DL, (8, 1): DR})),  # 6 exit
        # Galería (tercer piso)
        _spec(_lattice_rows(lattice_cols=(3, 6))),  # 7
        _spec(_floor_rows(extras={(4, 1): S, (6, 1): S})),
        _spec(_pillar_rows(pillar_cols=(4,))),
        _spec(_balcony_rows(side="left")),
        _spec(_floor_rows(extras={(5, 1): PO})),  # 11 potion HEAL
        _spec(_doortop_rows(doortop_cols=(4, 5, 6))),
        _spec(_floor_rows(extras={(3, 2): L, (4, 2): L})),  # 13 — loose baja a 5
        _spec(_pillar_rows(pillar_cols=(3, 7))),
        _spec(
            _floor_rows(extras={(5, 1): T}),
            guards=(G_S(col=4, row=1, direction=0, skill=5),),
        ),
        _spec(_floor_rows(extras={(4, 1): C, (6, 1): C})),
        _spec(_floor_rows(extras={(3, 1): P})),  # 17 plate
        _spec(_pillar_rows(pillar_cols=(4, 6))),
        _spec(_lattice_rows(lattice_cols=(3, 5, 7))),
        _spec(_floor_rows(extras={(4, 1): PO})),  # 20 potion MAX_HP
    ]
    doorlinks = (
        DoorLink(plate_room=5, plate_col=2, plate_row=1, gate_room=5, gate_col=5, gate_row=1),
        DoorLink(plate_room=17, plate_col=3, plate_row=1, gate_room=5, gate_col=5, gate_row=1),
    )
    lvl = _build_level(
        number=11,
        name="The Tower II",
        specs=specs,
        grid=grid,
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
    grid = """
     1  2  3  4  5  6  7  8  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .
     .  .  .  .  .  .  .  9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24
    """
    specs = [
        _spec(
            _platform_rows(platform_cols=(4, 5), extras={(7, 1): S}),
            guards=(G_S(col=5, row=1, direction=-1, skill=6),),
        ),  # 1 spawn con plataforma + spike
        _spec(_split_rows(upper_cols=(0, 1, 2), extras={(3, 1): C, (6, 1): C})),
        _spec(
            _arena_rows(pillar_pair=(2, 7), extras={(2, 1): PO}),
            guards=(G_S(col=5, row=1, direction=-1, skill=7),),
        ),  # 3 arena
        _spec(
            _platform_rows(
                platform_cols=(3, 4, 5, 6), pit_cols=(6,), extras={(4, 2): L, (5, 2): L}
            ),
        ),
        _spec(_floor_rows(extras={(5, 1): M, (8, 1): PO})),  # 5 MIRROR fusion
        _spec(_split_rows(upper_cols=(6, 7, 8, 9), extras={(5, 2): L})),
        _spec(
            _arena_rows(pillar_pair=(1, 8), extras={(2, 1): S, (8, 1): S}),
            guards=(G_S(col=5, row=1, direction=-1, skill=11),),
        ),  # 7 ARENA VIZIER
        _spec(_floor_rows(extras={(7, 1): DL, (8, 1): DR})),  # 8 exit + drop a galería
        # Galería sub
        _spec(_lattice_rows(lattice_cols=(3, 6), extras={(5, 1): T})),
        _spec(_pillar_rows(pillar_cols=(4, 6))),
        _spec(_doortop_rows(doortop_cols=(3, 4, 5))),
        _spec(_balcony_rows(side="left")),
        _spec(_floor_rows(extras={(5, 1): P})),
        _spec(_floor_rows(extras={(4, 1): G})),
        _spec(_pillar_rows(pillar_cols=(3, 6))),
        _spec(_floor_rows(extras={(5, 1): PO})),
        # Cripta sub
        _spec(_floor_rows(extras={(5, 1): SK})),  # 17 skeleton
        _spec(_lattice_rows(lattice_cols=(3, 5, 7))),
        _spec(_floor_rows(extras={(4, 1): C, (6, 1): C})),
        _spec(
            _floor_rows(),
            guards=(G_S(col=5, row=1, direction=0, skill=8),),
        ),
        _spec(_floor_rows(extras={(5, 1): P})),  # 21 plate adicional
        _spec(_pillar_rows(pillar_cols=(4,), extras={(7, 1): T})),
        _spec(_floor_rows(extras={(5, 2): L})),
        _spec(_floor_rows(extras={(4, 1): PO})),  # 24 potion MAX_HP
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
        grid=grid,
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
    grid = """
     1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18
    """
    specs = [
        _spec(_floor_rows(extras={(3, 1): C, (5, 1): C, (7, 1): C})),
        _spec(_floor_rows(extras={(2, 1): S, (4, 1): S, (5, 2): L, (6, 1): S, (8, 1): S})),
        _spec(_floor_rows(pit_cols=(4, 5, 6), extras={(3, 1): S, (7, 1): S})),
        _spec(_lattice_rows(lattice_cols=(3, 6))),
        _spec(_platform_rows(platform_cols=(3, 4, 5, 6), pit_cols=(4, 5))),  # 5 plataforma
        _spec(_floor_rows(extras={(5, 1): C})),
        _spec(
            _split_rows(
                upper_cols=(0, 1, 2), lower_cols=(5, 6, 7, 8, 9), extras={(2, 1): S, (8, 1): S}
            ),
        ),
        _spec(_doortop_rows(doortop_cols=(4, 5))),
        _spec(_platform_rows(platform_cols=(2, 3, 4, 5, 6, 7), extras={(5, 2): L})),  # 9 viga
        _spec(_floor_rows(extras={(3, 1): C, (7, 1): C})),
        _spec(_balcony_rows(side="right")),
        _spec(_lattice_rows(lattice_cols=(3, 5, 7))),
        _spec(_arena_rows(pillar_pair=(3, 7), extras={(5, 1): T})),  # 13 arena
        _spec(_floor_rows(extras={(2, 1): S, (4, 1): S, (6, 1): S})),
        _spec(_pillar_rows(pillar_cols=(3, 7))),
        _spec(
            _split_rows(
                upper_cols=(0, 1, 2, 3), lower_cols=(6, 7, 8, 9), extras={(4, 1): C, (6, 1): C}
            ),
        ),
        _spec(_doortop_rows(doortop_cols=(3, 4, 5, 6))),
        _spec(_floor_rows(extras={(7, 1): DL, (8, 1): DR})),  # 18 exit
    ]
    return _build_level(
        number=13,
        name="Final Run",
        specs=specs,
        grid=grid,
        start_room=1,
        start_col=1,
        start_row=1,
    )


# ===========================================================================
# Nivel 14 — Ending  (3 salas — acceso + escaleras + cámara princesa)
# ===========================================================================
def _l14() -> Level:
    grid = """
     1  2  3
    """
    specs = [
        # Sala 1: pórtico de entrada con antorchas + plataforma alta
        _spec(
            _platform_rows(
                platform_cols=(3, 4, 5, 6),
                extras={(0, 1): T, (9, 1): T},
            ),
        ),
        # Sala 2: galería de escaleras (lattice) hacia el norte ceremonial
        _spec(
            _lattice_rows(
                lattice_cols=(3, 5, 7),
                extras={(2, 1): T, (5, 0): DT, (7, 1): T},
            ),
        ),
        # Sala 3: cámara real con la princesa
        _spec(
            _arena_rows(
                pillar_pair=(1, 8),
                extras={
                    (3, 1): T,
                    (5, 0): DT,
                    (7, 1): T,
                },
            ),
        ),
    ]
    events = (Event(EventKind.PRINCESS_REUNION, room=3),)
    return _build_level(
        number=14,
        name="Ending",
        specs=specs,
        grid=grid,
        start_room=1,
        start_col=1,
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
L14 cinemática 3-salas."""


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
