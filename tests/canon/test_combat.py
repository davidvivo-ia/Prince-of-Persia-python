"""Tests del combate a espada canon (seg002.c check_hurting / hurt_by_sword)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from pop2026canon.domain.actions import Action, Direction, Seq, SwordStatus
from pop2026canon.domain.chars import GUARD_SKILLS, Char, CharId
from pop2026canon.domain.combat import (
    MIN_HURT_RANGE_ARMED,
    MIN_HURT_RANGE_UNARMED,
    STRIKE_REACH,
    can_strike,
    char_opp_dist,
    check_hurting,
    heal,
    heal_max,
    hurt_by_sword,
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
        "x": 7,
        "hp_curr": 3,
        "hp_max": 3,
        "sword": SwordStatus.DRAWN,
        "direction": int(Direction.RIGHT),
        "frame": 158,
    }
    defaults.update(kw)
    return Char(**defaults)  # type: ignore[arg-type]


def _guard(**kw: object) -> Char:
    defaults: dict[str, object] = {
        "charid": CharId.GUARD,
        "room": 1,
        "curr_col": 4,
        "curr_row": 1,
        "x": 7,
        "hp_curr": 4,
        "hp_max": 4,
        "sword": SwordStatus.DRAWN,
        "direction": int(Direction.LEFT),
        "frame": 158,
        "skill": 1,
    }
    defaults.update(kw)
    return Char(**defaults)  # type: ignore[arg-type]


class TestDistance:
    def test_opponent_in_front(self) -> None:
        # kid en col 3 x 7 mirando a la derecha; guard en col 4 x 7 mirándole:
        # 14 px de separación + 13 por mirarse de frente.
        assert char_opp_dist(_kid(), _guard()) == 27

    def test_opponent_behind_is_negative(self) -> None:
        kid = _kid(direction=int(Direction.LEFT))
        assert char_opp_dist(kid, _guard()) < 0

    def test_other_room(self) -> None:
        assert char_opp_dist(_kid(), _guard(room=2)) == 999


class TestTakeHP:
    def test_simple_damage(self) -> None:
        result = take_hp(_kid(hp_curr=3), 1)
        assert result.char.hp_curr == 2
        assert result.killed is False

    def test_lethal_damage(self) -> None:
        result = take_hp(_kid(hp_curr=1), 1)
        assert result.killed is True
        assert result.char.hp_curr == 0
        assert result.char.alive >= 0
        assert result.char.curr_seq_id == int(Seq.STABBED_TO_DEATH)

    def test_skeleton_immortal(self) -> None:
        skel = _kid(charid=CharId.SKELETON, hp_curr=1)
        result = take_hp(skel, 1)
        assert result.killed is False
        assert result.char.hp_curr == 1

    def test_dead_char_no_damage(self) -> None:
        kid = replace(_kid(), alive=5)
        assert take_hp(kid, 1).char is kid

    def test_clamp_to_zero(self) -> None:
        assert take_hp(_kid(hp_curr=1), 5).char.hp_curr == 0


class TestHurtBySword:
    def test_armed_victim_loses_one_hp_and_staggers(self) -> None:
        victim = hurt_by_sword(_kid(hp_curr=3))
        assert victim.hp_curr == 2
        assert victim.curr_seq_id == int(Seq.HIT_BY_SWORD)
        assert victim.alive < 0

    def test_unarmed_victim_dies(self) -> None:
        """Canon: una estocada a un kid desarmado es mortal."""
        victim = hurt_by_sword(_kid(hp_curr=3, sword=SwordStatus.SHEATHED))
        assert victim.alive >= 0
        assert victim.curr_seq_id == int(Seq.STABBED_TO_DEATH)

    def test_guard_enters_refractory(self) -> None:
        guard = hurt_by_sword(_guard(hp_curr=4, skill=1))
        assert guard.refrac == GUARD_SKILLS[1].refractory

    def test_last_hp_kills(self) -> None:
        assert hurt_by_sword(_kid(hp_curr=1)).alive >= 0


class TestHeal:
    def test_heal_below_max(self) -> None:
        assert heal(_kid(hp_curr=1, hp_max=3), 1).hp_curr == 2

    def test_heal_caps_at_max(self) -> None:
        assert heal(_kid(hp_curr=3, hp_max=3), 5).hp_curr == 3

    def test_heal_max_increases_cap(self) -> None:
        new_kid = heal_max(_kid(hp_curr=2, hp_max=3))
        assert new_kid.hp_max == 4
        assert new_kid.hp_curr == 4


class TestWindows:
    def test_strike_window_is_153_154(self) -> None:
        assert is_in_strike_window(_kid(frame=153))
        assert is_in_strike_window(_kid(frame=154))
        assert not is_in_strike_window(_kid(frame=152))
        assert not is_in_strike_window(_kid(frame=155))

    def test_block_window_is_parry_frames(self) -> None:
        assert is_in_block_window(_kid(frame=150))
        assert is_in_block_window(_kid(frame=161))
        assert not is_in_block_window(_kid(frame=158))


class TestCanStrike:
    def test_in_reach(self) -> None:
        assert can_strike(_kid(), _guard())

    def test_too_far(self) -> None:
        assert not can_strike(_kid(), _guard(curr_col=6))

    def test_too_close_blade_passes(self) -> None:
        """Canon: a menos de 12 px (8 desarmado) la hoja no hiere — por
        ejemplo pegado a la espalda de un guard que mira al otro lado."""
        guard = _guard(curr_col=3, x=12, direction=int(Direction.RIGHT))
        d = char_opp_dist(_kid(), guard)
        assert d < MIN_HURT_RANGE_ARMED
        assert not can_strike(_kid(), guard)
        assert MIN_HURT_RANGE_UNARMED < MIN_HURT_RANGE_ARMED < STRIKE_REACH

    def test_facing_wrong_way(self) -> None:
        assert not can_strike(_kid(direction=int(Direction.LEFT)), _guard())

    def test_different_row(self) -> None:
        assert not can_strike(_kid(), _guard(curr_row=2))

    def test_different_room(self) -> None:
        assert not can_strike(_kid(), _guard(room=2))

    def test_sheathed_cannot_strike(self) -> None:
        assert not can_strike(_kid(sword=SwordStatus.SHEATHED), _guard())


class TestCheckHurting:
    def test_poke_hurts(self) -> None:
        res = check_hurting(_kid(frame=154), _guard(frame=158))
        assert res.hurt
        assert res.opp.hp_curr == 3

    def test_frame_153_does_not_hurt_yet(self) -> None:
        res = check_hurting(_kid(frame=153), _guard(frame=158))
        assert not res.hurt

    def test_parry_blocks_and_recoils_attacker(self) -> None:
        res = check_hurting(_kid(frame=154), _guard(frame=150))
        assert res.parried
        assert not res.hurt
        assert res.attacker.curr_seq_id == int(Seq.ATTACK_PARRIED)
        assert res.opp.frame == 161
        assert res.opp.hp_curr == 4

    def test_parried_guard_is_easier_to_hit_for_a_moment(self) -> None:
        """Canon: el guard cuya estocada ha sido parada queda con
        ``justblocked = 4`` — su siguiente bloqueo usa impblockprob."""
        res = check_hurting(_guard(frame=154), _kid(frame=150))
        assert res.parried
        assert res.attacker.justblocked == 4
        assert res.opp.frame == 161

    def test_parry_works_on_frame_153_too(self) -> None:
        res = check_hurting(_kid(frame=153), _guard(frame=161))
        assert res.parried

    def test_no_sword_no_hit(self) -> None:
        res = check_hurting(_kid(frame=154, sword=SwordStatus.SHEATHED), _guard())
        assert not res.hurt


class TestResolveCombat:
    def test_kid_hits_unblocked_guard(self) -> None:
        result = resolve_combat(_kid(frame=154), _guard(frame=158))
        assert result.guard_hit is True
        assert result.guard.hp_curr == 3

    def test_kid_strike_parried(self) -> None:
        result = resolve_combat(_kid(frame=154), _guard(frame=150))
        assert result.guard_hit is False
        assert result.kid_parried is True
        assert result.guard.hp_curr == 4

    def test_simultaneous_pokes_only_hurt_the_guard(self) -> None:
        """Ambos en el frame de impacto: canon check_sword_hurt anula el
        golpe recibido por el kid cuando el enemigo también ha sido
        alcanzado."""
        result = resolve_combat(_kid(frame=154), _guard(frame=154))
        assert result.guard_hit is True
        assert result.kid_hit is False
        assert result.kid.hp_curr == 3
        assert result.guard.hp_curr == 3

    def test_no_strike_no_damage(self) -> None:
        result = resolve_combat(_kid(frame=158), _guard(frame=158))
        assert result.kid_hit is False
        assert result.guard_hit is False

    def test_lethal_strike(self) -> None:
        result = resolve_combat(_kid(frame=154), _guard(frame=158, hp_curr=1))
        assert result.guard_hit is True
        assert result.guard.alive >= 0

    def test_unarmed_kid_dies_from_one_poke(self) -> None:
        kid = _kid(frame=15, sword=SwordStatus.SHEATHED, action=Action.STAND)
        result = resolve_combat(kid, _guard(frame=154))
        assert result.kid_hit
        assert result.kid.alive >= 0


class TestHitResultImmutable:
    def test_dataclass_frozen(self) -> None:
        kid = _kid()
        result = take_hp(kid, 1)
        with pytest.raises(AttributeError):
            result.char = kid  # type: ignore[misc]
