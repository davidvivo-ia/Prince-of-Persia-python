"""Acciones canónicas (`enum actions`) y secuencias (`seqids`) del POP1.

Extraído de `src/types.h` de SDLPoP. Ver `docs/audit.md §4.2-4.3`.
"""

from __future__ import annotations

from enum import IntEnum


class Action(IntEnum):
    """9 acciones canónicas del kid (y otros chars)."""

    STAND = 0
    """Parado, listo para input."""

    RUN_JUMP = 1
    """Corriendo o saltando con carrerilla."""

    HANG_CLIMB = 2
    """Trepando una cornisa."""

    IN_MIDAIR = 3
    """Subiendo en un salto (aún no descendiendo)."""

    IN_FREEFALL = 4
    """Cayendo libremente — gravity aplica."""

    BUMPED = 5
    """Choque contra pared / guard. Pierde velocidad."""

    HANG_STRAIGHT = 6
    """Colgado de una cornisa, sin trepar todavía."""

    TURN = 7
    """Girando — ni avanza ni retrocede."""

    HURT = 99
    """Recibió un golpe — animación de daño."""


# ---------------------------------------------------------------------------
# Sequence IDs canónicos (extracto — completar en implementación)
# ---------------------------------------------------------------------------


class Seq(IntEnum):
    """Identificadores de secuencias `seqtbl.c`. Subconjunto crítico — el
    resto se añade conforme se implementan.
    """

    START_RUN = 1
    STAND = 2
    STANDING_JUMP = 3
    RUN_JUMP = 4
    TURN = 5
    FALL = 7
    JUMP_UP_GRAB_STRAIGHT = 8
    CLIMB_UP = 10
    RELEASE_LEDGE_LAND = 11
    STOP_RUN = 13
    GRAB_LEDGE_MIDAIR = 15
    JUMP_UP_GRAB = 16
    SOFT_LAND = 17
    FALL_AFTER_STANDING_JUMP = 18
    CRUSHED = 22
    STAND_UP_FROM_CROUCH = 49
    CROUCH = 50
    SPIKED = 51
    LOOSE_FLOOR_FELL_ON_KID = 52
    CHOMPED = 54
    DRAW_SWORD = 55
    DYING = 71
    STRIKE = 75
    DRINK = 78
    GUARD_FALL = 83
    RUN = 84
    STABBED_TO_DEATH = 85


# ---------------------------------------------------------------------------
# Frame IDs canónicos (subconjunto crítico)
# ---------------------------------------------------------------------------


class FrameID(IntEnum):
    """IDs de frame del kid. Los rangos completos están en
    `docs/design/02-frame-system.md §2`.
    """

    STAND = 15
    RUN_CYCLE_START = 121
    RUN_CYCLE_END = 132
    RUNJUMP_FRAME43 = 43
    """Frame canónico que dispara el shadow step de nivel 6."""

    HANG_FIRST = 81
    HANG_LAST = 99
    CLIMB_FIRST = 135
    CLIMB_LAST = 149
    SWORD_READY = 150
    SWORD_STRIKE = 165
    SPIKED = 177
    CHOMPED = 178
    DEATH_FIRST = 179
    DEATH_LAST = 185
    DRINK_FIRST = 191
    DRINK_LAST = 205
    SWORD_DRAW_FIRST = 207
    SWORD_DRAW_LAST = 210
    EXIT_STAIRS_FIRST = 217
    EXIT_STAIRS_LAST = 228
    FOUND_SWORD = 229
    SWORD_SHEATHE_FIRST = 230
    SWORD_SHEATHE_LAST = 240


# ---------------------------------------------------------------------------
# Directions
# ---------------------------------------------------------------------------


class Direction(IntEnum):
    """`enum directions` de types.h."""

    RIGHT = 0
    NONE = 0x56
    LEFT = -1


# ---------------------------------------------------------------------------
# Sword status
# ---------------------------------------------------------------------------


class SwordStatus(IntEnum):
    """`enum sword_status` de types.h."""

    SHEATHED = 0
    DRAWN = 2
