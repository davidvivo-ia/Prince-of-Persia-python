"""Tests del controller — input → transiciones de secuencia."""

from __future__ import annotations

from dataclasses import replace

from pop2026canon.application.controller import Command, apply_input
from pop2026canon.domain.actions import Action, Direction, Seq, SwordStatus
from pop2026canon.domain.chars import Char, CharId


def _kid_standing(direction: int = int(Direction.RIGHT)) -> Char:
    return Char(
        charid=CharId.KID,
        room=1,
        curr_col=3,
        curr_row=1,
        action=Action.STAND,
        curr_seq_id=int(Seq.STAND),
        direction=direction,
    )


class TestCommand:
    def test_default_no_input(self) -> None:
        cmd = Command()
        assert not cmd.any_dir()
        assert not cmd.shift
        assert not cmd.strike

    def test_any_dir(self) -> None:
        assert Command(right=True).any_dir()
        assert Command(up=True).any_dir()
        assert not Command(strike=True).any_dir()


class TestStandTransitions:
    def test_no_input_no_change(self) -> None:
        kid = _kid_standing()
        new_kid = apply_input(kid, Command())
        assert new_kid is kid

    def test_right_starts_run_if_facing_right(self) -> None:
        kid = _kid_standing(direction=int(Direction.RIGHT))
        new_kid = apply_input(kid, Command(right=True))
        assert new_kid.curr_seq_id == int(Seq.START_RUN)

    def test_right_turns_if_facing_left(self) -> None:
        kid = _kid_standing(direction=int(Direction.LEFT))
        new_kid = apply_input(kid, Command(right=True))
        assert new_kid.curr_seq_id == int(Seq.TURN)
        # El facing se invierte tras turn
        assert new_kid.direction == int(Direction.RIGHT)

    def test_left_starts_run_if_facing_left(self) -> None:
        kid = _kid_standing(direction=int(Direction.LEFT))
        new_kid = apply_input(kid, Command(left=True))
        assert new_kid.curr_seq_id == int(Seq.START_RUN)

    def test_up_triggers_standing_jump(self) -> None:
        kid = _kid_standing()
        new_kid = apply_input(kid, Command(up=True))
        assert new_kid.curr_seq_id == int(Seq.STANDING_JUMP)

    def test_up_shift_draws_sword(self) -> None:
        kid = _kid_standing()
        new_kid = apply_input(kid, Command(up=True, shift=True))
        assert new_kid.curr_seq_id == int(Seq.DRAW_SWORD)
        assert new_kid.sword == SwordStatus.DRAWN

    def test_down_crouches(self) -> None:
        kid = _kid_standing()
        new_kid = apply_input(kid, Command(down=True))
        assert new_kid.curr_seq_id == int(Seq.CROUCH)

    def test_strike_only_with_sword(self) -> None:
        kid = _kid_standing()
        # Sin espada — el strike no funciona
        new_kid = apply_input(kid, Command(strike=True))
        assert new_kid.curr_seq_id != int(Seq.STRIKE)

        # Con espada — sí
        kid = replace(_kid_standing(), sword=SwordStatus.DRAWN)
        new_kid = apply_input(kid, Command(strike=True))
        assert new_kid.curr_seq_id == int(Seq.STRIKE)


class TestRunningTransitions:
    def _kid_running(self) -> Char:
        return replace(_kid_standing(), action=Action.RUN_JUMP)

    def test_up_triggers_run_jump(self) -> None:
        kid = self._kid_running()
        new_kid = apply_input(kid, Command(up=True))
        assert new_kid.curr_seq_id == int(Seq.RUN_JUMP)

    def test_no_dir_stops_run(self) -> None:
        kid = self._kid_running()
        new_kid = apply_input(kid, Command())
        assert new_kid.curr_seq_id == int(Seq.STOP_RUN)

    def test_continue_running_keeps_seq(self) -> None:
        kid = replace(self._kid_running(), curr_seq_id=int(Seq.RUN))
        new_kid = apply_input(kid, Command(right=True))
        # Sigue corriendo (no cambia)
        assert new_kid.curr_seq_id == int(Seq.RUN)


