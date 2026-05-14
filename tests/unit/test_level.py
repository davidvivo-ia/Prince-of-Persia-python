"""Tests del parser de niveles."""

from __future__ import annotations

import pytest

from pop2026.domain.errors import LevelLoadError
from pop2026.domain.geometry import Position
from pop2026.domain.level import Level, LevelState, effective_tile
from pop2026.domain.tiles import Tile

SIMPLE = """
##########
#..@....>#
##########
"""

WITH_GUARD = """
##########
#..@..g..#
##########
"""


class TestLevelParse:
    def test_parse_simple(self) -> None:
        lv = Level.parse(SIMPLE, name="t")
        assert lv.rows == 3
        assert lv.cols == 10
        assert lv.prince_spawn == Position(1, 3)
        assert lv.tile_at(Position(1, 8)) is Tile.EXIT

    def test_parse_with_guard(self) -> None:
        lv = Level.parse(WITH_GUARD)
        assert len(lv.guard_spawns) == 1
        pos, skill = lv.guard_spawns[0]
        assert pos == Position(1, 6)
        assert skill == 1

    def test_parse_empty_raises(self) -> None:
        with pytest.raises(LevelLoadError):
            Level.parse("")

    def test_parse_unknown_char_raises(self) -> None:
        with pytest.raises(LevelLoadError):
            Level.parse("@?>\n")

    def test_parse_missing_prince_raises(self) -> None:
        with pytest.raises(LevelLoadError):
            Level.parse("######\n#....#\n######\n")

    def test_tile_at_out_of_bounds_is_floor(self) -> None:
        lv = Level.parse(SIMPLE)
        assert lv.tile_at(Position(-1, 0)) is Tile.FLOOR
        assert lv.tile_at(Position(100, 100)) is Tile.FLOOR

    def test_level_default_time_limit_is_none(self) -> None:
        lv = Level.parse(SIMPLE)
        assert lv.time_limit_ticks is None

    def test_level_with_explicit_time_limit(self) -> None:
        from dataclasses import replace

        lv = replace(Level.parse(SIMPLE), time_limit_ticks=3600)
        assert lv.time_limit_ticks == 3600


class TestLevelState:
    def test_effective_tile_respects_open_gate(self) -> None:
        src = "##########\n#..@.|..>#\n##########\n"
        lv = Level.parse(src)
        gate = Position(1, 5)
        st = LevelState().with_open(gate)
        assert effective_tile(lv, st, gate) is Tile.EMPTY

    def test_effective_tile_respects_fallen_floor(self) -> None:
        src = "##########\n#..@.=..>#\n##########\n"
        lv = Level.parse(src)
        pos = Position(1, 5)
        st = LevelState().with_floor_fallen(pos)
        assert effective_tile(lv, st, pos) is Tile.EMPTY

    def test_effective_tile_respects_consumed_potion(self) -> None:
        src = "##########\n#..@.+..>#\n##########\n"
        lv = Level.parse(src)
        pos = Position(1, 5)
        st = LevelState().with_potion_consumed(pos)
        assert effective_tile(lv, st, pos) is Tile.EMPTY
