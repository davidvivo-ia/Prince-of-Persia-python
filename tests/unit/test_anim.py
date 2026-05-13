"""Tests del módulo de animación sub-celda."""

from __future__ import annotations

import pytest

from pop2026.domain.actions import Action, duration_ticks
from pop2026.domain.anim import offset_for


class TestNoOffsetActions:
    @pytest.mark.parametrize(
        "action",
        [Action.STAND, Action.CROUCH, Action.DEAD],
    )
    def test_returns_zero_offset(self, action: Action) -> None:
        dx, dy = offset_for(action=action, ticks=0, facing_value=1)
        assert dx == 0.0
        assert dy == 0.0


class TestWalkRun:
    def test_run_progresses_dx_forward(self) -> None:
        dur = duration_ticks(Action.RUN)
        dx_start, _ = offset_for(action=Action.RUN, ticks=0, facing_value=1)
        dx_mid, _ = offset_for(action=Action.RUN, ticks=dur // 2, facing_value=1)
        assert dx_start == 0.0
        assert 0.0 < dx_mid < 1.0

    def test_run_left_is_negative(self) -> None:
        dx, _ = offset_for(action=Action.RUN, ticks=3, facing_value=-1)
        assert dx < 0


class TestJumps:
    def test_jump_v_no_horizontal_movement(self) -> None:
        dx, dy = offset_for(action=Action.JUMP_V, ticks=5, facing_value=1)
        assert dx == 0.0
        assert dy < 0  # va hacia arriba en el medio del salto

    def test_jump_r_advances_two_cells(self) -> None:
        dur = duration_ticks(Action.JUMP_R)
        dx_end, _ = offset_for(action=Action.JUMP_R, ticks=dur - 1, facing_value=1)
        assert dx_end > 1.5  # cerca de +2

    def test_jump_r_arcs_up(self) -> None:
        dur = duration_ticks(Action.JUMP_R)
        _, dy_mid = offset_for(action=Action.JUMP_R, ticks=dur // 2, facing_value=1)
        assert dy_mid < 0


class TestFall:
    def test_fall_progresses_downward(self) -> None:
        dur = duration_ticks(Action.FALL)
        _, dy0 = offset_for(action=Action.FALL, ticks=0, facing_value=1)
        _, dy_end = offset_for(action=Action.FALL, ticks=dur - 1, facing_value=1)
        assert dy0 == 0.0
        assert dy_end > 0


class TestClimb:
    def test_climb_up_goes_up_and_forward(self) -> None:
        dur = duration_ticks(Action.CLIMB_UP)
        dx_end, dy_end = offset_for(action=Action.CLIMB_UP, ticks=dur - 1, facing_value=1)
        assert dx_end > 0.5  # avanza hacia adelante
        assert dy_end < -1.0  # sube ~2 celdas

    def test_climb_down_goes_down_and_forward(self) -> None:
        dur = duration_ticks(Action.CLIMB_DOWN)
        dx_end, dy_end = offset_for(action=Action.CLIMB_DOWN, ticks=dur - 1, facing_value=1)
        assert dx_end > 0
        assert dy_end > 0


class TestCombat:
    def test_strike_lunges_forward(self) -> None:
        dx, _ = offset_for(action=Action.STRIKE, ticks=2, facing_value=1)
        assert dx > 0

    def test_parry_minor_sway(self) -> None:
        dx, _ = offset_for(action=Action.PARRY, ticks=2, facing_value=1)
        assert abs(dx) < 0.1

    def test_hurt_recoils(self) -> None:
        dx, _ = offset_for(action=Action.HURT, ticks=0, facing_value=1)
        # retrocede en sentido opuesto al facing
        assert dx < 0
