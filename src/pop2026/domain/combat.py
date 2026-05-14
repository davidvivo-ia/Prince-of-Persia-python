"""Resolución de combate cuerpo a cuerpo entre príncipe y guardias.

Versión 2 (Tier A, F-4): los golpes tienen **ventanas de impacto** y
**alcance** variable. La defensa también tiene ventana activa.

- ``STRIKE`` alcanza a distancia 1, conecta solo en los ticks 3-4 de 6.
- ``LUNGE`` alcanza a distancia 2, conecta solo en los ticks 4-6 de 9.
- ``PARRY`` absorbe el golpe durante los ticks 0-3 de 4.
- Daño doble si el golpe entra por la espalda.

Esto convierte el combate en una lectura de tempo: atacar fuera de
ventana es esfuerzo perdido y deja al atacante expuesto durante el
recovery.
"""

from __future__ import annotations

from dataclasses import dataclass

from pop2026.domain.actions import (
    Action,
    attack_reach,
    is_within_block,
    is_within_window,
)
from pop2026.domain.geometry import Facing
from pop2026.domain.guard import Guard, GuardMode
from pop2026.domain.physics_prince import PhysicsPrince as Prince


@dataclass(frozen=True, slots=True)
class CombatResult:
    """Resultado de la resolución de combate en un tick."""

    prince: Prince
    guards: tuple[Guard, ...]
    hits_dealt: int = 0
    hits_received: int = 0


def _same_row(p: Prince, g: Guard) -> bool:
    return g.alive and g.pos.row == p.pos.row


def _within_reach(p: Prince, g: Guard, reach: int) -> bool:
    return _same_row(p, g) and abs(g.pos.col - p.pos.col) <= reach


def _facing_toward(attacker_col: int, defender_col: int, defender_facing: Facing) -> bool:
    """¿El defensor mira hacia el atacante?"""
    expected = Facing.LEFT if defender_col > attacker_col else Facing.RIGHT
    return defender_facing is expected


def resolve(prince: Prince, guards: tuple[Guard, ...]) -> CombatResult:
    """Resuelve un tick de combate.

    Determinista dado el estado actual de las acciones (la aleatoriedad
    vive en la IA del guardia, no en este intercambio).
    """
    hits_dealt = 0
    hits_received = 0

    new_guards: list[Guard] = list(guards)
    new_prince = prince

    # Príncipe ataca (STRIKE o LUNGE)
    if (
        new_prince.action in (Action.STRIKE, Action.LUNGE)
        and new_prince.has_sword
        and is_within_window(new_prince.action, new_prince.ticks_in_action)
    ):
        reach = attack_reach(new_prince.action)
        for i, g in enumerate(new_guards):
            if not _within_reach(new_prince, g, reach):
                continue
            # ¿el guardia bloquea dentro de su ventana?
            if is_within_block(g.action, g.ticks_in_action):
                continue
            facing_to_prince = _facing_toward(new_prince.pos.col, g.pos.col, g.facing)
            dmg = 1 if facing_to_prince else 2
            new_guards[i] = g.with_damage(dmg)
            hits_dealt += 1
            break  # un golpe por tick

    # Guardias atacan
    for g in new_guards:
        if g.action not in (Action.STRIKE, Action.LUNGE) or not g.alive:
            continue
        if not is_within_window(g.action, g.ticks_in_action):
            continue
        reach = attack_reach(g.action)
        if not _within_reach(new_prince, g, reach):
            continue
        if is_within_block(new_prince.action, new_prince.ticks_in_action):
            continue
        facing_to_guard = _facing_toward(g.pos.col, new_prince.pos.col, new_prince.facing)
        dmg = 1 if facing_to_guard else 2
        new_prince = new_prince.with_damage(dmg)
        hits_received += 1
        break

    cleaned_guards = tuple(g for g in new_guards if g.alive or g.mode is GuardMode.DEAD)
    return CombatResult(
        prince=new_prince,
        guards=cleaned_guards,
        hits_dealt=hits_dealt,
        hits_received=hits_received,
    )
