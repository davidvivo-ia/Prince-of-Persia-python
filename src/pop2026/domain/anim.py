"""Animación sub-celda: offsets fraccionarios para suavizar el renderer.

El dominio sigue siendo discreto (celdas), pero durante los ticks
intermedios de una acción el renderer puede interpolar la posición
visual del actor para producir un movimiento continuo.

Convención:

- ``dx`` es desplazamiento en celdas hacia adelante respecto a la
  posición lógica (``+`` hacia la derecha en facing RIGHT y similar para
  LEFT cuando se aplica ``facing.value``).
- ``dy`` es desplazamiento vertical en celdas (positivo hacia abajo).

Las acciones que no implican desplazamiento devuelven ``(0.0, 0.0)``.
"""

from __future__ import annotations

import math
from typing import Protocol

from pop2026.domain.actions import Action, duration_ticks


class _AnimActor(Protocol):
    """Mínimo necesario para calcular el offset (sirve para Prince y Guard)."""

    action: Action
    ticks_in_action: int

    @property
    def facing_value(self) -> int:  # pragma: no cover
        ...


def offset_for(*, action: Action, ticks: int, facing_value: int) -> tuple[float, float]:
    """Devuelve ``(dx, dy)`` en fracciones de celda para el frame actual.

    Args:
        action: Acción en curso.
        ticks: Ticks transcurridos dentro de la acción.
        facing_value: ``+1`` si mira a la derecha, ``-1`` a la izquierda.

    Returns:
        Tupla ``(dx, dy)`` que el renderer suma a la posición lógica
        para obtener la posición visual.
    """
    dur = duration_ticks(action)
    if dur <= 1:
        return 0.0, 0.0
    t = min(1.0, ticks / dur)

    if action in (Action.WALK, Action.RUN):
        return t * facing_value, 0.0

    if action is Action.JUMP_V:
        # Parábola: sube y baja en sitio.
        return 0.0, -0.9 * 4.0 * t * (1.0 - t)

    if action is Action.JUMP_R:
        # 2 celdas hacia adelante con arco vertical.
        return 2.0 * t * facing_value, -1.1 * 4.0 * t * (1.0 - t)

    if action is Action.FALL:
        # Acelera ligeramente al final (caída).
        return 0.0, t * t

    if action is Action.CLIMB_UP:
        # Pasos suaves: agarre, impulso, asentarse. Suavizado por seno.
        eased = 0.5 - 0.5 * math.cos(math.pi * t)
        return eased * facing_value, -2.0 * eased

    if action is Action.CLIMB_DOWN:
        eased = 0.5 - 0.5 * math.cos(math.pi * t)
        return eased * facing_value, 1.0 * eased

    if action is Action.HURT:
        # Pequeño retroceso visible.
        return -0.15 * facing_value * (1.0 - t), 0.0

    if action is Action.STRIKE:
        # Lunge adelante en el primer tercio, recoge.
        peak = math.sin(min(1.0, t * 1.5) * math.pi)
        return 0.2 * facing_value * peak, 0.0

    if action is Action.PARRY:
        return 0.05 * facing_value * math.sin(t * math.pi), 0.0

    return 0.0, 0.0
