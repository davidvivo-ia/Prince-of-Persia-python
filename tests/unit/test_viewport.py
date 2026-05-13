"""Tests del viewport por habitaciones (F-3, room-flick)."""

from __future__ import annotations

from pop2026.presentation.renderer import total_rooms, viewport_col
from pop2026.presentation.theme import LAYOUT


class TestViewportCol:
    def test_single_room_always_zero(self) -> None:
        # Nivel del tamaño exacto de una habitación
        assert viewport_col(0, LAYOUT.cols) == 0
        assert viewport_col(LAYOUT.cols - 1, LAYOUT.cols) == 0

    def test_smaller_level_always_zero(self) -> None:
        # Nivel más pequeño que una habitación
        assert viewport_col(5, 10) == 0

    def test_two_rooms_flick_at_boundary(self) -> None:
        # 40 celdas = 2 habitaciones de 20
        assert viewport_col(0, 40) == 0
        assert viewport_col(LAYOUT.cols - 1, 40) == 0
        assert viewport_col(LAYOUT.cols, 40) == LAYOUT.cols
        assert viewport_col(LAYOUT.cols + 5, 40) == LAYOUT.cols
        assert viewport_col(39, 40) == LAYOUT.cols

    def test_three_rooms(self) -> None:
        cols = LAYOUT.cols * 3
        assert viewport_col(0, cols) == 0
        assert viewport_col(LAYOUT.cols, cols) == LAYOUT.cols
        assert viewport_col(LAYOUT.cols * 2, cols) == LAYOUT.cols * 2

    def test_overflow_clamps_to_last_room(self) -> None:
        # Si la columna del príncipe supera el nivel, el viewport se mantiene
        # en la última habitación válida.
        assert viewport_col(9999, 40) == LAYOUT.cols


class TestTotalRooms:
    def test_zero_cols(self) -> None:
        assert total_rooms(0) == 0

    def test_one_room_exact(self) -> None:
        assert total_rooms(LAYOUT.cols) == 1

    def test_partial_room_rounds_up(self) -> None:
        assert total_rooms(LAYOUT.cols + 1) == 2

    def test_two_rooms_exact(self) -> None:
        assert total_rooms(LAYOUT.cols * 2) == 2

    def test_three_rooms(self) -> None:
        assert total_rooms(LAYOUT.cols * 3) == 3
