"""Resolución de combate cuerpo a cuerpo entre príncipe y guardias.

Versión 3 (R4) — combate continuo:

- **Alcance Euclídeo**: la distancia horizontal entre el príncipe
  (``body.pos.x``) y el centro de la celda del guardia
  (``guard.pos.col + 0.5``) se compara con ``attack_reach`` en celdas.
- **Misma fila**: tolerancia de ``ROW_TOLERANCE`` celdas entre el
  centro vertical del príncipe y el centro de la celda del guardia.
- **Cono frontal de parada**: el ``PARRY`` absorbe el golpe solo si la
  dirección del atacante coincide con el ``facing`` del defensor.
- **Hit windows**: los ticks dentro de la acción que conectan
  (definidos en :mod:`pop2026.domain.actions`).
- **Knockback dirigido**: al golpear al príncipe se aplica un empujón
  opuesto a la dirección del atacante usando
  :meth:`PhysicsPrince.with_damage` con ``from_direction``.

El guardia sigue siendo discreto: el cambio interesante es para el
príncipe, que ya se mueve en floats.
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
from pop2026.domain.physics_prince import PhysicsPrince

ROW_TOLERANCE: float = 0.6
"""Tolerancia vertical (celdas) para considerar a dos actores en la misma fila."""


@dataclass(frozen=True, slots=True)
class CombatResult:
    """Resultado de la resolución de combate en un tick."""

    prince: PhysicsPrince
    guards: tuple[Guard, ...]
    hits_dealt: int = 0
    hits_received: int = 0


def _guard_center_x(g: Guard) -> float:
    """Centro horizontal de la celda del guardia."""
    return g.pos.col + 0.5


def _guard_center_y(g: Guard) -> float:
    """Centro vertical de la celda del guardia."""
    return g.pos.row + 0.5


def _same_row(p: PhysicsPrince, g: Guard) -> bool:
    """¿El príncipe está en la misma fila lógica que el guardia?"""
    if not g.alive:
        return False
    return abs(p.body.pos.y - _guard_center_y(g)) <= ROW_TOLERANCE


def _distance_x(p: PhysicsPrince, g: Guard) -> float:
    """Distancia horizontal en celdas."""
    return abs(p.body.pos.x - _guard_center_x(g))


def _within_reach(p: PhysicsPrince, g: Guard, reach: float) -> bool:
    """¿Hay distancia suficiente para que el golpe conecte?"""
    return _same_row(p, g) and _distance_x(p, g) <= reach


def _attacker_dir(attacker_x: float, defender_x: float) -> int:
    """``+1`` si el atacante está a la derecha del defensor, ``-1`` si está a la izquierda."""
    return 1 if attacker_x > defender_x else -1


def _defender_faces_attacker(defender_facing: Facing, attacker_dir: int) -> bool:
    """``True`` si el defensor mira hacia donde viene el atacante (cono frontal)."""
    # facing.value: +1 = RIGHT, -1 = LEFT. Coincide con attacker_dir si mira hacia él.
    return int(defender_facing) == attacker_dir


def resolve(prince: PhysicsPrince, guards: tuple[Guard, ...]) -> CombatResult:
    """Resuelve un tick de combate en coordenadas continuas.

    Determinista dado el estado actual.
    """
    hits_dealt = 0
    hits_received = 0

    new_guards: list[Guard] = list(guards)
    new_prince = prince

    # --- Príncipe ataca (STRIKE o LUNGE) -------------------------------------
    if (
        new_prince.action in (Action.STRIKE, Action.LUNGE)
        and new_prince.has_sword
        and is_within_window(new_prince.action, new_prince.ticks_in_action)
    ):
        reach = float(attack_reach(new_prince.action))
        for i, g in enumerate(new_guards):
            if not _within_reach(new_prince, g, reach):
                continue
            # ¿el guardia bloquea dentro de su ventana y orientado hacia el príncipe?
            attacker_dir_for_guard = _attacker_dir(new_prince.body.pos.x, _guard_center_x(g))
            blocks = is_within_block(g.action, g.ticks_in_action) and _defender_faces_attacker(
                g.facing, attacker_dir_for_guard
            )
            if blocks:
                continue
            # Daño doble si entra por la espalda.
            from_front = _defender_faces_attacker(g.facing, attacker_dir_for_guard)
            dmg = 1 if from_front else 2
            new_guards[i] = g.with_damage(dmg)
            hits_dealt += 1
            break  # un golpe por tick

    # --- Guardias atacan ------------------------------------------------------
    for g in new_guards:
        if g.action not in (Action.STRIKE, Action.LUNGE) or not g.alive:
            continue
        if not is_within_window(g.action, g.ticks_in_action):
            continue
        reach = float(attack_reach(g.action))
        if not _within_reach(new_prince, g, reach):
            continue
        # ¿el príncipe bloquea con PARRY orientado hacia el guardia?
        guard_x = _guard_center_x(g)
        attacker_dir_for_prince = _attacker_dir(guard_x, new_prince.body.pos.x)
        prince_blocks = is_within_block(
            new_prince.action, new_prince.ticks_in_action
        ) and _defender_faces_attacker(new_prince.facing, attacker_dir_for_prince)
        if prince_blocks:
            continue
        from_front = _defender_faces_attacker(new_prince.facing, attacker_dir_for_prince)
        dmg = 1 if from_front else 2
        new_prince = new_prince.with_damage(dmg, from_direction=attacker_dir_for_prince)
        hits_received += 1
        break

    cleaned_guards = tuple(g for g in new_guards if g.alive or g.mode is GuardMode.DEAD)
    return CombatResult(
        prince=new_prince,
        guards=cleaned_guards,
        hits_dealt=hits_dealt,
        hits_received=hits_received,
    )
