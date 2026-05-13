"""Tests del sistema de combate."""

from __future__ import annotations

from dataclasses import replace

from pop2026.domain.actions import Action
from pop2026.domain.combat import resolve
from pop2026.domain.geometry import Facing, Position
from pop2026.domain.guard import Guard, GuardMode
from pop2026.domain.prince import Prince


def _p_with_sword() -> Prince:
    return Prince(
        pos=Position(1, 3),
        facing=Facing.RIGHT,
        has_sword=True,
        hp=3,
        max_hp=3,
        action=Action.STRIKE,
    )


def _g_adjacent_facing_left() -> Guard:
    return Guard(
        pos=Position(1, 4),
        facing=Facing.LEFT,
        action=Action.STAND,
        hp=2,
    )


class TestCombatResolve:
    def test_strike_hits_unguarded(self) -> None:
        p = _p_with_sword()
        g = _g_adjacent_facing_left()
        r = resolve(p, (g,))
        assert r.hits_dealt == 1
        assert r.guards[0].hp == 1

    def test_strike_is_blocked_by_parry(self) -> None:
        p = _p_with_sword()
        g = replace(_g_adjacent_facing_left(), action=Action.PARRY)
        r = resolve(p, (g,))
        assert r.hits_dealt == 0
        assert r.guards[0].hp == g.hp

    def test_back_attack_does_double_damage(self) -> None:
        p = _p_with_sword()
        # guardia mirando RIGHT (de espaldas al príncipe que está a su izda)
        g = Guard(pos=Position(1, 4), facing=Facing.RIGHT, action=Action.STAND, hp=3)
        r = resolve(p, (g,))
        # daño doble
        assert r.guards[0].hp == 1

    def test_guard_strike_hurts_prince(self) -> None:
        p = Prince(
            pos=Position(1, 3),
            facing=Facing.RIGHT,
            has_sword=True,
            hp=3,
            max_hp=3,
            action=Action.STAND,
        )
        g = Guard(
            pos=Position(1, 4),
            facing=Facing.LEFT,
            action=Action.STRIKE,
            hp=3,
        )
        r = resolve(p, (g,))
        assert r.hits_received >= 1
        assert r.prince.hp < p.hp

    def test_prince_parry_blocks_guard_strike(self) -> None:
        p = Prince(
            pos=Position(1, 3),
            facing=Facing.RIGHT,
            has_sword=True,
            hp=3,
            max_hp=3,
            action=Action.PARRY,
        )
        g = Guard(
            pos=Position(1, 4),
            facing=Facing.LEFT,
            action=Action.STRIKE,
            hp=3,
        )
        r = resolve(p, (g,))
        assert r.hits_received == 0
        assert r.prince.hp == p.hp

    def test_dead_guard_kept_in_list(self) -> None:
        # un guardia muerto se conserva (mode DEAD) para que el render lo dibuje
        p = _p_with_sword()
        g = Guard(
            pos=Position(1, 4),
            facing=Facing.LEFT,
            action=Action.STAND,
            hp=1,
        )
        r = resolve(p, (g,))
        assert len(r.guards) == 1
        assert r.guards[0].mode is GuardMode.DEAD
