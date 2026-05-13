"""Acciones del príncipe (FSM) y sus duraciones en ticks.

Modelo simplificado de la FSM original. Cada acción tiene una duración
fija en ticks lógicos (60 Hz). Cuando ``ticks_in_action`` alcanza
``duration_ticks(action)``, la acción se considera "completada" y se
evalúa una transición.
"""

from __future__ import annotations

from enum import IntEnum


class Action(IntEnum):
    """Acciones posibles del príncipe o guardia.

    ``STAND``  : parado, listo para cualquier comando.
    ``WALK``   : un paso preciso (con shift).
    ``RUN``    : un paso de carrera, más largo.
    ``CROUCH`` : agachado (puede pasar por gates bajas, no recibe HP).
    ``JUMP_V`` : salto vertical (sin avance horizontal).
    ``JUMP_R`` : salto de carrera (con avance horizontal).
    ``CLIMB_UP``  : trepa una celda hacia arriba.
    ``CLIMB_DOWN``: descuelga una celda hacia abajo.
    ``HANG``   : colgado de un borde.
    ``FALL``   : cayendo.
    ``LAND``   : aterrizando (frame de absorción, congela input).
    ``STRIKE`` : ataque con sable.
    ``PARRY``  : defensa con sable.
    ``HURT``   : recibió un golpe.
    ``DEAD``   : muerto.
    """

    STAND = 0
    WALK = 1
    RUN = 2
    CROUCH = 3
    JUMP_V = 4
    JUMP_R = 5
    CLIMB_UP = 6
    CLIMB_DOWN = 7
    HANG = 8
    FALL = 9
    LAND = 10
    STRIKE = 11
    PARRY = 12
    HURT = 13
    DEAD = 14


_DURATIONS: dict[Action, int] = {
    Action.STAND: 1,
    Action.WALK: 8,
    Action.RUN: 6,
    Action.CROUCH: 4,
    Action.JUMP_V: 10,
    Action.JUMP_R: 10,
    Action.CLIMB_UP: 12,
    Action.CLIMB_DOWN: 10,
    Action.HANG: 2,
    Action.FALL: 3,
    Action.LAND: 4,
    Action.STRIKE: 6,
    Action.PARRY: 4,
    Action.HURT: 6,
    Action.DEAD: 1_000_000,  # absorbente
}


def duration_ticks(action: Action) -> int:
    """Devuelve cuántos ticks dura una acción antes de evaluar transición."""
    return _DURATIONS[action]


COMBAT_ACTIONS: frozenset[Action] = frozenset({Action.STRIKE, Action.PARRY, Action.HURT})
"""Acciones en las que el actor está empuñando el sable."""

LOCKED_ACTIONS: frozenset[Action] = frozenset(
    {
        Action.JUMP_V,
        Action.JUMP_R,
        Action.CLIMB_UP,
        Action.CLIMB_DOWN,
        Action.FALL,
        Action.LAND,
        Action.STRIKE,
        Action.PARRY,
        Action.HURT,
        Action.HANG,
        Action.DEAD,
    }
)
"""Acciones que no aceptan re-comando hasta su tick final."""
