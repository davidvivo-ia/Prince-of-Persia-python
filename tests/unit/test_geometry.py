"""Tests de geometría."""

from __future__ import annotations

import dataclasses

import pytest

from pop2026.domain.geometry import Facing, Position


class TestFacing:
    def test_opposite_is_involutive(self) -> None:
        assert Facing.LEFT.opposite() is Facing.RIGHT
        assert Facing.RIGHT.opposite() is Facing.LEFT
        assert Facing.LEFT.opposite().opposite() is Facing.LEFT


class TestPosition:
    def test_shift_default_is_identity(self) -> None:
        p = Position(3, 4)
        assert p.shifted() == p

    def test_shift_by_drow_dcol(self) -> None:
        p = Position(3, 4)
        assert p.shifted(drow=1, dcol=-2) == Position(4, 2)

    def test_step_right(self) -> None:
        assert Position(0, 0).step(Facing.RIGHT, 3) == Position(0, 3)

    def test_step_left(self) -> None:
        assert Position(5, 5).step(Facing.LEFT, 2) == Position(5, 3)

    def test_position_is_frozen(self) -> None:
        p = Position(1, 1)
        with pytest.raises(dataclasses.FrozenInstanceError):
            p.row = 2  # type: ignore[misc]
