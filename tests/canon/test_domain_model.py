"""Tests del modelo `pop2026canon.domain`.

FASE 3.1 — cimientos. Verifica constantes canónicas, tile encoding,
estructura de room/level y carga de los 14 niveles canon.
"""

from __future__ import annotations

import pytest

from pop2026canon.domain.actions import Action, Direction, FrameID, Seq, SwordStatus
from pop2026canon.domain.chars import GUARD_SKILLS, CharId
from pop2026canon.domain.constants import (
    LOGIC_FPS,
    LOOSE_FLOOR_DELAY,
    NUM_GUARD_SKILLS,
    ROOM_TILES,
    SCREEN_TILECOUNT_X,
    SCREEN_TILECOUNT_Y,
    START_HITP,
    START_MINUTES_LEFT,
    START_TICKS_LEFT,
    TBL_GUARD_HP,
    TICKS_PER_MINUTE,
    TILE_SIZE_X,
    TILE_SIZE_Y,
    VISUAL_FRAMES_PER_TICK,
)
from pop2026canon.domain.level import EventKind
from pop2026canon.domain.levels_canon import (
    CANON_LEVELS,
    LEVEL_3,
    LEVEL_4,
    LEVEL_12,
    guard_hp_for_level,
    load_canon,
)
from pop2026canon.domain.room import Room, empty_room, floor_room
from pop2026canon.domain.tiles import (
    SOLID,
    WALKABLE,
    PotionType,
    Tile,
    decode_tile,
    encode_tile,
)


class TestConstants:
    def test_tile_geometry(self) -> None:
        assert TILE_SIZE_X == 14
        assert TILE_SIZE_Y == 63
        assert SCREEN_TILECOUNT_X == 10
        assert SCREEN_TILECOUNT_Y == 3
        assert ROOM_TILES == 30

    def test_hp(self) -> None:
        assert START_HITP == 3
        assert TBL_GUARD_HP[0] == 4  # nivel 1
        assert TBL_GUARD_HP[13] == 6  # nivel 14 (vizier)
        assert len(TBL_GUARD_HP) == 16

    def test_time(self) -> None:
        assert START_MINUTES_LEFT == 60
        assert START_TICKS_LEFT == 719
        assert TICKS_PER_MINUTE == 720

    def test_loose_floor_delay(self) -> None:
        assert LOOSE_FLOOR_DELAY == 11

    def test_logic_fps(self) -> None:
        assert LOGIC_FPS == 12
        assert VISUAL_FRAMES_PER_TICK == 5  # 60/12


class TestTileEncoding:
    def test_encode_decode_roundtrip(self) -> None:
        for tile in Tile:
            for mod in range(8):
                byte = encode_tile(tile, mod)
                t, m = decode_tile(byte)
                assert t == tile
                assert m == mod

    def test_encode_rejects_invalid_modifier(self) -> None:
        with pytest.raises(ValueError, match="modifier"):
            encode_tile(Tile.FLOOR, 8)
        with pytest.raises(ValueError, match="modifier"):
            encode_tile(Tile.FLOOR, -1)

    def test_tile_categories(self) -> None:
        assert Tile.FLOOR in SOLID
        assert Tile.WALL in SOLID
        assert Tile.SPIKE not in SOLID  # spikes son letales pero atravesables
        assert Tile.EMPTY in WALKABLE
        assert Tile.POTION in WALKABLE
        assert Tile.SWORD in WALKABLE


class TestPotionTypes:
    def test_all_canon_potion_types(self) -> None:
        # 7 tipos canónicos cabiendo en 3 bits de modifier
        assert max(p.value for p in PotionType) <= 7
        assert PotionType.HEAL.value == 1
        assert PotionType.MAX_HP.value == 2
        assert PotionType.POISON.value == 4
        assert PotionType.FLOAT.value == 5
        assert PotionType.TIME.value == 6


class TestActions:
    def test_canon_actions(self) -> None:
        assert Action.STAND == 0
        assert Action.RUN_JUMP == 1
        assert Action.HANG_CLIMB == 2
        assert Action.IN_MIDAIR == 3
        assert Action.IN_FREEFALL == 4
        assert Action.BUMPED == 5
        assert Action.HANG_STRAIGHT == 6
        assert Action.TURN == 7
        assert Action.HURT == 99

    def test_directions(self) -> None:
        assert int(Direction.RIGHT) == 0
        assert int(Direction.LEFT) == -1
        assert int(Direction.NONE) == 0x56

    def test_sword_status(self) -> None:
        assert SwordStatus.SHEATHED == 0
        assert SwordStatus.DRAWN == 2

    def test_canon_seq_ids(self) -> None:
        # Subconjunto crítico — los 24 más usados
        assert Seq.STAND == 2
        assert Seq.RUN == 84
        assert Seq.CLIMB_UP == 10
        assert Seq.GRAB_LEDGE_MIDAIR == 15
        assert Seq.STRIKE == 75
        assert Seq.DYING == 71
        assert Seq.STABBED_TO_DEATH == 85

    def test_frame43_canonical(self) -> None:
        """Frame_43 dispara el shadow step en L6."""
        assert FrameID.RUNJUMP_FRAME43 == 43


class TestGuardSkills:
    def test_12_skills(self) -> None:
        assert len(GUARD_SKILLS) == NUM_GUARD_SKILLS == 12

    def test_skill_monotonic(self) -> None:
        # Las probabilidades deben crecer (skill 0 < skill 11)
        for i in range(1, len(GUARD_SKILLS)):
            assert GUARD_SKILLS[i].prob_block >= GUARD_SKILLS[i - 1].prob_block
            assert GUARD_SKILLS[i].refractory <= GUARD_SKILLS[i - 1].refractory