class TestHangTransitions:
    def _kid_hanging(self) -> Char:
        return replace(
            _kid_standing(),
            action=Action.HANG_STRAIGHT,
            curr_seq_id=int(Seq.JUMP_UP_GRAB_STRAIGHT),
        )

    def test_up_climbs(self) -> None:
        kid = self._kid_hanging()
        new_kid = apply_input(kid, Command(up=True))
        assert new_kid.curr_seq_id == int(Seq.CLIMB_UP)

    def test_down_releases(self) -> None:
        kid = self._kid_hanging()
        new_kid = apply_input(kid, Command(down=True))
        assert new_kid.curr_seq_id == int(Seq.RELEASE_LEDGE_LAND)

    def test_no_input_keeps_hanging(self) -> None:
        kid = self._kid_hanging()
        new_kid = apply_input(kid, Command())
        assert new_kid is kid


class TestDeadCharNoInput:
    def test_dead_kid_no_response(self) -> None:
        kid = replace(_kid_standing(), alive=5)
        new_kid = apply_input(kid, Command(right=True))
        assert new_kid is kid


class TestEngardeStance:
    def _drawn_kid(self) -> Char:
        return replace(_kid_standing(), sword=SwordStatus.DRAWN)

    def test_stand_with_sword_shift_enters_engarde(self) -> None:
        kid = self._drawn_kid()
        new_kid = apply_input(kid, Command(shift=True))
        assert new_kid.curr_seq_id == int(Seq.ENGARDE)

    def test_engarde_strike_starts_strike(self) -> None:
        kid = replace(self._drawn_kid(), curr_seq_id=int(Seq.ENGARDE))
        new_kid = apply_input(kid, Command(strike=True))
        assert new_kid.curr_seq_id == int(Seq.STRIKE)

    def test_engarde_up_blocks(self) -> None:
        kid = replace(self._drawn_kid(), curr_seq_id=int(Seq.ENGARDE))
        new_kid = apply_input(kid, Command(up=True))
        assert new_kid.curr_seq_id == int(Seq.BLOCK_STRIKE)

    def test_engarde_forward_advances(self) -> None:
        kid = replace(
            self._drawn_kid(),
            curr_seq_id=int(Seq.ENGARDE),
            direction=int(Direction.RIGHT),
        )
        new_kid = apply_input(kid, Command(right=True))
        assert new_kid.curr_seq_id == int(Seq.ADVANCE)

    def test_engarde_backward_retreats(self) -> None:
        kid = replace(
            self._drawn_kid(),
            curr_seq_id=int(Seq.ENGARDE),
            direction=int(Direction.RIGHT),
        )
        new_kid = apply_input(kid, Command(left=True))
        assert new_kid.curr_seq_id == int(Seq.RETREAT)

    def test_engarde_left_facing_swaps_directions(self) -> None:
        """Si el kid mira a la izquierda, LEFT es advance y RIGHT es retreat."""
        kid = replace(
            self._drawn_kid(),
            curr_seq_id=int(Seq.ENGARDE),
            direction=int(Direction.LEFT),
        )
        new_left = apply_input(kid, Command(left=True))
        assert new_left.curr_seq_id == int(Seq.ADVANCE)
        new_right = apply_input(kid, Command(right=True))
        assert new_right.curr_seq_id == int(Seq.RETREAT)

    def test_engarde_down_sheathes(self) -> None:
        kid = replace(self._drawn_kid(), curr_seq_id=int(Seq.ENGARDE))
        new_kid = apply_input(kid, Command(down=True))
        assert new_kid.curr_seq_id == int(Seq.PUT_SWORD_AWAY)
        assert new_kid.sword == SwordStatus.SHEATHED


class TestStandWithSwordExtras:
    def test_stand_down_with_sword_sheathes(self) -> None:
        kid = replace(_kid_standing(), sword=SwordStatus.DRAWN)
        new_kid = apply_input(kid, Command(down=True))
        assert new_kid.curr_seq_id == int(Seq.PUT_SWORD_AWAY)
        assert new_kid.sword == SwordStatus.SHEATHED

    def test_stand_shift_without_sword_does_nothing(self) -> None:
        kid = _kid_standing()  # SHEATHED
        new_kid = apply_input(kid, Command(shift=True))
        assert new_kid.curr_seq_id == int(Seq.STAND)
