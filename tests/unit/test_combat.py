"""Tests del sistema de combate."""

from __future__ import annotations

from dataclasses import replace

from pop2026.domain.actions import Action
from pop2026.domain.combat import resolve
from pop2026.domain.geometry import Facing, Position
from pop2026.domain.guard import Guard, GuardMode
from pop2026.domain.prince import Prince


def _p_with_sword() -> Prince:
    # ticks_in_action=3 cae dentro de la hit-window de STRIKE (3, 5).
    return Prince(
        pos=Position(1, 3),
        facing=Facing.RIGHT,
        has_sword=True,
        hp=3,
        max_hp=3,
        action=Action.STRIKE,
        ticks_in_action=3,
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
            ticks_in_action=3,  # dentro de la hit-window
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
            ticks_in_action=1,  # dentro de la block-window de PARRY (0, 4)
        )
        g = Guard(
            pos=Position(1, 4),
            facing=Facing.LEFT,
            action=Action.STRIKE,
            ticks_in_action=3,  # hit-window activa
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


class TestHitWindows:
    def test_strike_outside_window_does_no_damage(self) -> None:
        # ticks_in_action=0 está fuera de la hit-window (3, 5)
        p = Prince(
            pos=Position(1, 3),
            facing=Facing.RIGHT,
            has_sword=True,
            hp=3,
            max_hp=3,
            action=Action.STRIKE,
            ticks_in_action=0,
        )
        g = Guard(pos=Position(1, 4), facing=Facing.LEFT, action=Action.STAND, hp=3)
        r = resolve(p, (g,))
        assert r.hits_dealt == 0
        assert r.guards[0].hp == 3

    def test_strike_inside_window_damages(self) -> None:
        p = Prince(
            pos=Position(1, 3),
            facing=Facing.RIGHT,
            has_sword=True,
            hp=3,
            max_hp=3,
            action=Action.STRIKE,
            ticks_in_action=4,  # tick 4 está dentro de (3, 5)
        )
        g = Guard(pos=Position(1, 4), facing=Facing.LEFT, action=Action.STAND, hp=3)
        r = resolve(p, (g,))
        assert r.hits_dealt == 1

    def test_parry_outside_window_does_not_block(self) -> None:
        # ticks=4 está fuera de la block-window (0, 4)
        p = Prince(
            pos=Position(1, 3),
            facing=Facing.RIGHT,
            has_sword=True,
            hp=3,
            max_hp=3,
            action=Action.PARRY,
            ticks_in_action=4,
        )
        g = Guard(
            pos=Position(1, 4),
            facing=Facing.LEFT,
            action=Action.STRIKE,
            ticks_in_action=3,
            hp=3,
        )
        r = resolve(p, (g,))
        # PARRY fuera de ventana → recibe golpe
        assert r.hits_received >= 1


class TestLunge:
    def test_lunge_reaches_two_cells(self) -> None:
        # Príncipe con LUNGE en ticks 4-7, guardia a 2 celdas
        p = Prince(
            pos=Position(1, 3),
            facing=Facing.RIGHT,
            has_sword=True,
            hp=3,
            max_hp=3,
            action=Action.LUNGE,
            ticks_in_action=5,  # dentro de hit-window LUNGE (4, 7)
        )
        g = Guard(pos=Position(1, 5), facing=Facing.LEFT, action=Action.STAND, hp=3)
        r = resolve(p, (g,))
        assert r.hits_dealt == 1
        assert r.guards[0].hp < 3

    def test_lunge_outside_window_misses(self) -> None:
        p = Prince(
            pos=Position(1, 3),
            facing=Facing.RIGHT,
            has_sword=True,
            hp=3,
            max_hp=3,
            action=Action.LUNGE,
            ticks_in_action=1,  # fuera de (4, 7)
        )
        g = Guard(pos=Position(1, 5), facing=Facing.LEFT, action=Action.STAND, hp=3)
        r = resolve(p, (g,))
        assert r.hits_dealt == 0

    def test_strike_does_not_reach_two_cells(self) -> None:
        # STRIKE solo alcanza 1 celda, no debería conectar a distancia 2.
        p = Prince(
            pos=Position(1, 3),
            facing=Facing.RIGHT,
            has_sword=True,
            hp=3,
            max_hp=3,
            action=Action.STRIKE,
            ticks_in_action=3,
        )
        g = Guard(pos=Position(1, 5), facing=Facing.LEFT, action=Action.STAND, hp=3)
        r = resolve(p, (g,))
        assert r.hits_dealt == 0