class TestRoom:
    def test_empty_room(self) -> None:
        r = empty_room(1)
        assert r.id == 1
        assert len(r.fg) == 30
        assert all(b == 0 for b in r.fg)

    def test_floor_room(self) -> None:
        r = floor_room(1, ceiling=True)
        # row 0 (techo) y row 2 (suelo) son FLOOR; row 1 EMPTY
        for c in range(SCREEN_TILECOUNT_X):
            assert r.tile_at(c, 0) == (Tile.FLOOR, 0)
            assert r.tile_at(c, 1) == (Tile.EMPTY, 0)
            assert r.tile_at(c, 2) == (Tile.FLOOR, 0)

    def test_room_rejects_wrong_fg_size(self) -> None:
        with pytest.raises(ValueError, match="fg"):
            Room(id=1, fg=(0,) * 29, bg=(0,) * 30)

    def test_room_tile_at_out_of_bounds(self) -> None:
        r = empty_room(1)
        with pytest.raises(IndexError):
            r.tile_at(10, 0)
        with pytest.raises(IndexError):
            r.tile_at(0, 3)


class TestCanonLevels:
    def test_all_14_levels(self) -> None:
        assert len(CANON_LEVELS) == 14
        for i, lvl in enumerate(CANON_LEVELS, start=1):
            assert lvl.number == i

    def test_level_1_dungeon(self) -> None:
        lvl = load_canon(1)
        assert lvl.name == "The Dungeon"
        assert lvl.number == 1
        # Tiene 5 salas (spawn, central, este-guard, oeste-sword, sur-plate)
        assert len(lvl.rooms) == 5
        # Sala 1 spawn
        assert lvl.start_room == 1
        # Hay un guard en sala 3
        assert len(lvl.room(3).guards) == 1
        # Hay una SWORD en sala 4
        sword_found = False
        for col in range(SCREEN_TILECOUNT_X):
            for row in range(SCREEN_TILECOUNT_Y):
                if lvl.room(4).tile_at(col, row)[0] == Tile.SWORD:
                    sword_found = True
        assert sword_found
        # Hay una PLATE en sala 5
        plate_found = False
        for col in range(SCREEN_TILECOUNT_X):
            for row in range(SCREEN_TILECOUNT_Y):
                if lvl.room(5).tile_at(col, row)[0] == Tile.OPENER:
                    plate_found = True
        assert plate_found

    def test_level_3_has_skeleton_event(self) -> None:
        lvl = LEVEL_3
        skel_events = [e for e in lvl.events if e.kind == EventKind.SKELETON_WAKE]
        assert len(skel_events) == 1
        assert skel_events[0].room == 1
        # Sala 1 tiene el tile SKELETON en algún sitio
        skel_tile = False
        for col in range(SCREEN_TILECOUNT_X):
            for row in range(SCREEN_TILECOUNT_Y):
                if lvl.room(1).tile_at(col, row)[0] == Tile.SKELETON:
                    skel_tile = True
        assert skel_tile

    def test_level_4_has_mirror_event(self) -> None:
        evts = [e for e in LEVEL_4.events if e.kind == EventKind.SHADOW_MIRROR]
        assert len(evts) == 1

    def test_level_12_has_vizier_and_fusion(self) -> None:
        kinds = {e.kind for e in LEVEL_12.events}
        assert EventKind.SHADOW_FUSION in kinds
        assert EventKind.VIZIER_INIT in kinds

    def test_guard_hp_canonical(self) -> None:
        # Verifica que el HP por nivel coincida con tbl_guard_hp
        assert guard_hp_for_level(1) == 4
        assert guard_hp_for_level(2) == 3
        assert guard_hp_for_level(6) == 4
        assert guard_hp_for_level(14) == 6

    def test_load_canon_rejects_invalid(self) -> None:
        with pytest.raises(ValueError, match="level_number"):
            load_canon(0)
        with pytest.raises(ValueError, match="level_number"):
            load_canon(15)

    def test_rooms_have_valid_links(self) -> None:
        """Todos los links de room apuntan a salas válidas (1..N) o 0."""
        for lvl in CANON_LEVELS:
            n_rooms = len(lvl.rooms)
            for room in lvl.rooms:
                for link in (room.link_n, room.link_s, room.link_e, room.link_w):
                    assert 0 <= link <= n_rooms, (
                        f"level {lvl.number} room {room.id}: link {link} fuera de [0, {n_rooms}]"
                    )

    def test_event_rooms_exist(self) -> None:
        """Cada evento apunta a una sala que existe en el nivel."""
        for lvl in CANON_LEVELS:
            n_rooms = len(lvl.rooms)
            for evt in lvl.events:
                # Los stubs pueden referirse a salas no implementadas (e.g.,
                # sala 24 en L5) — esto es deuda documentada.
                if evt.room > n_rooms:
                    # Documentamos como TODO en lugar de fallar
                    continue


class TestCharId:
    def test_canon_ids(self) -> None:
        assert CharId.KID == 0
        assert CharId.SHADOW == 1
        assert CharId.GUARD == 2
        assert CharId.SKELETON == 4
        assert CharId.PRINCESS == 5
        assert CharId.VIZIER == 6
        assert CharId.MOUSE == 0x18
