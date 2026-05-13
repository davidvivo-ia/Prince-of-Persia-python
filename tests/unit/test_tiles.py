"""Tests de tiles."""

from __future__ import annotations

import pytest

from pop2026.domain.tiles import CHAR_TO_TILE, SOLID, TILE_TO_CHAR, WALKABLE_OVER, Tile


class TestTileMaps:
    @pytest.mark.parametrize("ch", list("#=^|_+->@gG."))
    def test_every_known_char_maps(self, ch: str) -> None:
        assert ch in CHAR_TO_TILE

    def test_reverse_map_is_inverse(self) -> None:
        for ch, tile in CHAR_TO_TILE.items():
            assert TILE_TO_CHAR[tile] == ch

    def test_unknown_char_not_in_map(self) -> None:
        assert "%" not in CHAR_TO_TILE


class TestTileSets:
    def test_floor_is_solid(self) -> None:
        assert Tile.FLOOR in SOLID

    def test_loose_floor_is_solid(self) -> None:
        assert Tile.LOOSE_FLOOR in SOLID

    def test_empty_is_walkable_not_solid(self) -> None:
        assert Tile.EMPTY in WALKABLE_OVER
        assert Tile.EMPTY not in SOLID

    def test_gate_is_solid(self) -> None:
        assert Tile.GATE in SOLID

    def test_spikes_are_walkable_through(self) -> None:
        # se puede entrar; el daño viene por caída en game.py
        assert Tile.SPIKES in WALKABLE_OVER
