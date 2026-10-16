"""Los 14 niveles canónicos del POP1 — versión expandida 18-24 salas.

**Fuente**: walkthroughs comunidad (popot.org, gamefaqs, popuw.com) y
descripciones canónicas. No hay `LEVELS.DAT` original: estos layouts
son **fan-recreation fieles a la canon** — mismas mecánicas, eventos
narrativos, número de salas y progresión espacial, pero no byte-perfect.

Cada nivel se construye con :func:`_build_level` a partir de sus salas
dibujadas en ASCII (:func:`_ascii`, tres filas de diez tiles que usan
toda la altura: cornisas, plataformas, muros macizos, pasarelas altas)
**y un mapa de cuadrícula** (``grid``). El grid es un
string multilinea donde cada token es el id de una sala (o ``.`` para
vacío); los links N/S/E/W se derivan automáticamente de la adyacencia,
igual que en el juego original, donde las salas son ventanas sobre un
mapa continuo. Esto garantiza por construcción:

- links recíprocos (si A está al este de B, B está al oeste de A),
- geometría planar (ninguna sala ocupa dos posiciones),
- que caer al sur / trepar al norte siempre lleva a la sala correcta.

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
# RoomSpec — declaración compacta de una sala (los links vienen del grid)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _RoomSpec:
    """Spec compacta para construir una sala dentro de un nivel."""

    rows: tuple[list[Tile | int], list[Tile | int], list[Tile | int]]
    guards: tuple[GuardSpawn, ...] = ()
    fg_modifiers: tuple[tuple[tuple[int, int], int], ...] = ()
    canonical: bool = False
    """Ya en geometría canon (sala ASCII): los items están en la fila que
    pisan, los guards en su fila real y no se perfora el techo."""


# ---------------------------------------------------------------------------
# Salas dibujadas en ASCII (geometría canon directa, las 3 filas en juego)
# ---------------------------------------------------------------------------

_ASCII: dict[str, tuple[Tile, int]] = {
    ".": (E, 0),
    "_": (F, 0),
    "#": (W, 0),
    "L": (L, 0),
    "S": (S, 0),
    "G": (G, 0),
    "P": (P, 0),
    "c": (CL, 0),
    "X": (C, 0),
    "T": (T, 0),
    "h": (PO, int(PotionType.HEAL)),
    "H": (PO, int(PotionType.MAX_HP)),
    "v": (PO, int(PotionType.POISON)),
    "f": (PO, int(PotionType.FLOAT)),
    "y": (PO, int(PotionType.TIME)),
    "e": (PO, 0),
    "k": (SK, 0),
    "M": (M, 0),
    "s": (SW, 0),
    "D": (DL, 0),
    "d": (DR, 0),
    "I": (PI, 0),
    "B": (BP_B, 0),
    "b": (BP_T, 0),
    "^": (DT_F, 0),
    "t": (DT, 0),
    "z": (Tile.DEBRIS, 0),
    "|": (LP, 0),
    "[": (BL, 0),
    "]": (BR, 0),
    "=": (LD, 0),
    "-": (LS, 0),
}
"""Leyenda de las salas ASCII: ``.`` aire, ``_`` suelo, ``#`` muro,
``L`` losa suelta, ``S`` pinchos, ``G`` reja, ``P`` placa que abre,
``c`` placa que cierra, ``X`` cuchillas, ``T`` antorcha, ``h``/``H``/
``v``/``f``/``y``/``e`` pociones (vida, vida máxima, veneno, pluma,
tiempo, frasco vacío), ``k`` esqueleto,
``M`` espejo, ``s`` espada, ``D``/``d`` puerta de salida, ``I`` columna,
``B``/``b`` columna grande (base/capitel), ``^`` dintel con suelo, ``t``
dintel, ``z`` cascotes, ``|`` celosía, ``[``/``]`` balcón, ``=``/``-``
celosías."""


def _ascii(top: str, mid: str, bot: str, *, guards: tuple[GuardSpawn, ...] = ()) -> _RoomSpec:
    """Sala desde tres filas de 10 caracteres (ver ``_ASCII``). Los
    guards se dan en su fila real (la del suelo que pisan)."""
    rows: list[list[Tile | int]] = []
    mods: list[tuple[tuple[int, int], int]] = []
    for r, line in enumerate((top, mid, bot)):
        if len(line) != SCREEN_TILECOUNT_X:
            raise ValueError(f"fila ASCII de {len(line)} caracteres: {line!r}")
        row: list[Tile | int] = []
        for c, ch in enumerate(line):
            if ch not in _ASCII:
                raise ValueError(f"carácter ASCII desconocido {ch!r} en {line!r}")
            tile, mod = _ASCII[ch]
            row.append(tile)
            if mod:
                mods.append(((c, r), mod))
        rows.append(row)
    return _RoomSpec(
        rows=(rows[0], rows[1], rows[2]),
        guards=guards,
        fg_modifiers=tuple(mods),
        canonical=True,
    )


def _carve_vertical_openings(
    rooms: tuple[Room, ...], keep: frozenset[int] = frozenset()
) -> tuple[Room, ...]:
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
        if not south_id or south_id not in by_id or south_id in keep:
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


_ROW1_ITEMS: frozenset[Tile] = frozenset(
    {
        Tile.POTION,
        Tile.SWORD,
        Tile.OPENER,
        Tile.CLOSER,
        Tile.TORCH,
        Tile.SPIKE,
        Tile.CHOMPER,
        Tile.SKELETON,
        Tile.MIRROR,
        Tile.GATE,
        Tile.LEVEL_DOOR_LEFT,
        Tile.LEVEL_DOOR_RIGHT,
    }
)


def _canonize_rows(
    rooms: tuple[Room, ...],
    doorlinks: tuple[DoorLink, ...],
    keep: frozenset[int] = frozenset(),
) -> tuple[tuple[Room, ...], tuple[DoorLink, ...], dict[tuple[int, int, int], int]]:
    """Geometría canon POP1: el char OCUPA la celda del suelo que pisa.

    Los specs fan colocan los items "en el aire" de la fila 1 sobre un
    suelo en la fila 2; en el original esos items SON tiles-suelo de la
    fila 2 (potion, plate, gate, chomper... todos `tile_is_floor`). Esta
    pasada baja cada item de la fila 1 a la fila 2 cuando debajo hay
    FLOOR liso, y devuelve el mapa de coordenadas movidas para
    recolocar doorlinks, eventos y pociones.
    """
    moved: dict[tuple[int, int, int], int] = {}
    new_rooms = []
    for room in rooms:
        if room.id in keep:
            new_rooms.append(room)
            continue
        fg = list(room.fg)
        for c in range(SCREEN_TILECOUNT_X):
            up, down = fg[1 * SCREEN_TILECOUNT_X + c], fg[2 * SCREEN_TILECOUNT_X + c]
            if Tile(up & 0x1F) in _ROW1_ITEMS and Tile(down & 0x1F) is Tile.FLOOR:
                fg[2 * SCREEN_TILECOUNT_X + c] = up
                fg[1 * SCREEN_TILECOUNT_X + c] = encode_tile(Tile.EMPTY, 0)
                moved[(room.id, c, 1)] = 2
        new_rooms.append(
            Room(
                id=room.id,
                fg=tuple(fg),
                bg=room.bg,
                link_n=room.link_n,
                link_s=room.link_s,
                link_e=room.link_e,
                link_w=room.link_w,
                # Los guards pisan la fila del suelo (canon)
                guards=tuple(
                    GuardSpawn(
                        col=g.col,
                        row=min(2, g.row + 1),
                        direction=g.direction,
                        skill=g.skill,
                        color=g.color,
                    )
                    for g in room.guards
                ),
            )
        )
    new_links = tuple(
        DoorLink(
            plate_room=d.plate_room,
            plate_col=d.plate_col,
            plate_row=moved.get((d.plate_room, d.plate_col, d.plate_row), d.plate_row),
            gate_room=d.gate_room,
            gate_col=d.gate_col,
            gate_row=moved.get((d.gate_room, d.gate_col, d.gate_row), d.gate_row),
        )
        for d in doorlinks
    )
    return tuple(new_rooms), new_links, moved


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
    """``start_row`` es la fila del spec; si la sala de inicio es ASCII
    (canónica) es ya la fila que pisa el kid."""
    links = _grid_links(grid, len(specs))
    keep = frozenset(i + 1 for i, spec in enumerate(specs) if spec.canonical)
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
    rooms = _carve_vertical_openings(rooms, keep)
    rooms, doorlinks, _moved = _canonize_rows(rooms, doorlinks, keep)
    return Level(
        number=number,
        name=name,
        rooms=rooms,
        start_room=start_room,
        start_col=start_col,
        # El kid pisa la fila del suelo (canon): spawn una fila más abajo
        start_row=start_row if start_room in keep else min(2, start_row + 1),
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
    """Mazmorra en tres pisos (6x3).

    Piso alto: la celda, las losas sueltas (si las pisas caes a la 7) y el
    pozo de la sala 3, que baja al piso medio. Por encima del pozo, un
    salto con carrerilla lleva a la galería 4-6: pinchos y una losa que
    cae a la sala 12 con la poción grande.

    Piso medio: la espada está en una cornisa de la sala 8; su placa abre
    la reja de la 9 (hay que correr: se cierra sola). El primer guardia
    vigila la 10. En la 11 la única salida es la losa suelta.

    Piso bajo: hay que cruzar guardia, pinchos y cuchillas hasta la placa
    de la sala 13, que abre la puerta de salida de la 18, y volver."""
    G_S = GuardSpawn  # noqa: N806 — alias local de tipo
    grid = """
     1  2  3  4  5  6
     7  8  9 10 11 12
    13 14 15 16 17 18
    """
    specs = [
        # --- Piso alto ----------------------------------------------------
        _ascii("##########", "#.........", "#___LL____"),  # 1 la celda
        _ascii("##########", "...^^h....", "__T_______"),  # 2 cornisa con poción
        _ascii("##########", "..........", "____...___"),  # 3 el pozo
        _ascii("##########", "...^^.....", "_______T__"),  # 4 galería alta
        _ascii("##########", "..........", "___S_S____"),  # 5 pinchos
        _ascii("##########", ".........#", "__y_PL___#"),  # 6 tiempo, placa del tesoro, losa → 12
        # --- Piso medio ---------------------------------------------------
        _ascii("##.___####", "..........", "#____T____"),  # 7 bajo las losas
        _ascii("##########", "..s_......", "____T__P__"),  # 8 la espada y la placa
        _ascii("###.___###", "..........", "______G___"),  # 9 la reja
        _ascii(  # 10 sala de guardia
            "##########",
            "#........#",
            "__T_______",
            guards=(G_S(col=7, row=2, direction=-1, skill=0),),
        ),
        _ascii("##########", "..........", "___X__L__#"),  # 11 cuchilla y la losa: no te pares
        _ascii(
            "###..__###", "..........", "#H_G______"
        ),  # 12 el tesoro tras la reja: se cae desde la 6
        # --- Piso bajo ----------------------------------------------------
        _ascii("##########", "#...^^h...", "#__P______"),  # 13 placa de la salida
        _ascii("##########", "..........", "____XX____"),  # 14 cuchillas
        _ascii("##########", "..........", "___S_S____"),  # 15 pinchos
        _ascii(  # 16 segundo guardia
            "##########",
            "..........",
            "____T_____",
            guards=(G_S(col=5, row=2, direction=0, skill=0),),
        ),
        _ascii("####___.##", "..........", "_S_T______"),  # 17 pinchos por el lado del guardia
        _ascii(  # 18 la salida: el portero
            "##########",
            ".........#",
            "___h___Dd#",
            guards=(G_S(col=5, row=2, direction=-1, skill=0),),
        ),
    ]
    doorlinks = (
        DoorLink(plate_room=8, plate_col=7, plate_row=2, gate_room=9, gate_col=6, gate_row=2),
        DoorLink(plate_room=13, plate_col=3, plate_row=2, gate_room=18, gate_col=7, gate_row=2),
        DoorLink(plate_room=6, plate_col=4, plate_row=2, gate_room=12, gate_col=1, gate_row=2),
    )
    return _build_level(
        number=1,
        name="The Dungeon",
        specs=specs,
        grid=grid,
        start_room=1,
        start_col=1,
        start_row=2,
        start_direction=0,
        doorlinks=doorlinks,
    )


# ===========================================================================
# Nivel 2 — The Guards  (20 salas)
# ===========================================================================
# Dos filas de patios: la norte con guards de skill 1-3 y trampas; la sur
# con el exit (sala 18) y las potions bonus al este del exit (19-20).
# El descenso es por los loose floors del spawn (sala 1 → 11).


def _l2() -> Level:
    """Cuerpo de guardia (10x2). Arriba, barracones: guardia, cuchillas,
    la reja de la sala 4 (su placa está en la misma sala: corre) y el pozo
    de la 5, que baja al patio. Abajo, hacia el este: la reja de la sala
    20 la abre la placa de la 18, pero la placa de cierre de la 19 la
    vuelve a cerrar si la pisas (sáltala); la losa de la 8 cae sobre la
    placa y la deja abierta para siempre. La puerta de salida se abre
    con la placa de la sala 9, a la que se sube por la cornisa de la 20
    y se vuelve dejándose caer por el agujero de la 10. Al oeste del
    patio, una galería con pinchos guarda la poción grande."""
    G_S = GuardSpawn  # noqa: N806
    grid = """
     1  2  3  4  5  6  7  8  9 10
    11 12 13 14 15 16 17 18 19 20
    """
    specs = [
        # --- Barracones ---------------------------------------------------
        _ascii("##########", "#.........", "#___T_____"),  # 1 inicio
        _ascii(  # 2 primer guardia
            "##########",
            "..........",
            "__T____T__",
            guards=(G_S(col=5, row=2, direction=-1, skill=1),),
        ),
        _ascii("##########", "..........", "__X_X_X___"),  # 3 tres cuchillas
        _ascii("##########", "..........", "_P__c___G_"),  # 4 placa, cierre y reja: salta y corre
        _ascii("##########", ".........#", "___...___#"),  # 5 el pozo
        _ascii("##########", "#..^^.....", "#__v______"),  # 6 fondo: frasco envenenado
        _ascii("##########", "..........", "___vh_____"),  # 7 veneno junto a la cura
        _ascii("##########", "..........", "____L_____"),  # 8 losa sobre la placa de 18
        _ascii(  # 9 placa de la salida, vigilada
            "##########",
            "..........",
            "__P___T___",
            guards=(G_S(col=6, row=2, direction=0, skill=3),),
        ),
        _ascii("##########", ".....^^...", "___.______"),  # 10 agujero a la 20
        # --- Patio --------------------------------------------------------
        _ascii("##########", "#.........", "#__H______"),  # 11 la poción grande
        _ascii("##########", "...^^.....", "_S__SS____"),  # 12 pinchos dobles
        _ascii("##########", "..........", "___T______"),  # 13
        _ascii(  # 14 guardia entre la cuchilla y los pinchos
            "##########",
            "..........",
            "__X___S___",
            guards=(G_S(col=4, row=2, direction=-1, skill=2),),
        ),
        _ascii("##.___####", "..........", "____T_____"),  # 15 bajo el pozo
        _ascii(  # 16 guardia
            "##########",
            "..........",
            "_____T____",
            guards=(G_S(col=6, row=2, direction=-1, skill=2),),
        ),
        _ascii("##########", "..........", "__X___X___"),  # 17 cuchillas
        _ascii("####.#####", "......^^..", "____P_____"),  # 18 la placa de la reja
        _ascii("##########", "..........", "____c___T_"),  # 19 placa de cierre: sáltala
        _ascii(  # 20 reja, cornisa, el portero y la salida
            "##._.#####",
            "....^^....",
            "_G______Dd",
            guards=(G_S(col=5, row=2, direction=-1, skill=3),),
        ),
    ]
    doorlinks = (
        DoorLink(plate_room=4, plate_col=1, plate_row=2, gate_room=4, gate_col=8, gate_row=2),
        DoorLink(plate_room=4, plate_col=4, plate_row=2, gate_room=4, gate_col=8, gate_row=2),
        DoorLink(plate_room=18, plate_col=4, plate_row=2, gate_room=20, gate_col=1, gate_row=2),
        DoorLink(plate_room=19, plate_col=4, plate_row=2, gate_room=20, gate_col=1, gate_row=2),
        DoorLink(plate_room=9, plate_col=2, plate_row=2, gate_room=20, gate_col=8, gate_row=2),
    )
    return _build_level(
        number=2,
        name="The Guards",
        specs=specs,
        grid=grid,
        start_room=1,
        start_col=1,
        start_row=2,
        doorlinks=doorlinks,
    )


# ===========================================================================
# Nivel 3 — The Skeleton  (18 salas)
# ===========================================================================
# Fila norte 1-9; sub-piso 10-17 (el pit de la sala 3 cae en los loose de
# la 10); estancias secretas 17-18 bajo la sala 9 del plate.


def _l3() -> Level:
    """Osario. El esqueleto despierta al pasar junto a él. La reja de la
    sala 7 sólo se abre dejando caer la losa de la sala 4 sobre la placa
    de la sala 12 (corre por encima: cae cuando ya has pasado). El pozo
    de la 9 baja a la 17, cuya losa lleva a la cripta (18): la placa de
    la salida y la poción grande; se vuelve a subir por la cornisa. Las
    losas de la 2 y el pozo de la 3 dan a una galería baja (11, 10, 12,
    13) de la que se vuelve trepando."""
    G_S = GuardSpawn  # noqa: N806
    grid = """
     1  2  3  4  5  6  7  8  9
     . 11 10 12 13 14 15 16 17
     .  .  .  .  .  .  .  . 18
    """
    specs = [
        # --- Galería alta -------------------------------------------------
        _ascii("##########", "#.........", "#___k_____"),  # 1 el esqueleto
        _ascii("##########", "..........", "_____L____"),  # 2 losa → 11
        _ascii("##########", "..........", "____..____"),  # 3 pozo → 10
        _ascii("##########", "...^^.....", "_____L____"),  # 4 losa sobre la placa de 12
        _ascii("##########", "..........", "___X__X___"),  # 5 cuchillas
        _ascii(  # 6 arena
            "##########",
            "..b....b..",
            "__B____B__",
            guards=(G_S(col=5, row=2, direction=-1, skill=2),),
        ),
        _ascii("##########", "..........", "__G___T___"),  # 7 la reja
        _ascii("##########", "..........", "___S_S_S__"),  # 8 pinchos triples
        _ascii("##########", "..........", "____...___"),  # 9 pozo → 17
        # --- Galería baja -------------------------------------------------
        _ascii("###.__.###", "..^^......", "__________"),  # 10 bajo el pozo; se sube
        _ascii("####__.###", "..^^......", "#___h_____"),  # 11 bajo la losa; se sube
        _ascii(  # 12 la placa de la reja y su portero
            "#####.####",
            "..........",
            "_____P____",
            guards=(G_S(col=2, row=2, direction=0, skill=2),),
        ),
        _ascii("##########", ".........#", "_____y___#"),  # 13 poción del tiempo
        _ascii("##########", "#........#", "#__X_X____"),  # 14 cuchillas dobles
        _ascii(  # 15 guardia
            "##########",
            "..........",
            "___T______",
            guards=(G_S(col=5, row=2, direction=0, skill=2),),
        ),
        _ascii(  # 16 la salida: el portero
            "##########",
            "..........",
            "__h___Dd__",
            guards=(G_S(col=4, row=2, direction=-1, skill=3),),
        ),
        _ascii("####___.##", "..........", "_______L__"),  # 17 bajo el pozo; losa → 18
        # --- Cripta -------------------------------------------------------
        _ascii("####____.#", "........^^", "HG_P___P__"),  # 18 placa de la salida; tesoro tras reja
    ]
    doorlinks = (
        DoorLink(plate_room=12, plate_col=5, plate_row=2, gate_room=7, gate_col=2, gate_row=2),
        DoorLink(plate_room=18, plate_col=3, plate_row=2, gate_room=16, gate_col=6, gate_row=2),
        DoorLink(plate_room=18, plate_col=7, plate_row=2, gate_room=18, gate_col=1, gate_row=2),
    )
    events = (Event(EventKind.SKELETON_WAKE, room=1, col=2),)
    return _build_level(
        number=3,
        name="The Skeleton",
        specs=specs,
        grid=grid,
        start_room=1,
        start_col=1,
        start_row=2,
        events=events,
        doorlinks=doorlinks,
    )


# ===========================================================================
# Nivel 4 — The Mirror  (20 salas)
# ===========================================================================
# Fila norte 1-10 con el MIRROR en 5 y el exit en 10; sub-piso 11-18
# (el pit de la 3 cae en la potion poison de la 11); rincón 19-20.


def _l4() -> Level:
    """Galería del espejo. Arriba: pinchos, la placa de la 4 abre la reja
    de la 6 (hay que cruzar corriendo la sala del espejo, donde nace la
    sombra), cuchillas, guardia, el pozo de la 9. Abajo: la 17 lleva a la
    18, cuya losa cae a la 20 — placa de la salida y poción de pluma — y
    se vuelve por la escalera de la 19. La salida está en la 10, a la que
    se trepa desde la 18. Por el pozo de la 3 se baja a la galería oeste
    (11-16): guardia, cuchillas, una reja con placa de cierre y una
    escalera que sube a la 8."""
    G_S = GuardSpawn  # noqa: N806
    grid = """
     1  2  3  4  5  6  7  8  9 10
     .  . 11 12 13 14 15 16 17 18
     .  .  .  .  .  .  .  . 19 20
    """
    specs = [
        # --- Galería alta -------------------------------------------------
        _ascii("##########", "#.........", "#___T_____"),  # 1
        _ascii(  # 2 guardia sobre los pinchos: pelea a paso corto
            "##########",
            "..........",
            "__S_S_S___",
            guards=(G_S(col=7, row=2, direction=-1, skill=3),),
        ),
        _ascii("##########", "......^^..", "___.._____"),  # 3 pozo → 11
        _ascii("##########", "..........", "____T___P_"),  # 4 placa de la reja
        _ascii("_t__tt__t_", "..........", "_____M____"),  # 5 el espejo
        _ascii("##########", "..........", "_G___T____"),  # 6 la reja: corre
        _ascii("##########", "..........", "___X_X____"),  # 7 cuchillas
        _ascii(  # 8 guardia; agujero por el que se sube desde la 16
            "##########",
            "..b.......",
            "______.___",
            guards=(G_S(col=3, row=2, direction=0, skill=3),),
        ),
        _ascii("##########", "^^........", "____...___"),  # 9 pozo → 17
        _ascii("##########", "..........", "____.__Dd_"),  # 10 la salida
        # --- Galería oeste ------------------------------------------------
        _ascii(
            "##.__#####", "..........", "#HG_P_hX__"
        ),  # 11 bajo el pozo: tesoro, reja, placa, poción y cuchilla
        _ascii("##########", "..........", "___X_X_X__"),  # 12 cuchillas triples
        _ascii("##########", "..........", "[_v_S_____"),  # 13 balcón, veneno
        _ascii(  # 14 guardia
            "##########",
            "..........",
            "___T______",
            guards=(G_S(col=5, row=2, direction=-1, skill=3),),
        ),
        _ascii("##########", "..........", "__P__c__G_"),  # 15 reja, placa y cierre
        _ascii("#####._.##", "....^^....", "__________"),  # 16 escalera a la 8
        # --- Galería este -------------------------------------------------
        _ascii("###.___###", "..........", "____.___T_"),  # 17 bajo el pozo; agujero → 19
        _ascii("###._.####", "..^^......", "_______L__"),  # 18 escalera a la 10; losa → 20
        _ascii("###._.####", "..^^......", "__________"),  # 19 escalera a la 17
        _ascii(  # 20 placa de la salida, pluma y su portero
            "#####___##",
            "..........",
            "__P___f_T_",
            guards=(G_S(col=5, row=2, direction=-1, skill=3),),
        ),
    ]
    doorlinks = (
        DoorLink(plate_room=4, plate_col=8, plate_row=2, gate_room=6, gate_col=1, gate_row=2),
        DoorLink(plate_room=15, plate_col=2, plate_row=2, gate_room=15, gate_col=8, gate_row=2),
        DoorLink(plate_room=15, plate_col=5, plate_row=2, gate_room=15, gate_col=8, gate_row=2),
        DoorLink(plate_room=20, plate_col=2, plate_row=2, gate_room=10, gate_col=7, gate_row=2),
        DoorLink(plate_room=11, plate_col=4, plate_row=2, gate_room=11, gate_col=2, gate_row=2),
    )
    events = (Event(EventKind.SHADOW_MIRROR, room=5, col=5),)
    return _build_level(
        number=4,
        name="The Mirror",
        specs=specs,
        grid=grid,
        start_room=1,
        start_col=1,
        start_row=2,
        events=events,
        doorlinks=doorlinks,
    )


# ===========================================================================
# Nivel 5 — The Thief  (20 salas)
# ===========================================================================
def _l5() -> Level:
    """Salón del ladrón. La sombra roba la poción de la sala 4. La placa
    de la 5 abre la reja de la 7; tras ella, el pozo baja al ala este
    (14-20): celosías, cuchillas, guardia y, al fondo, la placa de la
    salida junto a la poción del tiempo. Se vuelve por la escalera de la
    14 hasta la 7, y por la arena y la 9 a la salida (10). Las losas de
    la 2 caen al ala oeste (11-13): balcón y poción; se sube por la 12."""
    G_S = GuardSpawn  # noqa: N806
    grid = """
     1  2  3  4  5  6  7  8  9 10  .  .  .
    11 12 13  .  .  . 14 15 16 17 18 19 20
    """
    specs = [
        # --- Ala norte ----------------------------------------------------
        _ascii("##########", "#.........", "#_____T___"),  # 1
        _ascii("##########", "..........", "___LLL____"),  # 2 losas → 12
        _ascii("##########", "^^^.......", "______S___"),  # 3
        _ascii("_t__t__t__", "...^.^....", "____h_____"),  # 4 la poción robada
        _ascii("##########", "..........", "__P_____L_"),  # 5 placa; losa al vacío
        _ascii("##########", "..........", "__c_X_____"),  # 6 placa de cierre ante la cuchilla
        _ascii("##########", "..........", "___G_...__"),  # 7 reja y pozo → 14
        _ascii(  # 8 arena
            "##########",
            "..b....b..",
            "__B____B__",
            guards=(G_S(col=5, row=2, direction=-1, skill=3),),
        ),
        _ascii("##########", "....^.^...", "_____T____"),  # 9
        _ascii(  # 10 la salida
            "##########",
            ".........#",
            "_______Dd#",
            guards=(G_S(col=3, row=2, direction=0, skill=3),),
        ),
        # --- Ala oeste ----------------------------------------------------
        _ascii("##########", "#.........", "#___k_____"),  # 11 huesos
        _ascii(  # 12 bajo las losas; guardia; se sube
            "###___.###",
            ".^^.......",
            "__________",
            guards=(G_S(col=6, row=2, direction=-1, skill=3),),
        ),
        _ascii(
            "##########", "..........", "__hPSG_H_]"
        ),  # 13 balcón: placa, pinchos, reja y tesoro
        # --- Ala este -----------------------------------------------------
        _ascii("####.___.#", "...^^.....", "__________"),  # 14 bajo el pozo; se sube
        _ascii("##########", "...|.|.|..", "__________"),  # 15 celosías
        _ascii(  # 16 guardia entre la cuchilla y los pinchos
            "##########",
            "..........",
            "___X_S____",
            guards=(G_S(col=7, row=2, direction=-1, skill=3),),
        ),
        _ascii("##########", "....^^....", "__________"),  # 17
        _ascii("##########", "..........", "___T___T__"),  # 18
        _ascii("##########", "....b.b...", "____B_B___"),  # 19
        _ascii(  # 20 placa de la salida y poción del tiempo
            "##########",
            ".........#",
            "_P__y____#",
            guards=(G_S(col=6, row=2, direction=-1, skill=3),),
        ),
    ]
    doorlinks = (
        DoorLink(plate_room=5, plate_col=2, plate_row=2, gate_room=7, gate_col=3, gate_row=2),
        DoorLink(plate_room=6, plate_col=2, plate_row=2, gate_room=7, gate_col=3, gate_row=2),
        DoorLink(plate_room=20, plate_col=1, plate_row=2, gate_room=10, gate_col=7, gate_row=2),
        DoorLink(plate_room=13, plate_col=3, plate_row=2, gate_room=13, gate_col=5, gate_row=2),
    )
    events = (Event(EventKind.SHADOW_STEAL, room=4),)
    return _build_level(
        number=5,
        name="The Thief",
        specs=specs,
        grid=grid,
        start_room=1,
        start_col=1,
        start_row=2,
        events=events,
        doorlinks=doorlinks,
    )


# ===========================================================================
# Nivel 6 — The Steps  (18 salas)
# ===========================================================================
def _l6() -> Level:
    """La escalinata. Se empieza ante un foso que se salta con carrerilla
    (la sombra salta contigo). En la 2, la placa abre la reja pero la
    placa de cierre del medio la cierra: sáltala. Cuchillas, guardia,
    pinchos; en la 6 la losa cae sobre la placa de la 11 y deja abierta
    para siempre la reja de la 8 (si la pisas, caes tres pisos). El pozo
    de la 7 baja a la terraza (11-18): balcón, pinchos, guardia y, al
    fondo, la placa de la salida con la poción grande. Se vuelve por la
    escalera de la 12."""
    G_S = GuardSpawn  # noqa: N806
    grid = """
     1  2  3  4  5  6  7  8  9 10  .  .  .
     .  .  .  .  . 11 12 13 14 15 16 17 18
    """
    specs = [
        # --- Terraza alta -------------------------------------------------
        _ascii("##########", "..........", "___...____"),  # 1 el foso
        _ascii("##########", "..........", "__P__c_G__"),  # 2 placa, cierre y reja
        _ascii("##########", "..........", "____X_____"),  # 3 cuchilla
        _ascii(  # 4 guardia y pinchos
            "##########",
            "..........",
            "_____S_S__",
            guards=(G_S(col=2, row=2, direction=0, skill=4),),
        ),
        _ascii("##########", "...b...b..", "___B___B__"),  # 5
        _ascii("##########", "....^^^...", "_____L____"),  # 6 losa sobre la placa de 11
        _ascii("##########", "...|.|.|..", "____..____"),  # 7 pozo → 12
        _ascii("##########", "^^^.......", "_____G____"),  # 8 la reja
        _ascii("##########", "..........", "___X______"),  # 9 cuchilla
        _ascii(  # 10 la salida
            "##########",
            ".........#",
            "_______Dd#",
            guards=(G_S(col=3, row=2, direction=0, skill=4),),
        ),
        # --- Terraza baja -------------------------------------------------
        _ascii(
            "#####.####", "..........", "#_hv_P____"
        ),  # 11 la placa de la reja; veneno junto a la cura
        _ascii(  # 12 bajo el pozo: un guardia te espera al caer; se sube
            "###.__.###",
            "..^^......",
            "__________",
            guards=(G_S(col=8, row=2, direction=-1, skill=4),),
        ),
        _ascii("##########", "..........", "[_________"),  # 13 balcón
        _ascii("##########", "..........", "___S_S_S__"),  # 14 pinchos
        _ascii(  # 15 guardia
            "##########",
            "..........",
            "_____T____",
            guards=(G_S(col=5, row=2, direction=-1, skill=4),),
        ),
        _ascii(  # 16 guardia bajo la cornisa
            "##########",
            "....^^^...",
            "__________",
            guards=(G_S(col=7, row=2, direction=-1, skill=4),),
        ),
        _ascii("##########", "..........", "_____X____"),  # 17 cuchilla
        _ascii(
            "##########", ".........#", "__P_GXH__#"
        ),  # 18 placa de la salida; reja, cuchilla y tesoro
    ]
    doorlinks = (
        DoorLink(plate_room=2, plate_col=2, plate_row=2, gate_room=2, gate_col=7, gate_row=2),
        DoorLink(plate_room=2, plate_col=5, plate_row=2, gate_room=2, gate_col=7, gate_row=2),
        DoorLink(plate_room=11, plate_col=5, plate_row=2, gate_room=8, gate_col=5, gate_row=2),
        DoorLink(plate_room=18, plate_col=2, plate_row=2, gate_room=10, gate_col=7, gate_row=2),
        DoorLink(plate_room=18, plate_col=2, plate_row=2, gate_room=18, gate_col=4, gate_row=2),
    )
    events = (Event(EventKind.SHADOW_STEP, room=1, extra=43),)
    return _build_level(
        number=6,
        name="The Steps",
        specs=specs,
        grid=grid,
        start_room=1,
        start_col=1,
        start_row=2,
        events=events,
        doorlinks=doorlinks,
    )


# ===========================================================================
# Nivel 7 — The Mountains  (22 salas)  vertical-heavy
# ===========================================================================
# Tres pisos completos 7 salas + exit colgado al este del piso bajo.
# Descensos reales: loose del spawn (1→8), loose de la 9 (→16),
# potion bajo la arena 6 (→13) y trampa de chompers bajo la gate 7 (→14).


def _l7() -> Level:
    """Entrañas de la montaña (3 pisos). Arriba: pinchos, celosías, la
    placa de la 4 abre la reja de la 7 y su pozo baja al piso medio
    este (14-11): poción, pinchos y, en la 11, la placa de la salida y la
    losa que baja al piso inferior. El pozo del inicio cae al piso medio
    oeste (8-10): la poción de pluma justo antes de un pozo de tres
    pisos, y las losas de la 9; de allí sólo se vuelve trepando a la 1.
    Abajo, hacia el este: losas sobre el vacío, guardia, cuchillas y la
    salida (22)."""
    G_S = GuardSpawn  # noqa: N806
    grid = """
     1  2  3  4  5  6  7  .
     8  9 10 11 12 13 14  .
    15 16 17 18 19 20 21 22
    """
    specs = [
        # --- Piso alto ----------------------------------------------------
        _ascii("##########", "#.........", "#___..____"),  # 1 pozo → 8
        _ascii("##########", "..........", "___S_S____"),  # 2 pinchos
        _ascii("##########", "...|..|...", "__________"),  # 3 celosías
        _ascii("##########", "...^^.....", "_____P____"),  # 4 placa de la reja
        _ascii("##########", "....b..b..", "____B__B__"),  # 5
        _ascii(  # 6 arena
            "##########",
            "..b....b..",
            "__B____B__",
            guards=(G_S(col=5, row=2, direction=-1, skill=5),),
        ),
        _ascii("##########", ".........#", "__G__...__"),  # 7 reja y pozo → 14
        # --- Piso medio ---------------------------------------------------
        _ascii("##.___.###", ".^^.......", "#___f..___"),  # 8 pluma y pozo de 3 pisos
        _ascii("##########", "..........", "____LL____"),  # 9 losas → 16
        _ascii("##########", ".........#", "_XX_h_XX_#"),  # 10 fondo de saco: cuchillas dobles
        _ascii("##########", "#.........", "#_P____L__"),  # 11 placa de la salida; losa → 18
        _ascii("##########", "....b.....", "____B_____"),  # 12
        _ascii(  # 13 poción con guardia
            "##########",
            "...^^.....",
            "__S__h____",
            guards=(G_S(col=8, row=2, direction=-1, skill=5),),
        ),
        _ascii("####.___##", "..........", "____T_____"),  # 14 bajo el pozo
        # --- Piso bajo ----------------------------------------------------
        _ascii(
            "#####..###", "..........", "_G_y_T____"
        ),  # 15 fondo del pozo; tesoro de tiempo tras reja
        _ascii(
            "###.__.###", "..........", "____P_____"
        ),  # 16 bajo las losas: la losa cae sobre la placa
        _ascii("##########", "..........", "____LLL___"),  # 17 losas sobre el vacío
        _ascii("######_.##", "...|...|..", "_____T____"),  # 18 bajo la losa de la 11
        _ascii(  # 19 guardia
            "##########",
            "..........",
            "__________",
            guards=(G_S(col=4, row=2, direction=0, skill=5),),
        ),
        _ascii("##########", "...b..b...", "___B__B___"),  # 20
        _ascii(  # 21 guardia entre las cuchillas
            "##########",
            "....^^....",
            "__X___X___",
            guards=(G_S(col=4, row=2, direction=0, skill=5),),
        ),
        _ascii(  # 22 la salida
            "##########",
            ".........#",
            "_______Dd#",
            guards=(G_S(col=3, row=2, direction=0, skill=5),),
        ),
    ]
    doorlinks = (
        DoorLink(plate_room=4, plate_col=5, plate_row=2, gate_room=7, gate_col=2, gate_row=2),
        DoorLink(plate_room=11, plate_col=2, plate_row=2, gate_room=22, gate_col=7, gate_row=2),
        DoorLink(plate_room=16, plate_col=4, plate_row=2, gate_room=15, gate_col=1, gate_row=2),
    )
    return _build_level(
        number=7,
        name="The Mountains",
        specs=specs,
        grid=grid,
        start_room=1,
        start_col=1,
        start_row=2,
        doorlinks=doorlinks,
    )


# ===========================================================================
# Nivel 8 — The Caverns  (20 salas)
# ===========================================================================
def _l8() -> Level:
    """Cavernas. El pozo del inicio baja a la galería inferior (11-20):
    cuchillas, losas sobre el vacío, la placa de la salida (14), guardias
    y, al fondo, la poción grande y la escalera que sube a la 10. Allí la
    reja no tiene placa: la abre el ratón cuando llegas. Desde la 10, la
    galería alta (2-9) guarda pociones tras más trampas."""
    G_S = GuardSpawn  # noqa: N806
    grid = """
     1  2  3  4  5  6  7  8  9 10
    11 12 13 14 15 16 17 18 19 20
    """
    specs = [
        # --- Galería alta -------------------------------------------------
        _ascii("##########", "#........#", "#___...__#"),  # 1 inicio: pozo → 11
        _ascii("##########", "#.........", "#__L_X____"),  # 2 fondo de saco
        _ascii("##########", "....|.|...", "__________"),  # 3 celosías
        _ascii("##########", "..........", "____LLLL__"),  # 4 losas cuádruples → 14
        _ascii("##########", "...b..b...", "___B__B___"),  # 5
        _ascii("##########", "..........", "_______S__"),  # 6 pinchos
        _ascii("##########", "..........", "_____X____"),  # 7 cuchilla
        _ascii("##########", "...^^.....", "____h_____"),  # 8 poción
        _ascii("##########", "..........", "[____T____"),  # 9 balcón
        _ascii("##########", "..........", "_____._GDd"),  # 10 reja del ratón y salida
        # --- Galería baja -------------------------------------------------
        _ascii(  # 11 bajo el pozo: el primer guardia te espera al caer
            "###.___.##",
            "..........",
            "#_________",
            guards=(G_S(col=8, row=2, direction=-1, skill=4),),
        ),
        _ascii("###_######", "..........", "___X__X___"),  # 12 cuchillas
        _ascii("##########", "..........", "__L__S____"),  # 13 losa al vacío, pinchos
        _ascii(  # 14 placa de la salida y su portero
            "####.___##",
            "..........",
            "____P_____",
            guards=(G_S(col=7, row=2, direction=-1, skill=4),),
        ),
        _ascii(  # 15 guardia
            "##########",
            "...b..b...",
            "___B__B___",
            guards=(G_S(col=4, row=2, direction=0, skill=4),),
        ),
        _ascii(
            "##########", "..........", "____k_L___"
        ),  # 16 huesos: despierta el esqueleto; losa al vacío
        _ascii("##########", "....^^....", "_____XX___"),  # 17 cuchillas dobles
        _ascii("##########", "...|.|.|..", "__________"),  # 18 celosías
        _ascii(  # 19 guardia
            "##########",
            "..........",
            "__________",
            guards=(G_S(col=5, row=2, direction=-1, skill=4),),
        ),
        _ascii("####._.###", "...^^....#", "__H______#"),  # 20 poción grande; escalera a 10
    ]
    doorlinks = (
        DoorLink(plate_room=14, plate_col=4, plate_row=2, gate_room=10, gate_col=8, gate_row=2),
    )
    events = (
        Event(EventKind.MOUSE_APPEAR, room=10),
        Event(EventKind.SKELETON_WAKE, room=16, col=3),
    )
    return _build_level(
        number=8,
        name="The Caverns",
        specs=specs,
        grid=grid,
        start_room=1,
        start_col=1,
        start_row=2,
        events=events,
        doorlinks=doorlinks,
    )


# ===========================================================================
# Nivel 9 — The Tomb  (20 salas)
# ===========================================================================
# Fila norte 1-10 con el exit en 10; sótano 11-20 bajo ella. La potion
# MAX_HP (19) queda justo bajo el exit; 20 es el rincón final.


def _l9() -> Level:
    """La tumba. La placa de la sala 3 abre la reja de la 5, pero en la 4
    hay una placa de cierre entre las columnas: sáltala y corre. Guardia,
    celosías y el pozo de la 8, que baja a la cripta: hacia el oeste, la
    placa de la salida (16) tras celosías y cuchillas; hacia el este,
    guardia, poción grande y la poción del tiempo. Se vuelve por la
    escalera de la 17 a la 8, y pinchos y cuchillas hasta la salida."""
    G_S = GuardSpawn  # noqa: N806
    grid = """
     1  2  3  4  5  6  7  8  9 10  .
     . 11 12 13 14 15 16 17 18 19 20
    """
    specs = [
        # --- Nivel superior -----------------------------------------------
        _ascii("##########", "#.........", "#___k_L___"),  # 1 losa al vacío
        _ascii("##########", "..........", "___S_S_S__"),  # 2 pinchos
        _ascii("##########", "....b.....", "____B___P_"),  # 3 placa de la reja
        _ascii("##########", "..b....b..", "__B_c__Bh_"),  # 4 placa de cierre: sáltala
        _ascii("##########", "..........", "______G___"),  # 5 la reja
        _ascii(  # 6 guardia
            "##########",
            "..........",
            "_____T____",
            guards=(G_S(col=5, row=2, direction=-1, skill=5),),
        ),
        _ascii("##########", "...|.|.|..", "__________"),  # 7 celosías
        _ascii("##########", "..........", "____...___"),  # 8 pozo → 17
        _ascii("##########", "^^^.......", "____X_X___"),  # 9 cuchillas
        _ascii("##########", ".........#", "_______Dd#"),  # 10 la salida
        # --- Cripta -------------------------------------------------------
        _ascii("##########", "#.........", "#___k_h___"),  # 11 huesos y poción
        _ascii(  # 12 guardia entre cuchillas
            "##########",
            "..........",
            "____X_X___",
            guards=(G_S(col=8, row=2, direction=-1, skill=5),),
        ),
        _ascii("##########", "....^^....", "__________"),  # 13
        _ascii("##########", "..........", "___X__X___"),  # 14
        _ascii("##########", "...|.|.|..", "__________"),  # 15
        _ascii("##########", "..........", "____P_____"),  # 16 placa de la salida
        _ascii(
            "###.___.##", "..^^......", "__________"
        ),  # 17 bajo el pozo: despierta el esqueleto; se sube
        _ascii(  # 18 guardia
            "##########",
            "..........",
            "___T______",
            guards=(G_S(col=5, row=2, direction=-1, skill=5),),
        ),
        _ascii(  # 19 poción grande tras reja; su portero
            "##########",
            "....^^....",
            "_PXG_H____",
            guards=(G_S(col=8, row=2, direction=-1, skill=5),),
        ),
        _ascii(  # 20 poción del tiempo
            "##########",
            ".........#",
            "_____y___#",
            guards=(G_S(col=3, row=2, direction=0, skill=5),),
        ),
    ]
    doorlinks = (
        DoorLink(plate_room=3, plate_col=8, plate_row=2, gate_room=5, gate_col=6, gate_row=2),
        DoorLink(plate_room=4, plate_col=4, plate_row=2, gate_room=5, gate_col=6, gate_row=2),
        DoorLink(plate_room=16, plate_col=4, plate_row=2, gate_room=10, gate_col=7, gate_row=2),
        DoorLink(plate_room=19, plate_col=1, plate_row=2, gate_room=19, gate_col=3, gate_row=2),
    )
    events = (Event(EventKind.SKELETON_WAKE, room=17, col=7),)
    return _build_level(
        number=9,
        name="The Tomb",
        specs=specs,
        grid=grid,
        start_room=1,
        start_col=1,
        start_row=2,
        events=events,
        doorlinks=doorlinks,
    )


# ===========================================================================
# Nivel 10 — The Tower  (20 salas)  vertical
# ===========================================================================
# Pozo vertical de 10 salas (1 arriba → 10 abajo con el exit) y galería
# lateral 11-20 colgada del nivel de la sala 4.


def _l10() -> Level:
    """La torre: un pozo de diez salas que se baja de hueco en hueco (cada
    agujero cae sobre una cornisa de la sala de abajo). En la 4 sale el
    ala este (11-20): su primera placa abre la reja de la 5 (corre), y
    al fondo de celosías, cuchillas y columnas, la placa de la salida
    (15) y la poción grande (20). La salida está en el fondo del pozo."""
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
    specs = [
        # --- El pozo ------------------------------------------------------
        _ascii("##########", "#.........", "#___..____"),  # 1 lo alto
        _ascii(  # 2
            "###.__.###",
            "..........",
            "_______..#",
            guards=(G_S(col=2, row=2, direction=0, skill=5),),
        ),
        _ascii("######.__.", "..........", "f_S_..____"),  # 3 pluma: baja el pozo de un salto
        _ascii("###.__.###", "..........", "________.."),  # 4 cruce con el ala
        _ascii("#######.__", "..........", "_..___G___"),  # 5 la reja
        _ascii(  # 6 guardia en la celosía
            "#__.######",
            "...|..|...",
            "____..____",
            guards=(G_S(col=7, row=2, direction=-1, skill=5),),
        ),
        _ascii("###.__.###", "....b.....", "____B___.."),  # 7
        _ascii("#######.__", "..........", "_..___S___"),  # 8 pinchos
        _ascii(  # 9 guardia; losa → 10
            "#__.######",
            "..........",
            "______L___",
            guards=(G_S(col=3, row=2, direction=0, skill=5),),
        ),
        _ascii("#####._.##", "..........", "_Dd_X_____"),  # 10 el fondo: la salida
        # --- Ala este -----------------------------------------------------
        _ascii("##########", "..........", "_P_____L__"),  # 11 placa de la reja
        _ascii("##########", "...^^.....", "____X_____"),  # 12
        _ascii(  # 13 guardia entre cuchillas
            "##########",
            "..........",
            "___X___X__",
            guards=(G_S(col=5, row=2, direction=-1, skill=5),),
        ),
        _ascii("##########", "...b..b.b.", "___B__B_B_"),  # 14 columnas
        _ascii(  # 15 placa de la salida, vigilada
            "##########",
            "..........",
            "_____P____",
            guards=(G_S(col=7, row=2, direction=-1, skill=5),),
        ),
        _ascii("##########", "..^^......", "___S_S____"),  # 16 pinchos
        _ascii("##########", "...|.|.|..", "____y_____"),  # 17 celosías y poción del tiempo
        _ascii("##########", "..........", "_____T____"),  # 18
        _ascii("##########", "..........", "____LL____"),  # 19 losas al vacío
        _ascii(  # 20 la poción grande tras reja
            "##########",
            ".........#",
            "_PG_H____#",
            guards=(G_S(col=6, row=2, direction=-1, skill=5),),
        ),
    ]
    doorlinks = (
        DoorLink(plate_room=11, plate_col=1, plate_row=2, gate_room=5, gate_col=6, gate_row=2),
        DoorLink(plate_room=20, plate_col=1, plate_row=2, gate_room=20, gate_col=2, gate_row=2),
        DoorLink(plate_room=15, plate_col=5, plate_row=2, gate_room=10, gate_col=1, gate_row=2),
    )
    return _build_level(
        number=10,
        name="The Tower",
        specs=specs,
        grid=grid,
        start_room=1,
        start_col=1,
        start_row=2,
        doorlinks=doorlinks,
    )


# ===========================================================================
# Nivel 11 — The Tower II  (20 salas)
# ===========================================================================
# Bloque superior 2x2 (1-2 / 3-4), galería larga 7-20 como tercer piso
# y cámara final 5-6 colgada bajo la galería: los loose floors de la
# sala 13 son la única entrada a la sala de la gate (5) y el exit (6).


def _l11() -> Level:
    """Lo alto de la torre. Se baja dos pisos (pozo de la 1, losa de la 3
    o agujero de la 4) hasta el gran corredor (7-20): pinchos, cuchillas,
    celosías, guardias y, al fondo, la placa de la salida. De vuelta, las
    dos losas de la 13: una cae sobre la placa de la antesala (5) y deja
    su reja abierta para siempre; la otra te deja caer en su cornisa.
    La salida está en la 6."""
    G_S = GuardSpawn  # noqa: N806
    grid = """
     1  2  .  .  .  .  .  .  .  .  .  .  .  .
     3  4  .  .  .  .  .  .  .  .  .  .  .  .
     7  8  9 10 11 12 13 14 15 16 17 18 19 20
     .  .  .  .  .  .  5  6  .  .  .  .  .  .
    """
    specs = [
        _ascii("##########", "....^^^...", "__T_..____"),  # 1 inicio: pozo → 3
        _ascii(  # 2 arena
            "##########",
            "..b.......",
            "__B_P_GH_#",
            guards=(G_S(col=3, row=2, direction=0, skill=5),),
        ),
        _ascii("###.__.###", "..........", "___X_LX___"),  # 3 cuchillas y losa → 7
        _ascii("##########", "....^^....", "____S__.__"),  # 4 pinchos; agujero → 8
        _ascii("###_.#####", "..........", "#_h_PG____"),  # 5 antesala: placa y reja
        _ascii("##########", ".........#", "_______Dd#"),  # 6 la salida
        _ascii("####._.###", "...|..|...", "#_________"),  # 7
        _ascii(  # 8 guardia entre pinchos
            "######._.#",
            "..........",
            "____S_S___",
            guards=(G_S(col=8, row=2, direction=-1, skill=5),),
        ),
        _ascii("##########", "....b.....", "____B_____"),  # 9
        _ascii("##########", "..........", "[_________"),  # 10 balcón
        _ascii("##########", "..........", "_____h____"),  # 11 poción
        _ascii("##########", "....^^^...", "__________"),  # 12
        _ascii("##########", "..........", "___LL_____"),  # 13 las dos losas → 5
        _ascii("##########", "...b...b..", "___B___B__"),  # 14
        _ascii(  # 15 guardia
            "##########",
            "..........",
            "_____T____",
            guards=(G_S(col=4, row=2, direction=0, skill=3),),
        ),
        _ascii("##########", "..........", "____X_X___"),  # 16
        _ascii(  # 17 guardia tras los pinchos
            "##########",
            "..........",
            "___S______",
            guards=(G_S(col=7, row=2, direction=-1, skill=5),),
        ),
        _ascii("##########", "....b.b...", "____B_B___"),  # 18
        _ascii("##########", "...|.|.|..", "__________"),  # 19
        _ascii(  # 20 placa de la salida
            "##########",
            ".........#",
            "__H_P____#",
            guards=(G_S(col=6, row=2, direction=-1, skill=4),),
        ),
    ]
    doorlinks = (
        DoorLink(plate_room=5, plate_col=4, plate_row=2, gate_room=5, gate_col=5, gate_row=2),
        DoorLink(plate_room=20, plate_col=4, plate_row=2, gate_room=6, gate_col=7, gate_row=2),
        DoorLink(plate_room=2, plate_col=4, plate_row=2, gate_room=2, gate_col=6, gate_row=2),
    )
    return _build_level(
        number=11,
        name="The Tower II",
        specs=specs,
        grid=grid,
        start_room=1,
        start_col=1,
        start_row=2,
        doorlinks=doorlinks,
    )


# ===========================================================================
# Nivel 12 — The Vizier  (24 salas)
# ===========================================================================
def _l12() -> Level:
    """Dominios del visir. Guardias de élite, cuchillas, losas sobre el
    vacío, el espejo donde el kid se funde con su sombra y la sala donde
    aparece el visir. La salida (8) está cerrada: su pozo baja a la
    galería sur. La placa de la 13 abre la reja de la 14, pero la placa
    de cierre de la 21 la cierra a tu paso; junto a ella está la placa de
    la salida. De vuelta, la placa de la 16 reabre la reja: corre. Se
    sube por la escalera de la 9."""
    G_S = GuardSpawn  # noqa: N806
    grid = """
     1  2  3  4  5  6  7  8  .  .  .  .  .  .  .  .  .  .  .  .  .  .  .
     .  .  .  .  .  .  .  9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24
    """
    specs = [
        _ascii(  # 1
            "##########",
            "....^^....",
            "_______S__",
            guards=(G_S(col=5, row=2, direction=-1, skill=6),),
        ),
        _ascii("##########", "^^^.......", "___X__X___"),  # 2
        _ascii(  # 3 la poción grande sobre la columna
            "##########",
            "..H....b..",
            "__B____B__",
            guards=(G_S(col=5, row=2, direction=-1, skill=7),),
        ),
        _ascii("##########", "...^^^^...", "____LL.___"),  # 4 losas y hueco al vacío
        _ascii(
            "_t__tt__t_", "..........", "_____M_vh_"
        ),  # 5 el espejo: fusión; veneno junto a la cura
        _ascii("##########", "......^^^^", "_____L____"),  # 6 losa al vacío
        _ascii("##########", ".b......S.", "_BS_____B_"),  # 7 aparece el visir
        _ascii("##########", "..........", "____..._Dd"),  # 8 pozo → 9 y la salida
        # --- Galería sur --------------------------------------------------
        _ascii("###.___.##", "..^^......", "#_________"),  # 9 bajo el pozo; se sube
        _ascii("##########", "....b.b...", "____B_B___"),  # 10
        _ascii(  # 11 guardia
            "##########",
            "...^^^....",
            "__________",
            guards=(G_S(col=7, row=2, direction=-1, skill=7),),
        ),
        _ascii("##########", "..........", "[_________"),  # 12 balcón
        _ascii("##########", "..........", "_____P____"),  # 13 placa de la reja
        _ascii("##########", "..........", "____G_____"),  # 14 la reja
        _ascii(  # 15 guardia
            "##########",
            "...b..b...",
            "___B__B___",
            guards=(G_S(col=5, row=2, direction=-1, skill=8),),
        ),
        _ascii("##########", "..........", "__P_______"),  # 16 placa de vuelta: corre
        _ascii("##########", "..........", "_____k____"),  # 17 huesos
        _ascii("##########", "...|.|.|..", "__________"),  # 18
        _ascii(  # 19 guardia entre cuchillas
            "##########",
            "..........",
            "____X_X___",
            guards=(G_S(col=7, row=2, direction=-1, skill=8),),
        ),
        _ascii(  # 20 el campeón del visir
            "##########",
            "..........",
            "__________",
            guards=(G_S(col=5, row=2, direction=0, skill=8),),
        ),
        _ascii("##########", "....^^....", "___c___P__"),  # 21 cierre y placa de la salida
        _ascii("##########", "....b.....", "____B__T__"),  # 22
        _ascii(
            "##########", "..........", "_____L____"
        ),  # 23 losa al vacío; despierta el esqueleto
        _ascii(  # 24 la poción grande tras reja
            "##########",
            ".........#",
            "_PG_H____#",
            guards=(G_S(col=6, row=2, direction=-1, skill=8),),
        ),
    ]
    doorlinks = (
        DoorLink(plate_room=13, plate_col=5, plate_row=2, gate_room=14, gate_col=4, gate_row=2),
        DoorLink(plate_room=16, plate_col=2, plate_row=2, gate_room=14, gate_col=4, gate_row=2),
        DoorLink(plate_room=21, plate_col=3, plate_row=2, gate_room=14, gate_col=4, gate_row=2),
        DoorLink(plate_room=21, plate_col=7, plate_row=2, gate_room=8, gate_col=8, gate_row=2),
        DoorLink(plate_room=24, plate_col=1, plate_row=2, gate_room=24, gate_col=2, gate_row=2),
    )
    events = (
        Event(EventKind.SHADOW_FUSION, room=5, col=5),
        Event(EventKind.VIZIER_INIT, room=7),
        Event(EventKind.SKELETON_WAKE, room=23, col=7),
    )
    return _build_level(
        number=12,
        name="The Vizier",
        specs=specs,
        grid=grid,
        start_room=1,
        start_col=1,
        start_row=2,
        events=events,
        doorlinks=doorlinks,
    )


# ===========================================================================
# Nivel 13 — Final Run  (18 salas)  carrera contra reloj
# ===========================================================================
def _l13() -> Level:
    """La huida final: dieciocho salas en hilera contra el reloj, con
    tres guardias de élite en el camino. Cuchillas en serie, camas de pinchos, fosos, losas sobre el
    vacío, la reja de la 7 (su placa, en la 6, entre cuchillas) y la
    placa de la salida en la 15, dos salas de cuchillas antes de la
    puerta."""
    G_S = GuardSpawn  # noqa: N806
    grid = """
     1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18
    """
    specs = [
        _ascii("##########", "#.........", "#__X_X_X__"),  # 1 tres cuchillas
        _ascii("##########", "..........", "__S_SLS_S_"),  # 2 pinchos y losa
        _ascii("##########", "..........", "__S_..._S_"),  # 3 foso entre pinchos
        _ascii("##########", "...|..|...", "__________"),  # 4 celosías
        _ascii("##########", "...^^^^...", "____..____"),  # 5 foso
        _ascii("##########", "..........", "__P__X____"),  # 6 placa de la reja
        _ascii("##########", "^^........", "__S__G__S_"),  # 7 la reja entre pinchos
        _ascii(  # 8 guardia
            "##########",
            "....^^....",
            "__________",
            guards=(G_S(col=6, row=2, direction=-1, skill=6),),
        ),
        _ascii("##########", "..^^^^^^..", "_____L____"),  # 9 losa al vacío
        _ascii("##########", "..........", "___X___X__"),  # 10
        _ascii("##########", "..........", "___h_y___]"),  # 11 balcón, vida y tiempo
        _ascii("##########", "...|.|.|..", "__________"),  # 12
        _ascii("##########", "...b...b..", "___B_T_B__"),  # 13
        _ascii("##########", "..........", "__S_S_S___"),  # 14 pinchos
        _ascii(  # 15 placa de la salida y su portero
            "##########",
            "..........",
            "____P_____",
            guards=(G_S(col=7, row=2, direction=-1, skill=6),),
        ),
        _ascii("##########", "..........", "____X_X___"),  # 16
        _ascii("##########", "...^^^^...", "____LL____"),  # 17 losas al vacío
        _ascii(  # 18 la puerta y el último guardia
            "##########",
            ".........#",
            "__h____Dd#",
            guards=(G_S(col=4, row=2, direction=-1, skill=6),),
        ),
    ]
    doorlinks = (
        DoorLink(plate_room=6, plate_col=2, plate_row=2, gate_room=7, gate_col=5, gate_row=2),
        DoorLink(plate_room=15, plate_col=4, plate_row=2, gate_room=18, gate_col=7, gate_row=2),
    )
    return _build_level(
        number=13,
        name="Final Run",
        specs=specs,
        grid=grid,
        start_room=1,
        start_col=1,
        start_row=2,
        doorlinks=doorlinks,
    )


# ===========================================================================
# Nivel 14 — Ending  (3 salas — acceso + escaleras + cámara princesa)
# ===========================================================================
def _l14() -> Level:
    """Los aposentos de la princesa: pórtico con antorchas, galería de
    celosías y la cámara donde ella espera."""
    grid = """
     1  2  3
    """
    specs = [
        _ascii("##______##", "...^^^^...", "T________T"),  # 1 pórtico
        _ascii("#____t___#", "...|.|....", "__T____T__"),  # 2 galería
        _ascii("##___t__##", ".b......b.", "_B_T___TB_"),  # 3 la princesa
    ]
    events = (Event(EventKind.PRINCESS_REUNION, room=3),)
    return _build_level(
        number=14,
        name="Ending",
        specs=specs,
        grid=grid,
        start_room=1,
        start_col=1,
        start_row=2,
        events=events,
    )


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
