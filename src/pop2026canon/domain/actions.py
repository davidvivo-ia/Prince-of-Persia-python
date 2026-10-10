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
    """Identificadores de secuencias `seqtbl.c`. Conjunto canónico
    operativo del motor.
    """

    START_RUN = 1
    STAND = 2
    STANDING_JUMP = 3
    RUN_JUMP = 4
    TURN = 5
    STANDING_JUMP_FORWARD = 6
    """Salto largo desde parado (ARRIBA+dirección): libra 2 celdas."""
    FALL = 7
    STEP = 9
    """Paso cuidadoso (SHIFT+dirección): una celda, nunca cae por el borde."""
    JUMP_UP_GRAB_STRAIGHT = 8
    CLIMB_UP = 10
    RELEASE_LEDGE_LAND = 11
    STOP_RUN = 13
    CLIMB_DOWN = 68
    """Descolgarse por el borde de espaldas al hueco (↓ de pie)."""
    GRAB_LEDGE_MIDAIR = 15
    JUMP_UP_GRAB = 16
    SOFT_LAND = 17
    FALL_AFTER_STANDING_JUMP = 18
    CRUSHED = 22
    RUNTURN = 25
    """Giro mientras corres (frenado + 180°)."""
    BUMP = 27
    """Choque frontal contra pared."""
    HARD_LAND = 30
    """Aterrizaje duro tras caída larga (>10 unidades de fall_y)."""
    MED_LAND = 33
    """Aterrizaje medio (fall_y entre 4 y 10)."""
    JUMP_HANG_MIDAIR = 38
    """Salto + agarrarse a cornisa estando en el aire (canon: seq 38)."""
    ENGARDE = 41
    """En guardia, sword drawn — listo para combate (canon ``ready``:
    frames 158, 170, 171)."""
    ADVANCE = 43
    """Paso adelante con espada empuñada (canon seq 86 ``advance``)."""
    RETREAT = 44
    """Paso atrás con espada empuñada (canon seq 57 ``retreat``)."""
    BLOCK_TO_STRIKE = 45
    """Parada seguida de estocada (canon seq 66 ``blocktostrike``)."""
    BLOCK_STRIKE = 46
    """Parada (canon seq 62 ``readyblock``: frames 169 → 150)."""
    GUARD_ADVANCE = 56
    """Avance rápido del guard (canon ``fastadvance``)."""
    GUARD_STRIKE = 58
    """Estocada del guard (canon ``strike``: 168 → 151..157)."""
    TURN_WITH_SWORD = 60
    """Giro en guardia tras cruzarse con el rival."""
    PARRY_AFTER_STRIKE = 61
    """Parada justo después de atacar (canon ``striketoblock``)."""
    ATTACK_PARRIED = 69
    """La estocada fue parada: retroceso (canon ``blockedstrike``)."""
    HIT_BY_SWORD = 74
    """Herido por la espada: tambaleo hacia atrás (canon ``stabbed``)."""
    GUARD_STAND_INACTIVE = 77
    """Guard en reposo, sin ver al kid (frame 166)."""
    KID_PUSHED_OFF_LEDGE = 81
    """Muerto a espada al borde: cae de espaldas (canon ``fightfall``)."""
    GUARD_PUSHED_OFF_LEDGE = 82
    """Guard muerto al borde: cae de espaldas (canon ``efightfall``)."""
    STAND_UP_FROM_CROUCH = 49
    CROUCH = 50
    SPIKED = 51
    LOOSE_FLOOR_FELL_ON_KID = 52
    CHOMPED = 54
    DRAW_SWORD = 55
    PUT_SWORD_AWAY = 92
    """Guardar espada (de DRAWN a SHEATHED)."""
    EXIT_LEVEL = 64
    """El kid entra por la puerta y sube las escaleras al siguiente nivel."""
    DYING = 71
    STRIKE = 75
    DRINK = 78
    GUARD_FALL = 83
    RUN = 84
    STABBED_TO_DEATH = 85
    BUMPED_FALL = 86
    """Bumped contra pared mientras está cerca de un borde — cae."""


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
