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
    LUNGE = 15
    """Estocada de mayor alcance (jefe). Dos celdas de distancia válida."""
    ADVANCE = 16
    """Micro-paso adelante con sable empuñado (medio tile)."""
    RETREAT = 17
    """Micro-paso atrás con sable empuñado (medio tile)."""


_DURATIONS: dict[Action, int] = {
    Action.STAND: 1,
    Action.WALK: 8,
    Action.RUN: 6,
    Action.CROUCH: 4,
    Action.JUMP_V: 10,
    Action.JUMP_R: 10,
    Action.CLIMB_UP: 12,
    Action.CLIMB_DOWN: 10,
    Action.HANG: 30,  # ~0.5 s sosteniéndose antes de evaluar siguiente acción
    Action.FALL: 3,
    Action.LAND: 4,
    Action.STRIKE: 6,
    Action.PARRY: 4,
    Action.HURT: 6,
    Action.DEAD: 1_000_000,  # absorbente
    Action.LUNGE: 9,  # mayor alcance, también más tiempo expuesto al final
    Action.ADVANCE: 8,
    Action.RETREAT: 8,
}


# ---------------------------------------------------------------------------
# Ventanas de impacto: ticks dentro de la acción en los que un golpe conecta.
# Rango ``(start, end)`` semi-abierto: ``start <= ticks_in_action < end``.
# Fuera de la ventana el atacante no causa daño aunque esté en rango.
# ---------------------------------------------------------------------------

HIT_WINDOWS: dict[Action, tuple[int, int]] = {
    Action.STRIKE: (3, 5),
    Action.LUNGE: (4, 7),
}
"""Ventana activa (inicio inclusivo, fin exclusivo) por acción ofensiva."""

BLOCK_WINDOWS: dict[Action, tuple[int, int]] = {
    Action.PARRY: (0, 4),
}
"""Ventana en la que la defensa absorbe el golpe del rival."""

ATTACK_REACH: dict[Action, int] = {
    Action.STRIKE: 1,
    Action.LUNGE: 2,
}
"""Distancia máxima en celdas a la que el ataque alcanza."""


def hit_window(action: Action) -> tuple[int, int] | None:
    """Ventana activa del ataque ``action``, o ``None`` si no es ataque."""
    return HIT_WINDOWS.get(action)


def block_window(action: Action) -> tuple[int, int] | None:
    """Ventana defensiva de ``action``, o ``None`` si no es defensa."""
    return BLOCK_WINDOWS.get(action)


def attack_reach(action: Action) -> int:
    """Alcance del ataque en celdas (0 si no es ataque)."""
    return ATTACK_REACH.get(action, 0)


def is_within_window(action: Action, ticks: int) -> bool:
    """``True`` si ``ticks`` cae dentro de la ventana activa del ataque."""
    window = HIT_WINDOWS.get(action)
    return window is not None and window[0] <= ticks < window[1]


def is_within_block(action: Action, ticks: int) -> bool:
    """``True`` si ``ticks`` cae dentro de la ventana defensiva."""
    window = BLOCK_WINDOWS.get(action)
    return window is not None and window[0] <= ticks < window[1]


def duration_ticks(action: Action) -> int:
    """Devuelve cuántos ticks dura una acción antes de evaluar transición."""
    return _DURATIONS[action]


COMBAT_ACTIONS: frozenset[Action] = frozenset(
    {Action.STRIKE, Action.PARRY, Action.HURT, Action.LUNGE, Action.ADVANCE, Action.RETREAT}
)
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
        Action.LUNGE,
        Action.ADVANCE,
        Action.RETREAT,
    }
)
"""Acciones que no aceptan re-comando hasta su tick final."""
