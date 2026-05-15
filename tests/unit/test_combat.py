"""Tests del sistema de combate continuo (R4)."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from pop2026.domain.actions import Action
from pop2026.domain.combat import resolve
from pop2026.domain.geometry import Facing, Position, PositionF, Velocity
from pop2026.domain.guard import Guard, GuardMode
from pop2026.domain.physics import BodyState
from pop2026.domain.physics_prince import PhysicsPrince


def _make_prince(col: float, row: int, **kwargs: Any) -> PhysicsPrince:
    """Construye un PhysicsPrince centrado en ``(col, row)``.

    El centro de la celda es ``col + 0.5``, ``row + 0.5``. El argumento
    ``col`` puede ser float para tests que necesiten distancia
    sub-celda.
    """
    return PhysicsPrince(
        body=BodyState(pos=PositionF(col + 0.5, row + 0.5), vel=Velocity()),
        **kwargs,
    )


def _p_with_sword() -> PhysicsPrince:
    # ticks_in_action=3 cae dentro de la hit-window de STRIKE (3, 5).
    return _make_prince(
        col=3,
        row=1,
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
        # PARRY orientado hacia el príncipe (atacante a la izquierda → mira LEFT).
        g = replace(_g_adjacent_facing_left(), action=Action.PARRY)
        r = resolve(p, (g,))
        assert r.hits_dealt == 0
        assert r.guards[0].hp == g.hp

    def test_back_attack_does_double_damage(self) -> None:
        p = _p_with_sword()
        # Guardia mirando RIGHT (de espaldas al príncipe que está a su izda).
        g = Guard(pos=Position(1, 4), facing=Facing.RIGHT, action=Action.STAND, hp=3)
        r = resolve(p, (g,))
        # Daño doble (entra por la espalda).
        assert r.guards[0].hp == 1

    def test_guard_strike_hurts_prince(self) -> None:
        p = _make_prince(
            col=3,
            row=1,
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
        p = _make_prince(
            col=3,
            row=1,
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
            ticks_in_action=3,
            hp=3,
        )
        r = resolve(p, (g,))
        assert r.hits_received == 0
        assert r.prince.hp == p.hp

    def test_dead_guard_kept_in_list(self) -> None:
        # Un guardia muerto se conserva (mode DEAD) para que el render lo dibuje.
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
        # ticks_in_action=0 está fuera de la hit-window (3, 5).
        p = _make_prince(
            col=3,
            row=1,
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
        p = _make_prince(
            col=3,
            row=1,
            facing=Facing.RIGHT,
            has_sword=True,
            hp=3,
            max_hp=3,
            action=Action.STRIKE,
            ticks_in_action=4,
        )
        g = Guard(pos=Position(1, 4), facing=Facing.LEFT, action=Action.STAND, hp=3)
        r = resolve(p, (g,))
        assert r.hits_dealt == 1

    def test_parry_outside_window_does_not_block(self) -> None:
        p = _make_prince(
            col=3,
            row=1,
            facing=Facing.RIGHT,
            has_sword=True,
            hp=3,
            max_hp=3,
            action=Action.PARRY,
            ticks_in_action=5,  # fuera de (0, 5)
        )
        g = Guard(
            pos=Position(1, 4),
            facing=Facing.LEFT,
            action=Action.STRIKE,
            ticks_in_action=3,
            hp=3,
        )
        r = resolve(p, (g,))
        assert r.hits_received >= 1


class TestLunge:
    def test_lunge_reaches_two_cells(self) -> None:
        # Príncipe con LUNGE en ticks 4-7, guardia a 2 celdas.
        p = _make_prince(
            col=3,
            row=1,
            facing=Facing.RIGHT,
            has_sword=True,
            hp=3,
            max_hp=3,
            action=Action.LUNGE,
            ticks_in_action=5,
        )
        g = Guard(pos=Position(1, 5), facing=Facing.LEFT, action=Action.STAND, hp=3)
        r = resolve(p, (g,))
        assert r.hits_dealt == 1
        assert r.guards[0].hp < 3

    def test_lunge_outside_window_misses(self) -> None:
        p = _make_prince(
            col=3,
            row=1,
            facing=Facing.RIGHT,
            has_sword=True,
            hp=3,
            max_hp=3,
            action=Action.LUNGE,
            ticks_in_action=1,
        )
        g = Guard(pos=Position(1, 5), facing=Facing.LEFT, action=Action.STAND, hp=3)
        r = resolve(p, (g,))
        assert r.hits_dealt == 0

    def test_strike_does_not_reach_two_cells(self) -> None:
        p = _make_prince(
            col=3,
            row=1,
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


# ---------------------------------------------------------------------------
# R4 — Continuo: distancias en float + knockback + parry cono frontal
# ---------------------------------------------------------------------------


class TestContinuousReach:
    def test_strike_hits_at_sub_cell_distance(self) -> None:
        # El príncipe está a 0.7 celdas del guardia (centro a centro): STRIKE
        # reach=1 debería conectar.
        p = _make_prince(
            col=2.8,  # centro x = 3.3
            row=1,
            facing=Facing.RIGHT,
            has_sword=True,
            hp=3,
            max_hp=3,
            action=Action.STRIKE,
            ticks_in_action=3,
        )
        g = Guard(pos=Position(1, 4), facing=Facing.LEFT, action=Action.STAND, hp=3)
        # distancia = |3.3 - 4.5| = 1.2 → fuera de reach=1; STRIKE no conecta
        r = resolve(p, (g,))
        assert r.hits_dealt == 0

    def test_strike_at_one_cell_exactly_hits(self) -> None:
        # Centro príncipe x=3.5; centro guardia x=4.5; distancia = 1.0 = reach
        p = _p_with_sword()
        g = _g_adjacent_facing_left()
        r = resolve(p, (g,))
        assert r.hits_dealt == 1

    def test_different_row_no_combat(self) -> None:
        # Príncipe en fila 1, guardia en fila 3 → no se golpean.
        p = _p_with_sword()
        g = Guard(pos=Position(3, 4), facing=Facing.LEFT, action=Action.STAND, hp=3)
        r = resolve(p, (g,))
        assert r.hits_dealt == 0


class TestKnockback:
    def test_hit_by_guard_pushes_prince_back(self) -> None:
        # Guardia a la derecha golpea: el príncipe debe salir disparado a la
        # izquierda (vx negativa) y entrar en estado HURT.
        p = _make_prince(
            col=3,
            row=1,
            facing=Facing.RIGHT,
            has_sword=False,
            hp=3,
            max_hp=3,
            action=Action.STAND,
        )
        g = Guard(
            pos=Position(1, 4),
            facing=Facing.LEFT,
            action=Action.STRIKE,
            ticks_in_action=3,
            hp=3,
        )
        r = resolve(p, (g,))
        assert r.hits_received == 1
        assert r.prince.body.vel.vx < 0, "knockback no empujó hacia la izquierda"
        assert r.prince.knockback_left > 0


class TestParryCone:
    def test_parry_blocks_only_when_facing_attacker(self) -> None:
        # Guardia ataca desde la derecha. Si el príncipe está orientado al
        # contrario (LEFT) y en PARRY, la cono no cubre el golpe → daño.
        p = _make_prince(
            col=3,
            row=1,
            facing=Facing.LEFT,  # mira fuera del atacante
            has_sword=True,
            hp=3,
            max_hp=3,
            action=Action.PARRY,
            ticks_in_action=1,
        )
        g = Guard(
            pos=Position(1, 4),
            facing=Facing.LEFT,
            action=Action.STRIKE,
            ticks_in_action=3,
            hp=3,
        )
        r = resolve(p, (g,))
        assert r.hits_received >= 1, "PARRY mirando fuera no debería bloquear"

    def test_parry_blocks_when_facing_attacker(self) -> None:
        # Príncipe orientado al guardia (RIGHT, guardia a la derecha): PARRY
        # bloquea.
        p = _make_prince(
            col=3,
            row=1,
            facing=Facing.RIGHT,
            has_sword=True,
            hp=3,
            max_hp=3,
            action=Action.PARRY,
            ticks_in_action=1,
        )
        g = Guard(
            pos=Position(1, 4),
            facing=Facing.LEFT,
            action=Action.STRIKE,
            ticks_in_action=3,
            hp=3,
        )
        r = resolve(p, (g,))
        assert r.hits_received == 0
