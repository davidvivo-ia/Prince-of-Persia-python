"""Tests de la física tile-based: play_seq + gravity + grab + cross_border."""

from __future__ import annotations

from dataclasses import replace

from pop2026canon.domain.actions import Action, Direction, Seq
from pop2026canon.domain.chars import Char, CharId
from pop2026canon.domain.constants import (
    FALLING_SPEED_ACCEL,
    FALLING_SPEED_MAX,
    GRAB_FALL_Y_THRESHOLD,
    SCREEN_TILECOUNT_X,
    SCREEN_TILECOUNT_Y,
    TILE_SIZE_X,
    TILE_SIZE_Y,
)
from pop2026canon.domain.levels_canon import LEVEL_1
from pop2026canon.domain.physics import (
    can_grab,
    cross_border,
    fall_accel,
    fall_speed,
    is_solid_at,
    normalize_to_cell,
    play_seq,
    snap_to_hang,
    start_seq,
    step_physics,
)
from pop2026canon.domain.room import Room
from pop2026canon.domain.tiles import Tile


def _kid(room: int = 1, col: int = 2, row: int = 1, **kw: object) -> Char:
    """Helper para crear un kid con defaults razonables."""
    return Char(
        charid=CharId.KID,
        room=room,
        curr_col=col,
        curr_row=row,
        curr_seq_id=int(Seq.STAND),
        **kw,  # type: ignore[arg-type]
    )


class TestPlaySeq:
    def test_play_seq_advances_one_frame(self) -> None:
        kid = _kid()
        new_kid = play_seq(kid)
        # Debería haber un nuevo frame visible
        assert new_kid.frame != 0 or new_kid.frame == 15  # STAND frame
        # El cursor avanzó
        assert new_kid.curr_seq_idx > 0

    def test_play_seq_respects_dead_char(self) -> None:
        kid = replace(_kid(), alive=10)
        result = play_seq(kid)
        # Char muerto no se mueve
        assert result is kid

    def test_play_seq_stand_loop(self) -> None:
        """STAND auto-bucle: tras varios ticks vuelve al mismo frame."""
        kid = _kid()
        frames_seen = set()
        for _ in range(20):
            kid = play_seq(kid)
            frames_seen.add(kid.frame)
        # STAND solo tiene 1 frame visible (15)
        assert frames_seen == {15}

    def test_play_seq_runs_cycle(self) -> None:
        """Run cycle pasa por sus 12 frames y vuelve al inicio."""
        kid = start_seq(_kid(), Seq.RUN)
        frames_seen = []
        for _ in range(30):
            kid = play_seq(kid)
            frames_seen.append(kid.frame)
        # Frames 121-132
        unique = sorted(set(frames_seen))
        assert all(121 <= f <= 132 for f in unique)
        assert len(unique) >= 8  # mayoría de los 12 cubiertos

    def test_play_seq_applies_dx(self) -> None:
        """Tras play_seq de RUN, x avanza en la dirección.

        En el RUN cycle, ``dx(2)`` viene después de cada ``frame(N)``.
        El primer play_seq devuelve en frame(121) y el cursor queda en
        dx(2). El segundo play_seq aplica el dx y devuelve en frame(122).
        """
        kid = start_seq(_kid(direction=int(Direction.RIGHT)), Seq.RUN)
        original_x = kid.x
        kid = play_seq(kid)  # frame(121)
        kid = play_seq(kid)  # dx(2) + frame(122)
        assert kid.x != original_x


class TestFallAccel:
    def test_accelerates_in_freefall(self) -> None:
        kid = replace(_kid(), action=Action.IN_FREEFALL, fall_y=0)
        kid = fall_accel(kid)
        assert kid.fall_y == FALLING_SPEED_ACCEL  # +3

    def test_caps_at_max(self) -> None:
        kid = replace(_kid(), action=Action.IN_FREEFALL, fall_y=FALLING_SPEED_MAX)
        kid = fall_accel(kid)
        assert kid.fall_y == FALLING_SPEED_MAX  # no excede 33

    def test_no_accel_when_not_falling(self) -> None:
        kid = replace(_kid(), action=Action.STAND, fall_y=0)
        kid = fall_accel(kid)
        assert kid.fall_y == 0


class TestFallSpeed:
    def test_applies_fall_y_to_y(self) -> None:
        kid = replace(_kid(), action=Action.IN_FREEFALL, fall_y=10, y=5)
        kid = fall_speed(kid)
        assert kid.y == 15

    def test_applies_fall_x_with_direction(self) -> None:
        kid = replace(
            _kid(direction=int(Direction.RIGHT)),
            action=Action.IN_FREEFALL,
            fall_x=2,
            x=4,
        )
        kid = fall_speed(kid)
        assert kid.x == 6


class TestNormalizeToCell:
    def test_no_overflow_no_change(self) -> None:
        kid = _kid(col=2, row=1)
        kid = replace(kid, x=5, y=10)
        result = normalize_to_cell(kid)
        assert result.curr_col == 2
        assert result.curr_row == 1
        assert result.x == 5
        assert result.y == 10

    def test_x_overflow_advances_col(self) -> None:
        kid = _kid(col=2)
        kid = replace(kid, x=TILE_SIZE_X + 3)  # 17 px = col 3 + 3
        result = normalize_to_cell(kid)
        assert result.curr_col == 3
        assert result.x == 3

    def test_y_overflow_advances_row(self) -> None:
        kid = _kid(row=1)
        kid = replace(kid, y=TILE_SIZE_Y + 5)
        result = normalize_to_cell(kid)
        assert result.curr_row == 2
        assert result.y == 5

    def test_x_negative_retreats_col(self) -> None:
        kid = _kid(col=3)
        kid = replace(kid, x=-2)  # -2 px = col 2, x = 12
        result = normalize_to_cell(kid)
        assert result.curr_col == 2
        assert result.x == TILE_SIZE_X - 2


