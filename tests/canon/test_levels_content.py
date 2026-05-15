"""Validaciones de mecánicas canon presentes en cada nivel.

Después de la pasada de refinement de L4-L13, cada nivel debe tener
los tiles y eventos clave que lo identifican. Estos tests fallan si
un cambio futuro borra accidentalmente la mecánica canon de un nivel.
"""

from __future__ import annotations

from pop2026canon.domain.level import EventKind
from pop2026canon.domain.levels_canon import (
    CANON_LEVELS,
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
from pop2026canon.domain.tiles import Tile


def _has_tile(level, tile: Tile) -> bool:  # type: ignore[no-untyped-def]
    for room in level.rooms:
        for byte in room.fg:
            if (byte & 0x1F) == int(tile):
                return True
    return False


def _has_event(level, kind: EventKind) -> bool:  # type: ignore[no-untyped-def]
    return any(e.kind is kind for e in level.events)


def _has_exit_door(level) -> bool:  # type: ignore[no-untyped-def]
    return _has_tile(level, Tile.LEVEL_DOOR_LEFT) and _has_tile(level, Tile.LEVEL_DOOR_RIGHT)


class TestAllLevelsHaveExit:
    """Cada nivel jugable (1-13) tiene puerta de exit. L14 es cinemática."""

    def test_levels_1_to_13_have_exit(self) -> None:
        for lvl in CANON_LEVELS[:13]:
            assert _has_exit_door(lvl), f"L{lvl.number} sin exit door"


class TestAllLevelsRoomCount:
    """Cada nivel tiene un número canon de salas (no degenerado)."""

    def test_room_counts(self) -> None:
        # (level_number, min_rooms_expected) — canon expandido 18-24 salas
        expected = {
            1: 18,
            2: 20,
            3: 18,
            4: 20,
            5: 20,
            6: 18,
            7: 22,
            8: 20,
            9: 20,
            10: 20,
            11: 20,
            12: 24,
            13: 18,
            14: 1,
        }
        for lvl in CANON_LEVELS:
            assert len(lvl.rooms) >= expected[lvl.number], (
                f"L{lvl.number} tiene {len(lvl.rooms)} salas, esperaba >= {expected[lvl.number]}"
            )


class TestLevelTilesByLevel:
    def test_l1_has_sword(self) -> None:
        assert _has_tile(LEVEL_1, Tile.SWORD)

    def test_l1_has_plate(self) -> None:
        assert _has_tile(LEVEL_1, Tile.OPENER)

    def test_l2_has_chomper(self) -> None:
        assert _has_tile(LEVEL_2, Tile.CHOMPER)

    def test_l3_has_skeleton(self) -> None:
        assert _has_tile(LEVEL_3, Tile.SKELETON)
        assert _has_event(LEVEL_3, EventKind.SKELETON_WAKE)

    def test_l4_has_mirror_and_event(self) -> None:
        assert _has_tile(LEVEL_4, Tile.MIRROR)
        assert _has_event(LEVEL_4, EventKind.SHADOW_MIRROR)

    def test_l4_has_doorlink(self) -> None:
        assert len(LEVEL_4.doorlinks) >= 1

    def test_l5_has_potion_and_steal_event(self) -> None:
        assert _has_tile(LEVEL_5, Tile.POTION)
        assert _has_event(LEVEL_5, EventKind.SHADOW_STEAL)

    def test_l5_has_loose_floors(self) -> None:
        assert _has_tile(LEVEL_5, Tile.LOOSE)

    def test_l6_has_runjump_event(self) -> None:
        assert _has_event(LEVEL_6, EventKind.SHADOW_STEP)
        # El evento debe codificar frame_43 como trigger
        step_event = next(e for e in LEVEL_6.events if e.kind is EventKind.SHADOW_STEP)
        assert step_event.extra == 43

    def test_l7_has_loose_and_spikes(self) -> None:
        assert _has_tile(LEVEL_7, Tile.LOOSE)
        assert _has_tile(LEVEL_7, Tile.SPIKE)

    def test_l8_has_mouse_event_and_gate(self) -> None:
        assert _has_event(LEVEL_8, EventKind.MOUSE_APPEAR)
        assert _has_tile(LEVEL_8, Tile.GATE)

    def test_l9_has_skeletons_and_chompers(self) -> None:
        assert _has_tile(LEVEL_9, Tile.SKELETON)
        assert _has_tile(LEVEL_9, Tile.CHOMPER)

    def test_l9_has_doorlink(self) -> None:
        assert len(LEVEL_9.doorlinks) >= 1

    def test_l10_is_vertical(self) -> None:
        """L10 debería tener al menos un link sur (drop)."""
        any_south = any(r.link_s != 0 for r in LEVEL_10.rooms)
        assert any_south, "L10 sin link sur — no es vertical"

    def test_l11_has_self_room_doorlink(self) -> None:
        # L11 tiene plate y gate en la misma sala.
        link = LEVEL_11.doorlinks[0]
        assert link.plate_room == link.gate_room

    def test_l12_has_fusion_and_vizier(self) -> None:
        assert _has_event(LEVEL_12, EventKind.SHADOW_FUSION)
        assert _has_event(LEVEL_12, EventKind.VIZIER_INIT)
        assert _has_tile(LEVEL_12, Tile.MIRROR)

    def test_l13_has_chompers_and_spikes(self) -> None:
        # Final run: carrera de obstáculos
        assert _has_tile(LEVEL_13, Tile.CHOMPER)
        assert _has_tile(LEVEL_13, Tile.SPIKE)

    def test_l14_has_princess_reunion(self) -> None:
        assert _has_event(LEVEL_14, EventKind.PRINCESS_REUNION)


class TestLevelGuardSkillProgression:
    """Skill de guards crece (canon TBL_GUARD_HP también)."""

    def test_l1_easiest_guard(self) -> None:
        for room in LEVEL_1.rooms:
            for g in room.guards:
                assert g.skill <= 2

    def test_l12_has_vizier_skill_11(self) -> None:
        found_high = False
        for room in LEVEL_12.rooms:
            for g in room.guards:
                if g.skill >= 11:
                    found_high = True
        assert found_high, "L12 sin vizier de skill 11+"


class TestRoomLinksConsistency:
    """Los room links no deben apuntar fuera de rango."""

    def test_links_in_range(self) -> None:
        for lvl in CANON_LEVELS:
            n = len(lvl.rooms)
            for room in lvl.rooms:
                for link in (room.link_n, room.link_s, room.link_e, room.link_w):
                    assert 0 <= link <= n, (
                        f"L{lvl.number} room {room.id} link {link} fuera de [0, {n}]"
                    )
