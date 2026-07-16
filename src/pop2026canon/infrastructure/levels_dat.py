"""Importador de LEVELS.DAT — carga los niveles ORIGINALES del POP1.

Este proyecto no distribuye datos del juego original (son propiedad de
Ubisoft). Si posees el juego, este módulo carga sus niveles reales en
nuestro dominio, desde cualquiera de estas fuentes:

- ``LEVELS.DAT`` de la versión MS-DOS (contenedor DAT v1),
- un directorio con blobs sueltos de nivel (``res2001.bin``…, como los
  extrae SDLPoP), o
- un único blob de 2305 bytes.

**Formato de un nivel** (2305 bytes, little-endian, verificado contra
``level_type`` del desensamblado SDLPoP):

========  ======  =====================================================
offset    tamaño  contenido
========  ======  =====================================================
0         720     fg: 24 salas x 30 tiles (bits 0-4 pieza, 5-7 nada)
720       720     modifiers: 24 x 30 (potion type, estado, doorlink idx)
1440      256     doorlinks byte 1 (bits 0-4 tile, 5-6 room-lo, 7 fin)
1696      256     doorlinks byte 2 (bits 0-4 timer, 5-7 room-hi)
1952      96      room links: 24 x (left, right, up, down)
2048      1       used_rooms
2049      48      roomxs/roomys (editor — ignorado)
2097      15      relleno
2112      1       start_room
2113      1       start_pos (0..29)
2114      1       start_dir (0 derecha, 0xFF izquierda)
2115      4       relleno
2119      168     guards: tile/dir/x/seq_lo/skill/seq_hi/color x 24
2287      18      relleno
========  ======  =====================================================
"""

from __future__ import annotations

import struct
from pathlib import Path

from pop2026canon.domain.chars import GuardSpawn
from pop2026canon.domain.level import DoorLink, Level
from pop2026canon.domain.room import Room
from pop2026canon.domain.tiles import Tile

LEVEL_BLOB_SIZE = 2305
ROOMS = 24
ROOM_TILES = 30

CANON_LEVEL_NAMES: dict[int, str] = {
    1: "The Dungeon",
    2: "The Guards",
    3: "The Skeleton",
    4: "The Mirror",
    5: "The Thief",
    6: "The Steps",
    7: "The Mountains",
    8: "The Caverns",
    9: "The Tomb",
    10: "The Tower",
    11: "The Tower II",
    12: "The Vizier",
    13: "Final Run",
    14: "Ending",
}

# Los modifiers de potion del DAT difieren de nuestro PotionType:
# DAT: 0 empty, 1 heal, 2 life, 3 feather, 4 invert, 5 poison, 6 open.
# Nuestro: 0 empty, 1 heal, 2 max_hp, 3 boost, 4 poison, 5 float, 6 time.
_POTION_REMAP = {3: 5, 4: 0, 5: 4}


def parse_level_blob(data: bytes, *, number: int, name: str = "") -> Level:
    """Convierte un blob de 2305 bytes en un :class:`Level` del dominio."""
    if len(data) != LEVEL_BLOB_SIZE:
        raise ValueError(f"blob de nivel debe medir {LEVEL_BLOB_SIZE} bytes, no {len(data)}")

    fg = data[0:720]
    modifiers = data[720:1440]
    doorlinks1 = data[1440:1696]
    doorlinks2 = data[1696:1952]
    roomlinks = data[1952:2048]
    start_room = data[2112]
    start_pos = data[2113]
    # Canon: el motor invierte el valor guardado (`direction = ~start_dir`
    # en seg003.c) — 0xFF en el DAT significa mirar a la DERECHA.
    start_dir = 0 if data[2114] == 0xFF else -1
    guards_tile = data[2119:2143]
    guards_dir = data[2143:2167]
    guards_skill = data[2215:2239]
    guards_color = data[2263:2287]

    rooms: list[Room] = []
    doorlink_pairs: list[DoorLink] = []
    for r in range(ROOMS):
        room_id = r + 1
        room_fg = bytearray(fg[r * ROOM_TILES : (r + 1) * ROOM_TILES])
        room_mod = modifiers[r * ROOM_TILES : (r + 1) * ROOM_TILES]
        packed: list[int] = []
        for t in range(ROOM_TILES):
            piece = room_fg[t] & 0x1F
            mod = room_mod[t]
            if piece == int(Tile.POTION):
                mod = _POTION_REMAP.get(mod, mod)
            if piece in (int(Tile.OPENER), int(Tile.CLOSER)):
                # El modifier es un índice de cadena de doorlinks, no
                # cabe en 3 bits — resolvemos la cadena aquí y el tile
                # se guarda con modifier 0.
                if piece == int(Tile.OPENER):
                    col, row = t % 10, t // 10
                    for gate_room, gate_tile in _walk_doorlink_chain(doorlinks1, doorlinks2, mod):
                        doorlink_pairs.append(
                            DoorLink(
                                plate_room=room_id,
                                plate_col=col,
                                plate_row=row,
                                gate_room=gate_room,
                                gate_col=gate_tile % 10,
                                gate_row=gate_tile // 10,
                            )
                        )
                mod = 0
            packed.append(piece | ((mod & 0x07) << 5))
        left, right, up, down = roomlinks[r * 4 : r * 4 + 4]
        guards: tuple[GuardSpawn, ...] = ()
        if guards_tile[r] < ROOM_TILES:
            gt = guards_tile[r]
            guards = (
                GuardSpawn(
                    col=gt % 10,
                    row=gt // 10,
                    direction=-1 if guards_dir[r] == 0xFF else 0,
                    skill=guards_skill[r] & 0x0F,
                    color=guards_color[r],
                ),
            )
        rooms.append(
            Room(
                id=room_id,
                fg=tuple(packed),
                bg=tuple([0] * ROOM_TILES),
                link_w=left if left <= ROOMS else 0,
                link_e=right if right <= ROOMS else 0,
                link_n=up if up <= ROOMS else 0,
                link_s=down if down <= ROOMS else 0,
                guards=guards,
            )
        )

    return Level(
        number=number,
        name=name or CANON_LEVEL_NAMES.get(number, f"Level {number}"),
        rooms=tuple(rooms),
        start_room=start_room if 1 <= start_room <= ROOMS else 1,
        start_col=start_pos % 10,
        start_row=start_pos // 10,
        start_direction=start_dir,
        events=(),
        doorlinks=tuple(doorlink_pairs),
    )


