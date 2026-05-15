"""Tests del sistema de combate canónico."""

from __future__ import annotations

from dataclasses import replace

from pop2026canon.domain.actions import Action, Direction, Seq, SwordStatus
from pop2026canon.domain.chars import Char, CharId
from pop2026canon.domain.combat import (
    can_strike,
    heal,
    heal_max,
    is_in_block_window,
    is_in_strike_window,
    resolve_combat,
    take_hp,
)


def _kid(**kw: object) -> Char:
    defaults: dict[str, object] = {
        "charid": CharId.KID,
        "room": 1,
        "curr_col": 3,
        "curr_row": 1,
        "hp_curr": 3,
        "hp_max": 3,
        "sword": SwordStatus.DRAWN,
        "direction": int(Direction.RIGHT),
    }
    defaults.update(kw)
    return Char(**defaults)  # type: ignore[arg-type]


def _guard(**kw: object) -> Char:
    defaults: dict[str, object] = {
        "charid": CharId.GUARD,
        "room": 1,
        "curr_col": 4,
        "curr_row": 1,
        "hp_curr": 4,
        "hp_max": 4,
        "sword": SwordStatus.DRAWN,
        "direction": int(Direction.LEFT),
    }
    defaults.update(kw)
    return Char(**defaults)  # type: ignore[arg-type]


class TestTakeHP:
    def test_simple_damage(self) -> None:
        kid = _kid(hp_curr=3)
        result = take_hp(kid, 1)
        assert result.char.hp_curr == 2
        assert result.killed is False
        assert result.char.action is Action.HURT

    def test_lethal_damage(self) -> None:
        kid = _kid(hp_curr=1)
        result = take_hp(kid, 1)
        assert result.killed is True
        assert result.char.hp_curr == 0
        assert result.char.alive >= 0
        assert result.char.curr_seq_id == int(Seq.STABBED_TO_DEATH)

    def test_skeleton_immortal(self) -> None:
        skel = _kid(charid=CharId.SKELETON, hp_curr=1)
        result = take_hp(skel, 1)
        assert result.killed is False
        assert result.char.hp_curr == 1  # recuperado a 1
        assert result.char.action is Action.HURT

    def test_dead_char_no_damage(self) -> None:
        kid = replace(_kid(), alive=5)
        result = take_hp(kid, 1)
        assert result.char is kid  # sin cambios

    def test_clamp_to_zero(self) -> None:
        kid = _kid(hp_curr=1)
        result = take_hp(kid, 5)
        assert result.char.hp_curr == 0


class TestHeal:
    def test_heal_below_max(self) -> None:
        kid = _kid(hp_curr=1, hp_max=3)
        new_kid = heal(kid, 1)
        assert new_kid.hp_curr == 2

    def test_heal_caps_at_max(self) -> None:
        kid = _kid(hp_curr=3, hp_max=3)
        new_kid = heal(kid, 5)
        assert new_kid.hp_curr == 3

    def test_heal_max_increases_cap(self) -> None:
        kid = _kid(hp_curr=2, hp_max=3)
        new_kid = heal_max(kid)
        assert new_kid.hp_max == 4
        assert new_kid.hp_curr == 4  # rellena


class TestWindows:
    def test_strike_window_165(self) -> None:
        kid = _kid(frame=165)
        assert is_in_strike_window(kid)

    def test_strike_window_167_inclusive(self) -> None:
        kid = _kid(frame=167)
        assert is_in_strike_window(kid)

    def test_not_in_strike_outside(self) -> None:
        kid = _kid(frame=164)
        assert not is_in_strike_window(kid)

    def test_block_window_161_164(self) -> None:
        kid = _kid(frame=161)
        assert is_in_block_window(kid)
        kid = _kid(frame=164)
        assert is_in_block_window(kid)

    def test_not_in_block_outside(self) -> None:
        kid = _kid(frame=160)
        assert not is_in_block_window(kid)


class TestCanStrike:
    def test_adjacent_right(self) -> None:
        kid = _kid(curr_col=3, direction=int(Direction.RIGHT))
        guard = _guard(curr_col=4)
        assert can_strike(kid, guard)

    def test_adjacent_left(self) -> None:
        kid = _kid(curr_col=3, direction=int(Direction.LEFT))
        guard = _guard(curr_col=2)
        assert can_strike(kid, guard)

    def test_too_far(self) -> None:
        kid = _kid(curr_col=3)
        guard = _guard(curr_col=6)
        assert not can_strike(kid, guard)

    def test_facing_wrong_way(self) -> None:
        kid = _kid(curr_col=3, direction=int(Direction.RIGHT))
        guard = _guard(curr_col=2)  # a la izquierda pero kid mira a la derecha
        assert not can_strike(kid, guard)

    def test_different_row(self) -> None:
        kid = _kid(curr_col=3, curr_row=1)
        guard = _guard(curr_col=4, curr_row=2)
        assert not can_strike(kid, guard)

    def test_different_room(self) -> None:
        kid = _kid(curr_col=3, room=1)
        guard = _guard(curr_col=4, room=2)
        assert not can_strike(kid, guard)


class TestResolveCombat:
    def test_kid_hits_unblocked_guard(self) -> None:
        kid = _kid(frame=166, direction=int(Direction.RIGHT))  # strike window
        guard = _guard(frame=150, direction=int(Direction.LEFT))  # NOT blocking
        result = resolve_combat(kid, guard)
        assert result.guard_hit is True
        assert result.guard.hp_curr == 3  # bajó de 4

    def test_kid_strike_blocked(self) -> None:
        kid = _kid(frame=166)
        guard = _guard(frame=162)  # block window
        result = resolve_combat(kid, guard)
        assert result.guard_hit is False
        assert result.guard.hp_curr == 4

    def test_simultaneous_strike(self) -> None:
        """Ambos en strike window — ambos se golpean."""
        kid = _kid(frame=166, direction=int(Direction.RIGHT))
        guard = _guard(frame=166, direction=int(Direction.LEFT))
        result = resolve_combat(kid, guard)
        assert result.kid_hit is True
        assert result.guard_hit is True

    def test_no_strike_no_damage(self) -> None:
        kid = _kid(frame=150)  # engarde, no strike
        guard = _guard(frame=150)
        result = resolve_combat(kid, guard)
        assert result.kid_hit is False
        assert result.guard_hit is False

    def test_lethal_strike(self) -> None:
        kid = _kid(frame=166, direction=int(Direction.RIGHT))
        guard = _guard(frame=150, direction=int(Direction.LEFT), hp_curr=1)
        result = resolve_combat(kid, guard)
        assert result.guard_hit is True
        assert result.guard.alive >= 0  # muerto


class TestHitResultImmutable:
    def test_dataclass_frozen(self) -> None:
        import pytest

        kid = _kid()
        result = take_hp(kid, 1)
        with pytest.raises(AttributeError):
            result.char = kid  # type: ignore[misc]