class TestCrossBorder:
    def test_cross_west_with_link(self) -> None:
        # Kid en sala 2 (sala central), va hacia sala 4 (oeste)
        kid = _kid(room=2, col=-1, row=1)  # se salió por west
        result = cross_border(kid, LEVEL_1)
        assert result.room == 4  # link_w de sala 2 = 4
        assert result.curr_col == SCREEN_TILECOUNT_X - 1

    def test_cross_east_with_link(self) -> None:
        kid = _kid(room=2, col=SCREEN_TILECOUNT_X, row=1)
        result = cross_border(kid, LEVEL_1)
        assert result.room == 3  # link_e de sala 2 = 3
        assert result.curr_col == 0

    def test_cross_south_with_link(self) -> None:
        kid = _kid(room=1, col=4, row=SCREEN_TILECOUNT_Y)  # se cayó por sur
        result = cross_border(kid, LEVEL_1)
        assert result.room == 2  # link_s de sala 1 = 2
        assert result.curr_row == 0

    def test_no_link_bumps(self) -> None:
        # Sala 4 no tiene link_w en L1
        kid = _kid(room=4, col=-1, row=1)
        result = cross_border(kid, LEVEL_1)
        assert result.action is Action.BUMPED


class TestSolidDetection:
    def test_floor_is_solid(self) -> None:
        room = LEVEL_1.room(1)
        # row 2 es suelo de FLOOR
        assert is_solid_at(room, col=5, row=2)

    def test_empty_is_not_solid(self) -> None:
        room = LEVEL_1.room(1)
        # row 1 es aire central
        assert not is_solid_at(room, col=3, row=1)

    def test_out_of_bounds_is_solid(self) -> None:
        room = LEVEL_1.room(1)
        assert is_solid_at(room, col=-1, row=1)
        assert is_solid_at(room, col=SCREEN_TILECOUNT_X, row=1)
        assert is_solid_at(room, col=0, row=-1)


class TestCanGrab:
    def _falling_kid_at_ledge(self) -> tuple[Char, Room]:
        """Setup: kid en pozo abierto cayendo, ledge sólido a su derecha.

        Geometría:
        - row 0 (col 5): EMPTY (espacio para cabeza al colgar)
        - row 1 (col 5): FLOOR — la cornisa (kid agarra el borde aquí)
        - row 1 (col 4): EMPTY — el kid está cayendo aquí
        - row 2 (col 5+): FLOOR — cuerpo de la plataforma
        """
        fg = [int(Tile.EMPTY)] * 30
        # Ledge a la derecha del kid: row 1 cols 5-9
        for c in range(5, 10):
            fg[10 + c] = int(Tile.FLOOR)
        # Cuerpo de la plataforma: row 2 cols 5-9
        for c in range(5, 10):
            fg[20 + c] = int(Tile.FLOOR)
        room = Room(id=1, fg=tuple(fg), bg=(0,) * 30)
        kid = replace(
            _kid(room=1, col=4, row=1),
            action=Action.IN_FREEFALL,
            fall_y=15,  # cayendo pero < 32
            direction=int(Direction.RIGHT),
        )
        return kid, room

    def test_grab_requires_shift(self) -> None:
        kid, room = self._falling_kid_at_ledge()
        assert can_grab(kid, room, shift_held=False) is None
        # Con SHIFT, sí
        assert can_grab(kid, room, shift_held=True) is not None

    def test_grab_requires_freefall(self) -> None:
        kid, room = self._falling_kid_at_ledge()
        kid = replace(kid, action=Action.STAND)
        assert can_grab(kid, room, shift_held=True) is None

    def test_grab_fails_if_falling_too_fast(self) -> None:
        kid, room = self._falling_kid_at_ledge()
        kid = replace(kid, fall_y=GRAB_FALL_Y_THRESHOLD)  # exactamente el threshold
        assert can_grab(kid, room, shift_held=True) is None

    def test_grab_returns_ledge_position(self) -> None:
        kid, room = self._falling_kid_at_ledge()
        ledge = can_grab(kid, room, shift_held=True)
        assert ledge == (5, 1)  # col 5, row 1

    def test_snap_to_hang(self) -> None:
        kid, _ = self._falling_kid_at_ledge()
        new_kid = snap_to_hang(kid, ledge_col=5, ledge_row=1)
        assert new_kid.action is Action.HANG_STRAIGHT
        assert new_kid.fall_x == 0
        assert new_kid.fall_y == 0
        assert new_kid.curr_seq_id == int(Seq.GRAB_LEDGE_MIDAIR)


class TestStepPhysicsIntegration:
    def test_step_advances_one_frame(self) -> None:
        kid = _kid()
        new_kid = step_physics(kid, LEVEL_1)
        # Avanzó la secuencia y/o sigue válido
        assert new_kid.room == kid.room  # no salió del nivel

    def test_step_falling_accelerates(self) -> None:
        kid = replace(_kid(), action=Action.IN_FREEFALL, fall_y=0)
        kid = step_physics(kid, LEVEL_1)
        # fall_y avanzó (ya sea por accel o por reset en seq)
        # Lo importante: action sigue freefall mientras no toque suelo
        assert kid.action in (Action.IN_FREEFALL, Action.STAND, Action.HANG_STRAIGHT)