def _walk_doorlink_chain(dl1: bytes, dl2: bytes, start_index: int) -> list[tuple[int, int]]:
    """Recorre una cadena de doorlinks y devuelve [(room, tilepos), ...].

    Encoding por entrada (verificado en ``seg007.c``):
    - byte1: bits 0-4 tilepos, bits 5-6 room bajo, bit 7 = FIN de cadena
    - byte2: bits 0-4 timer, bits 5-7 room alto
    """
    out: list[tuple[int, int]] = []
    index = start_index
    for _ in range(256):
        if not (0 <= index < len(dl1)):
            break
        b1, b2 = dl1[index], dl2[index]
        room = ((b1 & 0x60) >> 5) + ((b2 & 0xE0) >> 3)
        tilepos = b1 & 0x1F
        if 1 <= room <= ROOMS and tilepos < ROOM_TILES:
            out.append((room, tilepos))
        if b1 & 0x80:
            break
        index += 1
    return out


def _extract_from_dat(path: Path) -> dict[int, bytes]:
    """Extrae los recursos de nivel (ids 2000..2015) de un LEVELS.DAT."""
    raw = path.read_bytes()
    if len(raw) < 6:
        raise ValueError(f"{path} demasiado corto para ser un DAT")
    table_offset, table_size = struct.unpack_from("<IH", raw, 0)
    if table_offset + 2 > len(raw):
        raise ValueError(f"{path}: offset de tabla fuera de rango")
    (res_count,) = struct.unpack_from("<H", raw, table_offset)
    _ = table_size
    blobs: dict[int, bytes] = {}
    for i in range(res_count):
        entry_off = table_offset + 2 + i * 8
        res_id, offset, size = struct.unpack_from("<HIH", raw, entry_off)
        if not (2000 <= res_id <= 2015):
            continue
        # El recurso va precedido de 1 byte de checksum.
        payload = raw[offset + 1 : offset + 1 + size]
        if len(payload) == LEVEL_BLOB_SIZE:
            blobs[res_id - 2000] = payload
    return blobs


def load_original_levels(path: str | Path) -> dict[int, Level]:
    """Carga niveles originales desde ``path``.

    ``path`` puede ser un LEVELS.DAT, un directorio con ``res20NN.bin``
    o un blob suelto de 2305 bytes. Devuelve ``{numero: Level}`` con los
    números de nivel del juego (1..14; el 0 es la demo y el 15 la sala
    de pociones de la protección anticopia).
    """
    p = Path(path)
    blobs: dict[int, bytes] = {}
    if p.is_dir():
        for f in sorted(p.glob("res20*.bin")):
            try:
                num = int(f.stem[3:]) - 2000
            except ValueError:
                continue
            data = f.read_bytes()
            if len(data) == LEVEL_BLOB_SIZE:
                blobs[num] = data
    elif p.stat().st_size == LEVEL_BLOB_SIZE:
        blobs[1] = p.read_bytes()
    else:
        blobs = _extract_from_dat(p)

    levels: dict[int, Level] = {}
    for num, blob in sorted(blobs.items()):
        if not (1 <= num <= 14):
            continue
        levels[num] = parse_level_blob(blob, number=num)
    return levels


def load_campaign(path: str | Path) -> tuple[Level, ...]:
    """Campaña de 14 niveles: los originales de ``path``, completando
    con los niveles fan-recreation para cualquier hueco."""
    from pop2026canon.domain.levels_canon import CANON_LEVELS

    originals = load_original_levels(path)
    return tuple(originals.get(n, CANON_LEVELS[n - 1]) for n in range(1, 15))
