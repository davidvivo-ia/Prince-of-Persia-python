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
    """Mazmorra en tres pisos. Arriba: el despertar, losas sueltas, una
    pasarela alta con una poción y el pozo que baja. En medio: la espada
    en una cornisa, la reja que abre su placa y el primer duelo. Abajo:
    las placas que mantienen abierta la reja de la sala 11, el foso que se
    salta con carrerilla, el segundo guardia y la salida."""
    G_S = GuardSpawn  # noqa: N806 — alias local de tipo
    grid = """
     1  2  3  4  5  6
     7  8  9 10 11 12
    13 14 15 16 17 18
    """
    specs = [
        # --- Piso superior ------------------------------------------------
        _ascii(  # 1 despertar: muro a la espalda, losas sueltas, cornisa
            "#####_____",
            "#......___",
            "#___LL_T__",
        ),
        _ascii(  # 2 pasarela alta con hueco y poción al fondo
            "_____#####",
            "____..._h.",
            "______T___",
        ),
        _ascii(  # 3 el pozo que baja a la sala 9
            "##________",
            ".......___",
            "____..____",
        ),
        _ascii(  # 4 dintel con suelo sobre el pasillo
            "___####___",
            "....^^....",
            "_______T__",
        ),
        _ascii(  # 5 galería con repisa a la izquierda
            "______####",
            "^^^.......",
            "__________",
        ),
        _ascii(  # 6 fondo de saco: losa suelta y poción en lo alto
            "____######",
            "......_h.#",
            "_____L___#",
        ),
        # --- Piso intermedio ----------------------------------------------
        _ascii(  # 7 bajo las losas de la sala 1
            "####..####",
            "__......__",
            "______T___",
        ),
        _ascii(  # 8 la espada, en una cornisa; placa de la reja de 9
            "___#######",
            "..s_......",
            "_____T_P__",
        ),
        _ascii(  # 9 la reja (cae aquí el pozo de la sala 3)
            "____..____",
            "..........",
            "______G___",
        ),
        _ascii(  # 10 sala de guardia: el primer duelo
            "##########",
            "#........#",
            "__T_______",
            guards=(G_S(col=7, row=2, direction=-1, skill=0),),
        ),
        _ascii(  # 11 columna, placa propia y reja
            "____##____",
            "....b.....",
            "__P_B__G__",
        ),
        _ascii(  # 12 placa que reabre la 9 y losa sobre la salida
            "#####.####",
            ".........#",
            "___P_L___#",
        ),
        # --- Piso inferior ------------------------------------------------
        _ascii(  # 13 placa de la reja de 11
            "##########",
            "#.._......",
            "#__P______",
        ),
        _ascii(  # 14 losa suelta colgada como repisa
            "__________",
            ".....L....",
            "___T______",
        ),
        _ascii(  # 15 foso sin fondo: salto con carrerilla
            "###____###",
            "..........",
            "____...___",
        ),
        _ascii(  # 16 segundo guardia
            "##########",
            "..........",
            "______T___",
            guards=(G_S(col=4, row=2, direction=-1, skill=0),),
        ),
        _ascii(  # 17 placa (segunda apertura de la reja de 11)
            "_____#####",
            "..........",
            "__P_______",
        ),
        _ascii(  # 18 la salida
            "#####.####",
            "..........",
            "_______Dd#",
        ),
    ]
    doorlinks = (
        DoorLink(plate_room=8, plate_col=7, plate_row=2, gate_room=9, gate_col=6, gate_row=2),
        DoorLink(plate_room=11, plate_col=2, plate_row=2, gate_room=11, gate_col=7, gate_row=2),
        DoorLink(plate_room=12, plate_col=3, plate_row=2, gate_room=9, gate_col=6, gate_row=2),
        DoorLink(plate_room=13, plate_col=3, plate_row=2, gate_room=11, gate_col=7, gate_row=2),
        DoorLink(plate_room=17, plate_col=2, plate_row=2, gate_room=11, gate_col=7, gate_row=2),
    )
    return _build_level(
        number=1,
        name="The Dungeon",
        specs=specs,
        grid=grid,
        start_room=1,
        start_col=2,
        start_row=2,
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
    """Cuerpo de guardia: la fila norte son barracones de techo macizo con
    guardias cada vez más diestros y las primeras cuchillas; se baja por
    la losa suelta del inicio. La fila sur lleva a la salida, vigilada, y
    al este de ella dos pociones de premio."""
    G_S = GuardSpawn  # noqa: N806
    grid = """
     1  2  3  4  5  6  7  8  9 10
    11 12 13 14 15 16 17 18 19 20
    """
    specs = [
        # --- Fila norte ---------------------------------------------------
        _ascii("####______", "#.........", "_____L____"),  # 1 inicio
        _ascii(  # 2 barracón con antorchas
            "##########",
            "..........",
            "__T____T__",
            guards=(G_S(col=5, row=2, direction=-1, skill=1),),
        ),
        _ascii("_____#####", "..........", "____X_____"),  # 3 primeras cuchillas
        _ascii("___##_____", "....^^....", "_______.__"),  # 4 dintel y pozo
        _ascii("______####", "^^^^......", "__________"),  # 5 repisa larga
        _ascii("#####_____", "..........", "_____G____"),  # 6 la reja
        _ascii("____######", "......___.", "__P_______"),  # 7 su placa
        _ascii(  # 8 arena entre columnas
            "##########",
            "..b....b..",
            "__B____B__",
            guards=(G_S(col=5, row=2, direction=-1, skill=2),),
        ),
        _ascii("_____#####", "....b.....", "____B_____"),  # 9
        _ascii("######____", "........_#", "______T__#"),  # 10 fondo
        # --- Fila sur -----------------------------------------------------
        _ascii("#####.####", "#.........", "_____T____"),  # 11 cae aquí la losa
        _ascii("####______", "..........", "_____X____"),  # 12
        _ascii("###____###", "..........", "____LL____"),  # 13 losas trampa
        # La fila alta de estas salas es una pasarela continua (14-19)
        # que se alcanza cayendo por el pozo de la sala 4.
        _ascii("_______.__", "..........", "___P___G__"),  # 14 placa y reja
        _ascii(  # 15 guardia de élite entre columnas
            "__________",
            "..b....b..",
            "__B__T_B__",
            guards=(G_S(col=3, row=2, direction=0, skill=3),),
        ),
        _ascii("_____t____", "....b.b...", "____B_B___"),  # 16 columnata
        _ascii("__________", "..b....b..", "__B_X__B__"),  # 17 cuchillas
        _ascii(  # 18 la salida, vigilada
            "__________",
            "..b.......",
            "__B____Dd_",
            guards=(G_S(col=4, row=2, direction=0, skill=3),),
        ),
        _ascii("__________", "....b.....", "[___Bh____"),  # 19 balcón y poción
        _ascii("____######", ".........#", "____H____#"),  # 20 poción grande
    ]
    doorlinks = (
        DoorLink(plate_room=7, plate_col=2, plate_row=2, gate_room=6, gate_col=5, gate_row=2),
        DoorLink(plate_room=14, plate_col=3, plate_row=2, gate_room=14, gate_col=7, gate_row=2),
    )
    return _build_level(
        number=2,
        name="The Guards",
        specs=specs,
        grid=grid,
        start_room=1,
        start_col=2,
        start_row=2,
        doorlinks=doorlinks,
    )


# ===========================================================================
# Nivel 3 — The Skeleton  (18 salas)
# ===========================================================================
# Fila norte 1-9; sub-piso 10-17 (el pit de la sala 3 cae en los loose de
# la 10); estancias secretas 17-18 bajo la sala 9 del plate.


def _l3() -> Level:
    """Osario: el esqueleto despierta al pasar junto a él. La fila norte
    alterna cuchillas, celosías y dos arenas; se baja por el pozo de la
    sala 3 o por la losa de la 2. Bajo la sala 17 una losa suelta da a una
    cripta secreta con la poción grande; para salir hay que trepar por
    las cornisas de la columna."""
    G_S = GuardSpawn  # noqa: N806
    grid = """
     1  2  3  4  5  6  7  8  9
     . 11 10 12 13 14 15 16 17
     .  .  .  .  .  .  .  . 18
    """
    specs = [
        # --- Fila norte ---------------------------------------------------
        _ascii("##########", "#.........", "____k_____"),  # 1 el esqueleto
        _ascii("___#######", "........_.", "_____L____"),  # 2 losa → 11
        _ascii("##______##", "....^^....", "____..____"),  # 3 pozo → 10
        _ascii("_______###", "....|.....", "__________"),  # 4 celosía
        _ascii("####______", "......__..", "___X______"),  # 5 cuchillas
        _ascii(  # 6 arena
            "##########",
            "..b....b..",
            "__B____B__",
            guards=(G_S(col=5, row=2, direction=-1, skill=2),),
        ),
        _ascii("____######", "...b...b..", "___B___B__"),  # 7 columnata
        _ascii("______####", ".._.......", "_____G____"),  # 8 la reja
        _ascii("______####", ".........#", "_____P___#"),  # 9 su placa
        # --- Fila sur -----------------------------------------------------
        _ascii("####..####", "..........", "___L_L____"),  # 10 bajo el pozo
        _ascii("#####.____", "#.........", "______T___"),  # 11 bajo la losa
        _ascii("____^^____", ".._...._..", "__________"),  # 12
        _ascii("_####_####", "..........", "___X__X___"),  # 13 doble cuchilla
        _ascii(  # 14 arena
            "##########",
            "..b....b..",
            "__B____B__",
            guards=(G_S(col=5, row=2, direction=0, skill=2),),
        ),
        _ascii("_____#####", "...___....", "____P_____"),  # 15 placa
        _ascii(  # 16 la salida
            "##########",
            "..........",
            "_______Dd_",
            guards=(G_S(col=3, row=2, direction=0, skill=2),),
        ),
        _ascii("####______", "..........", "_____h__L_"),  # 17 poción; losa → cripta
        # --- Cripta secreta -----------------------------------------------
        _ascii("####._____", "...._.....", "__H_B_B___"),  # 18
    ]
    doorlinks = (
        DoorLink(plate_room=9, plate_col=5, plate_row=2, gate_room=8, gate_col=5, gate_row=2),
        DoorLink(plate_room=15, plate_col=4, plate_row=2, gate_room=8, gate_col=5, gate_row=2),
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
    """Galería del espejo: palacio de mármol a la luz de la luna. Pinchos y
    celosías arriba, el espejo del que sale la sombra, la reja que abren
    dos placas y la salida vigilada. El pozo de la sala 3 baja a la
    galería sur; una losa en la columnata (17) lleva a dos salas
    escondidas al fondo."""
    G_S = GuardSpawn  # noqa: N806
    grid = """
     1  2  3  4  5  6  7  8  9 10
     .  . 11 12 13 14 15 16 17 18
     .  .  .  .  .  .  .  . 19 20
    """
    specs = [
        # --- Galería norte ------------------------------------------------
        _ascii("##########", "#.....__..", "_____L____"),  # 1 losa trampa
        _ascii("_____#####", "..........", "___S_S_S__"),  # 2 pinchos
        _ascii("###____###", ".__.......", "____...___"),  # 3 pozo → 11
        _ascii("____######", "...|..|...", "__________"),  # 4 celosías
        _ascii("_t__tt__t_", "..........", "_____M__h_"),  # 5 el espejo
        _ascii("######____", "....__....", "___P___X__"),  # 6 placa y cuchillas
        _ascii("____######", "..........", "____G_____"),  # 7 la reja
        _ascii("##########", "....b..b..", "____B__B__"),  # 8 columnata
        _ascii("_____#####", "......___.", "___T_L____"),  # 9 losa → 17
        _ascii(  # 10 la salida
            "##########",
            ".........#",
            "_______Dd_",
            guards=(G_S(col=3, row=2, direction=0, skill=3),),
        ),
        # --- Galería sur --------------------------------------------------
        _ascii("####...###", "#.........", "__v_______"),  # 11 bajo el pozo: veneno
        _ascii("__________", "_........_", "____X_X___"),  # 12 cuchillas dobles
        _ascii("______####", "..........", "[_________"),  # 13 balcón
        _ascii(  # 14 guardia
            "##########",
            "..........",
            "__________",
            guards=(G_S(col=5, row=2, direction=-1, skill=3),),
        ),
        _ascii("___^^^____", "......___.", "__________"),  # 15
        _ascii("#####_____", ".._.......", "_____P____"),  # 16 segunda placa
        _ascii("_____.____", "...b..b...", "___B__BTL_"),  # 17 losa → 19
        _ascii("____######", ".........#", "_____f___#"),  # 18 poción pluma
        # --- Escondite ----------------------------------------------------
        _ascii("######.___", "......_...", "__________"),  # 19
        _ascii("_____#####", ".........#", "_____T___#"),  # 20
    ]
    doorlinks = (
        DoorLink(plate_room=6, plate_col=3, plate_row=2, gate_room=7, gate_col=4, gate_row=2),
        DoorLink(plate_room=16, plate_col=5, plate_row=2, gate_room=7, gate_col=4, gate_row=2),
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
    """Salón del ladrón: palacio cálido de velas y tapices. La sombra roba
    la poción de la sala 4. Arriba, losas sueltas que bajan al bucle sur;
    la placa de la sala 6 abre la reja de la 7; la salida, vigilada, en la
    10. Al sur, un frasco vacío y, al final del ala este, la poción del
    tiempo guardada por un espadachín."""
    G_S = GuardSpawn  # noqa: N806
    grid = """
     1  2  3  4  5  6  7  8  9 10  .  .  .
    11 12 13  .  .  . 14 15 16 17 18 19 20
    """
    specs = [
        # --- Ala norte ----------------------------------------------------
        _ascii("##########", "#......___", "______T___"),  # 1
        _ascii("____######", "..........", "___LLL____"),  # 2 losas → 12
        _ascii("##________", "^^^^......", "_______S__"),  # 3
        _ascii("_t__t__t__", "...^.^....", "____h_____"),  # 4 la poción robada
        _ascii("######____", "......__..", "_____L____"),  # 5 losa al vacío
        _ascii("____######", "..__......", "________P_"),  # 6 placa
        _ascii("##____####", "..........", "___G______"),  # 7 reja
        _ascii(  # 8 arena
            "##########",
            "..b....b..",
            "__B____B__",
            guards=(G_S(col=5, row=2, direction=-1, skill=3),),
        ),
        _ascii("____##____", "....^.^...", "_____T____"),  # 9
        _ascii(  # 10 la salida
            "##########",
            ".........#",
            "_______Dd_",
            guards=(G_S(col=3, row=2, direction=0, skill=3),),
        ),
        # --- Ala sur ------------------------------------------------------
        _ascii("#####_____", "#.........", "____k_____"),  # 11 huesos
        _ascii("___...____", "._........", "_____L____"),  # 12 bajo las losas
        _ascii("_____#####", "..........", "_________]"),  # 13 balcón
        _ascii("#####_____", "#.........", "_____e____"),  # 14 frasco vacío
        _ascii("__________", "...|.|.|..", "__________"),  # 15 celosías
        _ascii("####______", "..........", "_____XS___"),  # 16
        _ascii("____^^____", "........_.", "__________"),  # 17
        _ascii("##########", "..........", "___T___T__"),  # 18
        _ascii("____######", "....b.b...", "____B_B___"),  # 19
        _ascii(  # 20 la poción del tiempo
            "##########",
            ".........#",
            "____y____#",
            guards=(G_S(col=6, row=2, direction=-1, skill=3),),
        ),
    ]
    doorlinks = (
        DoorLink(plate_room=6, plate_col=8, plate_row=2, gate_room=7, gate_col=3, gate_row=2),
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
    """La escalinata: palacio nocturno. Se empieza ante un foso que hay que
    saltar con carrerilla (y la sombra salta contigo). Tres placas abren
    la reja de la sala 2; la 8 tiene la suya propia. La losa de la sala 6
    baja a la terraza sur, con su poción y, al fondo, la poción grande."""
    G_S = GuardSpawn  # noqa: N806
    grid = """
     1  2  3  4  5  6  7  8  9 10  .  .  .
     .  .  .  .  . 11 12 13 14 15 16 17 18
    """
    specs = [
        # --- Terraza norte ------------------------------------------------
        _ascii("##########", "..........", "____...___"),  # 1 el foso
        _ascii("____######", ".._.......", "_P_G______"),  # 2 placa y reja
        _ascii("######____", "..........", "____X__P__"),  # 3
        _ascii(  # 4 guardia
            "##########",
            "..........",
            "_______S__",
            guards=(G_S(col=5, row=2, direction=-1, skill=4),),
        ),
        _ascii("____######", "...b...b..", "___B___B__"),  # 5
        _ascii("##____####", "....^^^...", "_____L____"),  # 6 losa → 11
        _ascii("__________", "...|.|.|..", "__________"),  # 7 celosías
        _ascii("######____", "......._..", "__P__G____"),  # 8 placa y reja
        _ascii("##________", "^^^.......", "___X______"),  # 9
        _ascii(  # 10 la salida
            "##########",
            ".........#",
            "_______Dd_",
            guards=(G_S(col=3, row=2, direction=0, skill=4),),
        ),
        # --- Terraza sur --------------------------------------------------
        _ascii("_____.####", "#.........", "_____h____"),  # 11
        _ascii("__________", "_........_", "____..____"),  # 12 foso
        _ascii("##____####", "..........", "[_________"),  # 13 balcón
        _ascii("_____#####", "..........", "___S_S_S__"),  # 14 pinchos
        _ascii("__________", "..__......", "_____P____"),  # 15 placa
        _ascii("____^^^___", "..........", "__________"),  # 16
        _ascii("##########", "..........", "_____T____"),  # 17
        _ascii("####______", "...b..b..#", "___BH_B__#"),  # 18 poción grande
    ]
    doorlinks = (
        DoorLink(plate_room=2, plate_col=1, plate_row=2, gate_room=2, gate_col=3, gate_row=2),
        DoorLink(plate_room=3, plate_col=7, plate_row=2, gate_room=2, gate_col=3, gate_row=2),
        DoorLink(plate_room=8, plate_col=2, plate_row=2, gate_room=8, gate_col=5, gate_row=2),
        DoorLink(plate_room=15, plate_col=5, plate_row=2, gate_room=2, gate_col=3, gate_row=2),
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
    """Entrañas de la montaña: roca viva con raíces y arena que cae. Tres
    pisos: arriba pinchos, celosías y la placa que abre la reja de la sala
    7; la losa de la sala 1 baja a una cornisa con antorcha sobre un pozo
    que lleva al piso inferior; la salida está al final de este."""
    G_S = GuardSpawn  # noqa: N806
    grid = """
     1  2  3  4  5  6  7  .
     8  9 10 11 12 13 14  .
    15 16 17 18 19 20 21 22
    """
    specs = [
        # --- Piso alto ----------------------------------------------------
        _ascii("##########", "#......___", "_____L____"),  # 1 losa → 8
        _ascii("____######", "..........", "___S_S_S__"),  # 2 pinchos
        _ascii("######____", "...|..|...", "__________"),  # 3 celosías
        _ascii("____######", "...^^.....", "_____P____"),  # 4 placa
        _ascii("##________", "....b..b..", "____B__B__"),  # 5
        _ascii(  # 6 arena
            "##########",
            "..b....b..",
            "__B____B__",
            guards=(G_S(col=5, row=2, direction=-1, skill=5),),
        ),
        _ascii("______####", ".........#", "_____G____"),  # 7 reja
        # --- Piso medio ---------------------------------------------------
        _ascii("#.........", ".....T....", "__......__"),  # 8 cornisa sobre el pozo
        _ascii("__________", ".._.......", "____LL____"),  # 9 losas → 16
        _ascii("####______", "......__..", "___X______"),  # 10 cuchillas
        _ascii("______####", "....b.....", "____B_____"),  # 11
        _ascii("##________", "..........", "_________]"),  # 12 asomada
        _ascii("____######", ".._.......", "_____h____"),  # 13 poción
        _ascii("######____", ".........#", "__X___X___"),  # 14 doble cuchilla
        # --- Piso bajo ----------------------------------------------------
        _ascii("__......__", "#.........", "_____S____"),  # 15 fondo del pozo
        _ascii("___^^^____", "..........", "__________"),  # 16 dintel (recoge la losa)
        _ascii("__________", "_.......__", "____LLL___"),  # 17 losas al vacío
        _ascii("#####_____", "...|...|..", "_____T____"),  # 18
        _ascii(  # 19 guardia
            "##########",
            "..........",
            "__________",
            guards=(G_S(col=4, row=2, direction=0, skill=5),),
        ),
        _ascii("____######", "...b..b...", "___B__B___"),  # 20
        _ascii("######____", ".._.......", "_____P____"),  # 21 segunda placa
        _ascii(  # 22 la salida
            "##########",
            ".........#",
            "_______Dd_",
            guards=(G_S(col=3, row=2, direction=0, skill=5),),
        ),
    ]
    doorlinks = (
        DoorLink(plate_room=4, plate_col=5, plate_row=2, gate_room=7, gate_col=5, gate_row=2),
        DoorLink(plate_room=21, plate_col=5, plate_row=2, gate_room=7, gate_col=5, gate_row=2),
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
    """Cavernas: estalactitas, cristales y goteras. Losas sueltas por todas
    partes que bajan a la galería inferior; la reja junto a la salida no
    tiene placa: la abre el ratón de la princesa cuando el kid llega."""
    G_S = GuardSpawn  # noqa: N806
    grid = """
     1  2  3  4  5  6  7  8  9 10
    11 12 13 14 15 16 17 18 19 20
    """
    specs = [
        # --- Galería alta -------------------------------------------------
        _ascii("##########", "#.........", "____.._L__"),  # 1 pozo y losa → 11
        _ascii("____######", "..........", "___L_X____"),  # 2
        _ascii("######____", "....|.|...", "__________"),  # 3 celosías
        _ascii("____######", ".._.......", "_____LLL__"),  # 4 losas → 14
        _ascii("##________", "...b..b...", "___B__B___"),  # 5
        _ascii(  # 6 guardia
            "##########",
            "..........",
            "_______S__",
            guards=(G_S(col=4, row=2, direction=0, skill=4),),
        ),
        _ascii("_____#####", "..___.....", "_____X____"),  # 7 cuchillas
        _ascii("######____", "........_.", "_____P____"),  # 8
        _ascii("____######", "..........", "[____T____"),  # 9 balcón
        _ascii("##########", ".........#", "__G____Dd_"),  # 10 reja del ratón y salida
        # --- Galería baja -------------------------------------------------
        _ascii("____.._.__", "..........", "____LL____"),  # 11
        _ascii("___^^^____", "..........", "__________"),  # 12 dintel (recoge la losa)
        _ascii("__________", "._......_.", "___X__X___"),  # 13
        _ascii("_____...__", "..........", "_____h____"),  # 14 poción
        _ascii("##########", "....b..b..", "____B__B__"),  # 15
        _ascii("____######", "..........", "_____k____"),  # 16 huesos
        _ascii("######____", "..__......", "_____L____"),  # 17
        _ascii("__________", "...|.|.|..", "__________"),  # 18 celosías
        _ascii(  # 19 guardia
            "##########",
            "..........",
            "__________",
            guards=(G_S(col=5, row=2, direction=-1, skill=4),),
        ),
        _ascii("____######", ".........#", "____H____#"),  # 20 poción grande
    ]
    events = (Event(EventKind.MOUSE_APPEAR, room=10),)
    return _build_level(
        number=8,
        name="The Caverns",
        specs=specs,
        grid=grid,
        start_room=1,
        start_col=1,
        start_row=2,
        events=events,
    )


# ===========================================================================
# Nivel 9 — The Tomb  (20 salas)
# ===========================================================================
# Fila norte 1-10 con el exit en 10; sótano 11-20 bajo ella. La potion
# MAX_HP (19) queda justo bajo el exit; 20 es el rincón final.


def _l9() -> Level:
    """La tumba: arenisca con jeroglíficos, nichos con calaveras y
    esqueletos tumbados. Tres placas abren la reja de la sala 5; dobles
    cuchillas y pinchos hasta la salida; al sur, la cripta con la poción
    grande."""
    G_S = GuardSpawn  # noqa: N806
    grid = """
     1  2  3  4  5  6  7  8  9 10  .
     . 11 12 13 14 15 16 17 18 19 20
    """
    specs = [
        # --- Nivel superior -----------------------------------------------
        _ascii("##########", "#.........", "____k_L___"),  # 1
        _ascii("____######", "..........", "___S_S_S__"),  # 2 pinchos
        _ascii("######____", "....b.....", "____B_____"),  # 3
        _ascii(  # 4 arena con poción
            "##########",
            "..b....b..",
            "__B____Bh_",
            guards=(G_S(col=5, row=2, direction=-1, skill=5),),
        ),
        _ascii("____######", "..........", "__P__G____"),  # 5 placa y reja
        _ascii("##________", "...|.|.|..", "__________"),  # 6 celosías
        _ascii("____##____", "......^...", "____Pk____"),  # 7 placa
        _ascii("______####", "._........", "_________]"),  # 8 balcón
        _ascii("##________", "^^^.......", "____X_X___"),  # 9 cuchillas
        _ascii(  # 10 la salida
            "##########",
            ".........#",
            "_______Dd_",
            guards=(G_S(col=3, row=2, direction=0, skill=5),),
        ),
        # --- Cripta -------------------------------------------------------
        _ascii("__________", "#.........", "_____L____"),  # 11
        _ascii("####______", "..........", "____X_X___"),  # 12
        _ascii("____^^____", "........_.", "__________"),  # 13
        _ascii("##########", "...b..b...", "___B__B___"),  # 14
        _ascii("_____#####", "..___.....", "_____T____"),  # 15
        _ascii("######____", "..........", "____P_____"),  # 16 tercera placa
        _ascii("____######", "......__..", "___k______"),  # 17
        _ascii("##________", "...|.|....", "__________"),  # 18
        _ascii("##########", "..........", "_____H____"),  # 19 poción grande
        _ascii("____######", ".........#", "_____T___#"),  # 20
    ]
    doorlinks = (
        DoorLink(plate_room=5, plate_col=2, plate_row=2, gate_room=5, gate_col=5, gate_row=2),
        DoorLink(plate_room=7, plate_col=4, plate_row=2, gate_room=5, gate_col=5, gate_row=2),
        DoorLink(plate_room=16, plate_col=4, plate_row=2, gate_room=5, gate_col=5, gate_row=2),
    )
    return _build_level(
        number=9,
        name="The Tomb",
        specs=specs,
        grid=grid,
        start_room=1,
        start_col=1,
        start_row=2,
        doorlinks=doorlinks,
    )


# ===========================================================================
# Nivel 10 — The Tower  (20 salas)  vertical
# ===========================================================================
# Pozo vertical de 10 salas (1 arriba → 10 abajo con el exit) y galería
# lateral 11-20 colgada del nivel de la sala 4.


def _l10() -> Level:
    """La torre: un pozo vertical de diez salas que se baja de hueco en
    hueco (sin caer más de la cuenta) y, desde la sala 4, un ala hacia el
    este con la placa que, junto con la del fondo del pozo, abre la reja
    de la sala 5."""
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
        _ascii("##########", "#.........", "____...___"),  # 1 lo alto
        _ascii(  # 2
            "..........",
            "__......._",
            "__..___.._",
            guards=(G_S(col=9, row=2, direction=-1, skill=5),),
        ),
        _ascii("##..###.._", "....___...", "___S_S__.."),  # 3 pinchos
        _ascii("..........", "_.........", "______..__"),  # 4 cruce con el ala este
        _ascii("######..##", "...__.....", "_____G__.."),  # 5 la reja
        _ascii("########..", "...|..|...", "____..____"),  # 6
        _ascii("####..####", "....b.....", "____B___.."),  # 7
        _ascii(  # 8
            "..........",
            "__........",
            "____....__",
            guards=(G_S(col=2, row=2, direction=0, skill=5),),
        ),
        _ascii("####....##", "_.........", "..___L____"),  # 9
        _ascii("..###.####", "..___.....", "_____P_Dd_"),  # 10 fondo: placa y salida
        # --- Ala este -----------------------------------------------------
        _ascii("##########", ".._.......", "_____P____"),  # 11 placa
        _ascii("____######", "..........", "_________]"),  # 12 asomada
        _ascii("######____", "......__..", "____LL____"),  # 13 losas al vacío
        _ascii("____^^____", ".._.......", "__________"),  # 14
        _ascii("##########", "...b..b.b.", "___B__B_B_"),  # 15
        _ascii("____######", ".......__.", "_____h____"),  # 16 poción
        _ascii("##________", "...|.|.|..", "__________"),  # 17 celosías
        _ascii("______####", "._........", "_____T____"),  # 18
        _ascii("####______", "..........", "___X___X__"),  # 19
        _ascii(  # 20 guardia del fondo
            "##########",
            ".........#",
            "__________",
            guards=(G_S(col=5, row=2, direction=-1, skill=5),),
        ),
    ]
    doorlinks = (
        DoorLink(plate_room=10, plate_col=5, plate_row=2, gate_room=5, gate_col=5, gate_row=2),
        DoorLink(plate_room=11, plate_col=5, plate_row=2, gate_room=5, gate_col=5, gate_row=2),
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
    """Lo alto de la torre, al alba. Se baja dos pisos hasta un largo
    corredor (7-20) de celosías, cuchillas y pinchos; sus losas sueltas
    (13) dejan caer a la antesala de la salida, cuya reja abren la placa
    de la propia sala y la del corredor."""
    G_S = GuardSpawn  # noqa: N806
    grid = """
     1  2  .  .  .  .  .  .  .  .  .  .  .  .
     3  4  .  .  .  .  .  .  .  .  .  .  .  .
     7  8  9 10 11 12 13 14 15 16 17 18 19 20
     .  .  .  .  .  .  5  6  .  .  .  .  .  .
    """
    specs = [
        _ascii("##########", "....^^^...", "__T_..____"),  # 1 inicio sobre el hueco
        _ascii(  # 2
            "##########",
            "..b....b..",
            "__B____B__",
            guards=(G_S(col=5, row=2, direction=-1, skill=5),),
        ),
        _ascii("####..####", "..........", "___X_LX___"),  # 3
        _ascii(  # 4
            "##########",
            "...^^^....",
            "_______.__",
            guards=(G_S(col=4, row=2, direction=-1, skill=5),),
        ),
        _ascii("###..#####", "#.........", "__P__G____"),  # 5 antesala: placa y reja
        _ascii("##########", ".........#", "_______Dd_"),  # 6 la salida
        _ascii("#####.####", "...|..|...", "__________"),  # 7
        _ascii("#######.##", ".__.......", "____S_S___"),  # 8 pinchos
        _ascii("____######", "....b.....", "____B_____"),  # 9
        _ascii("##________", "..........", "[_________"),  # 10 balcón al alba
        _ascii("______####", ".._.......", "_____h____"),  # 11 poción
        _ascii("____^^^___", "........_.", "__________"),  # 12
        _ascii("##########", "..........", "___LL_____"),  # 13 losas → 5
        _ascii("##########", "...b...b..", "___B___B__"),  # 14
        _ascii(  # 15
            "______####",
            "..........",
            "_____T____",
            guards=(G_S(col=4, row=2, direction=0, skill=5),),
        ),
        _ascii("####______", "._......._", "____X_X___"),  # 16
        _ascii("##########", "......__..", "___P______"),  # 17 placa
        _ascii("____######", "....b.b...", "____B_B___"),  # 18
        _ascii("##________", "...|.|.|..", "__________"),  # 19
        _ascii("____######", ".........#", "____H____#"),  # 20 poción grande
    ]
    doorlinks = (
        DoorLink(plate_room=5, plate_col=2, plate_row=2, gate_room=5, gate_col=5, gate_row=2),
        DoorLink(plate_room=17, plate_col=3, plate_row=2, gate_room=5, gate_col=5, gate_row=2),
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
    """Dominios del visir: ladrillo púrpura, estandartes con la media luna y
    ceniza en el aire. Guardias de élite, el espejo donde el kid se funde
    con su sombra y la sala donde aparece el visir; la salida baja a la
    galería sur, cuya reja abren dos placas lejanas."""
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
        _ascii("____######", "^^^.......", "___X__X___"),  # 2
        _ascii(  # 3 la poción grande sobre la columna
            "##########",
            "..H....b..",
            "__B____B__",
            guards=(G_S(col=5, row=2, direction=-1, skill=7),),
        ),
        _ascii("____######", "...^^^^...", "____LL.___"),  # 4 losas y hueco
        _ascii("_t__tt__t_", "..........", "_____M__h_"),  # 5 el espejo: fusión
        _ascii("######____", "......^^^^", "_____L____"),  # 6
        _ascii("##########", ".b......S.", "_BS_____B_"),  # 7 aparece el visir
        _ascii("____######", "..........", "_______Dd_"),  # 8 salida
        # --- Galería sur --------------------------------------------------
        _ascii("##########", "#..|..|...", "_____T____"),  # 9
        _ascii("____######", "....b.b...", "____B_B___"),  # 10
        _ascii("___^^^____", "........_.", "__________"),  # 11
        _ascii("######____", "..........", "[_________"),  # 12 balcón
        _ascii("____######", ".._.......", "_____P____"),  # 13 placa
        _ascii("##########", "..........", "____G_____"),  # 14 reja
        _ascii("______####", "...b..b...", "___B__B___"),  # 15
        _ascii("##________", "......__..", "_____f____"),  # 16 pluma
        _ascii("____######", "..........", "_____k____"),  # 17
        _ascii("##________", "...|.|.|..", "__________"),  # 18
        _ascii("#####_____", "..........", "____X_X___"),  # 19
        _ascii(  # 20 el campeón del visir
            "##########",
            "..........",
            "__________",
            guards=(G_S(col=5, row=2, direction=0, skill=8),),
        ),
        _ascii("____######", ".__.......", "_____P____"),  # 21 segunda placa
        _ascii("######____", "....b.....", "____B__T__"),  # 22
        _ascii("____######", "......__..", "_____L____"),  # 23
        _ascii("##########", ".........#", "____H____#"),  # 24 poción grande
    ]
    doorlinks = (
        DoorLink(plate_room=13, plate_col=5, plate_row=2, gate_room=14, gate_col=4, gate_row=2),
        DoorLink(plate_room=21, plate_col=5, plate_row=2, gate_room=14, gate_col=4, gate_row=2),
    )
    events = (
        Event(EventKind.SHADOW_FUSION, room=5, col=5),
        Event(EventKind.VIZIER_INIT, room=7),
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
    """La huida final: el palacio se viene abajo. Dieciocho salas en hilera,
    sin guardias: cuchillas, pinchos, fosos sin fondo y losas sueltas,
    entre cascotes y ceniza, hasta la puerta que lleva a la princesa."""
    grid = """
     1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18
    """
    specs = [
        _ascii("##########", "#.........", "___X_X_X__"),  # 1 tres cuchillas
        _ascii("____######", "..........", "__S_SLS_S_"),  # 2 pinchos y losa
        _ascii("######____", "..........", "__S_..._S_"),  # 3 foso entre pinchos
        _ascii("____######", "...|..|...", "__________"),  # 4
        _ascii("##______##", "...^^^^...", "____..____"),  # 5 foso
        _ascii("######____", "........_.", "_____X____"),  # 6
        _ascii("____######", "^^........", "__S_____S_"),  # 7
        _ascii("____^^____", ".._.......", "__________"),  # 8
        _ascii("##########", "..^^^^^^..", "_____L____"),  # 9
        _ascii("____######", "..........", "___X___X__"),  # 10
        _ascii("######____", ".._.......", "_________]"),  # 11 balcón
        _ascii("____######", "...|.|.|..", "__________"),  # 12
        _ascii("##########", "...b...b..", "___B_T_B__"),  # 13
        _ascii("____######", "......__..", "__S_S_S___"),  # 14
        _ascii("######____", "...b...b..", "___B___B__"),  # 15
        _ascii("____######", "^^^^......", "____X_X___"),  # 16
        _ascii("___^^^^___", "........_.", "__________"),  # 17
        _ascii("##########", ".........#", "_______Dd_"),  # 18 la puerta
    ]
    return _build_level(
        number=13,
        name="Final Run",
        specs=specs,
        grid=grid,
        start_room=1,
        start_col=1,
        start_row=2,
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
