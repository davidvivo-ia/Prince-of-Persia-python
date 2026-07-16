"""Importador de LEVELS.DAT — probado con un blob sintético.

El repo NO incluye datos del juego original: el test construye un nivel
de 2305 bytes desde cero con el layout documentado y verifica que el
importador lo decodifica al dominio correctamente.
"""

from __future__ import annotations

import struct

import pytest

from pop2026canon.domain.tiles import PotionType, Tile
from pop2026canon.infrastructure.levels_dat import (
    LEVEL_BLOB_SIZE,
    load_original_levels,
    parse_level_blob,
)


def _blank_blob() -> bytearray:
    return bytearray(LEVEL_BLOB_SIZE)


def _set_tile(blob: bytearray, room: int, col: int, row: int, tile: Tile, mod: int = 0) -> None:
    idx = (room - 1) * 30 + row * 10 + col
    blob[idx] = int(tile)
    blob[720 + idx] = mod


def _make_level_blob() -> bytearray:
    """Nivel sintético: 2 salas enlazadas E/W, kid, guard, potion,
    plate→gate por cadena de doorlinks."""
    blob = _blank_blob()
    # Suelo en row 2 de las salas 1 y 2
    for c in range(10):
        _set_tile(blob, 1, c, 2, Tile.FLOOR)
        _set_tile(blob, 2, c, 2, Tile.FLOOR)
    # Potion feather (modifier DAT 3 → nuestro FLOAT=5)
    _set_tile(blob, 1, 4, 1, Tile.POTION, mod=3)
    # Plate en sala 1 (5,1) con cadena de doorlinks en el índice 2
    _set_tile(blob, 1, 5, 1, Tile.OPENER, mod=2)
    # Gate en sala 2 (3,1)
    _set_tile(blob, 2, 3, 1, Tile.GATE, mod=0)
    # Cadena de doorlinks (índice 2): una entrada → sala 2 tile 13, fin.
    tilepos = 13
    room = 2
    b1 = tilepos | ((room & 0x03) << 5) | 0x80  # bit 7 = fin
    b2 = (room >> 2) << 5
    blob[1440 + 2] = b1
    blob[1696 + 2] = b2
    # Room links: 1.right=2, 2.left=1
    struct.pack_into("<4B", blob, 1952 + 0 * 4, 0, 2, 0, 0)
    struct.pack_into("<4B", blob, 1952 + 1 * 4, 1, 0, 0, 0)
    # used_rooms
    blob[2048] = 2
    # Start: sala 1, tile 21 (col 1, row 2), dir 0xFF (=derecha tras ~)
    blob[2112] = 1
    blob[2113] = 21
    blob[2114] = 0xFF
    # Guard en sala 2: tile 15 (col 5, row 1), dir 0xFF (izquierda), skill 3
    blob[2119 + 1] = 15
    blob[2143 + 1] = 0xFF
    blob[2215 + 1] = 3
    return blob


class TestParseLevelBlob:
    def test_size_check(self) -> None:
        with pytest.raises(ValueError, match="2305"):
            parse_level_blob(b"\x00" * 100, number=1)

    def test_rooms_and_links(self) -> None:
        lvl = parse_level_blob(bytes(_make_level_blob()), number=1)
        assert len(lvl.rooms) == 24
        assert lvl.room(1).link_e == 2
        assert lvl.room(2).link_w == 1

    def test_tiles_decoded(self) -> None:
        lvl = parse_level_blob(bytes(_make_level_blob()), number=1)
        room1 = lvl.room(1)
        assert room1.tile_at(0, 2)[0] is Tile.FLOOR
        assert room1.tile_at(4, 1)[0] is Tile.POTION

    def test_potion_modifier_remapped(self) -> None:
        lvl = parse_level_blob(bytes(_make_level_blob()), number=1)
        _, mod = lvl.room(1).tile_at(4, 1)
        assert mod == int(PotionType.FLOAT), "feather del DAT (3) → FLOAT nuestro (5)"

    def test_start_position_and_direction(self) -> None:
        lvl = parse_level_blob(bytes(_make_level_blob()), number=1)
        assert lvl.start_room == 1
        assert lvl.start_col == 1
        assert lvl.start_row == 2
        # 0xFF guardado = mirar a la DERECHA (el motor invierte)
        assert lvl.start_direction == 0

    def test_guard_spawn(self) -> None:
        lvl = parse_level_blob(bytes(_make_level_blob()), number=1)
        guards = lvl.room(2).guards
        assert len(guards) == 1
        assert (guards[0].col, guards[0].row) == (5, 1)
        assert guards[0].direction == -1
        assert guards[0].skill == 3

    def test_doorlink_chain_resolved(self) -> None:
        lvl = parse_level_blob(bytes(_make_level_blob()), number=1)
        assert len(lvl.doorlinks) == 1
        link = lvl.doorlinks[0]
        assert link.plate_coord == (1, 5, 1)
        assert link.gate_coord == (2, 3, 1)

    def test_opener_modifier_cleared(self) -> None:
        """El modifier del OPENER es un índice de doorlink — no debe
        filtrarse al tile empaquetado (sólo caben 3 bits)."""
        lvl = parse_level_blob(bytes(_make_level_blob()), number=1)
        _, mod = lvl.room(1).tile_at(5, 1)
        assert mod == 0


class TestLoadFromDirectory:
    def test_load_res_bins(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        (tmp_path / "res2001.bin").write_bytes(bytes(_make_level_blob()))
        levels = load_original_levels(tmp_path)
        assert list(levels) == [1]
        assert levels[1].name == "The Dungeon"


class TestLoadFromDatArchive:
    def test_load_dat_container(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        blob = bytes(_make_level_blob())
        # DAT v1: header (u32 table_offset, u16 table_size) + payloads
        # con byte de checksum + tabla {u16 count, {u16 id,u32 off,u16 size}}
        payload_offset = 6
        body = b"\x00" + blob  # checksum + datos
        table_offset = payload_offset + len(body)
        table = struct.pack("<H", 1) + struct.pack("<HIH", 2001, payload_offset, len(blob))
        raw = struct.pack("<IH", table_offset, len(table)) + body + table
        dat = tmp_path / "LEVELS.DAT"
        dat.write_bytes(raw)
        levels = load_original_levels(dat)
        assert list(levels) == [1]
        assert levels[1].room(1).link_e == 2
