"""Resolución de combate cuerpo a cuerpo entre príncipe y guardias.

Reglas v1.0 (simplificadas pero fieles al espíritu):

- Un golpe ``STRIKE`` impacta si el defensor **no** está en ``PARRY`` y
  está adyacente y mirando hacia el atacante.
- Si el defensor está en ``PARRY``, el golpe se anula y ambos retroceden
  un tick.
- Daño base: 1 HP. El jefe (``skill==2``) hace 1 HP igualmente pero su
  ``coin`` de strike es más alto (ver :mod:`guard`).
- Si el atacante golpea por la espalda, daño doble.
"""

from __future__ import annotations

from dataclasses import dataclass

from pop2026.domain.actions import Action
from pop2026.domain.geometry import Facing
from pop2026.domain.guard import Guard, GuardMode
from pop2026.domain.prince import Prince


@dataclass(frozen=True, slots=True)
class CombatResult:
    """Resultado de la resolución de combate en un tick."""

    prince: Prince
    guards: tuple[Guard, ...]
    hits_dealt: int = 0
    hits_received: int = 0


def _adjacent(prince: Prince, guard: Guard) -> bool:
    return (
        guard.alive and guard.pos.row == prince.pos.row and abs(guard.pos.col - prince.pos.col) <= 1
    )


def resolve(prince: Prince, guards: tuple[Guard, ...]) -> CombatResult:
    """Resuelve un tick de combate.

    No usa RNG: es determinista dadas las acciones actuales. La
    aleatoriedad vive en la IA del guardia (qué acción eligió), no en
    el resultado del intercambio.
    """
    hits_dealt = 0
    hits_received = 0

    new_guards: list[Guard] = list(guards)
    new_prince = prince

    # Príncipe ataca
    if new_prince.action is Action.STRIKE and new_prince.has_sword:
        for i, g in enumerate(new_guards):
            if not _adjacent(new_prince, g):
                continue
            # ¿el guardia para?
            if g.action is Action.PARRY:
                continue
            # daño doble si por la espalda
            facing_to_prince = (
                Facing.LEFT if new_prince.pos.col < g.pos.col else Facing.RIGHT
            ) == g.facing
            dmg = 1 if facing_to_prince else 2
            new_guards[i] = g.with_damage(dmg)
            hits_dealt += 1
            break  # un golpe por tick

    # Guardias atacan
    for i, g in enumerate(new_guards):
        if g.action is not Action.STRIKE or not g.alive:
            continue
        if not _adjacent(new_prince, g):
            continue
        if new_prince.action is Action.PARRY:
            continue
        facing_to_guard = (
            Facing.LEFT if g.pos.col < new_prince.pos.col else Facing.RIGHT
        ) == new_prince.facing
        dmg = 1 if facing_to_guard else 2
        new_prince = new_prince.with_damage(dmg)
        hits_received += 1
        _ = i  # silencia loop var
        break

    # Limpia guardias muertos manteniendo orden
    cleaned_guards = tuple(g for g in new_guards if g.alive or g.mode is GuardMode.DEAD)
    return CombatResult(
        prince=new_prince,
        guards=cleaned_guards,
        hits_dealt=hits_dealt,
        hits_received=hits_received,
    )
