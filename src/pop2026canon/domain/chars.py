"""Modelos de char (kid, shadow, guard, princess, vizier, skeleton, mouse).

Coincide 1-a-1 con `char_type` de `types.h` salvo por nombres en snake_case.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from pop2026canon.domain.actions import Action, Direction, SwordStatus


class CharId(IntEnum):
    """`enum charids` de types.h. Identifica el tipo de personaje."""

    KID = 0
    SHADOW = 1
    GUARD = 2
    GUARD_VARIANT = 3
    SKELETON = 4
    PRINCESS = 5
    VIZIER = 6
    MOUSE = 0x18


@dataclass(frozen=True, slots=True)
class Char:
    """Estado completo de un personaje en un tick.

    Coincide con `char_type` (types.h) en SDLPoP. Todos los offsets son
    sub-tile (0..13 horizontal, 0..62 vertical).
    """

    charid: CharId
    room: int
    """1..24, 0 = "no room"."""

    curr_col: int
    """0..9 dentro de la sala."""

    curr_row: int
    """0..2 dentro de la sala."""

    x: int = 0
    """Sub-tile px horizontal (0..13)."""

    y: int = 0
    """Sub-tile px vertical (0..62)."""

    direction: int = int(Direction.RIGHT)
    """+0 = right, -1 = left, 0x56 = none."""

    frame: int = 0
    """ID del frame visible actualmente."""

    curr_seq_id: int = 0
    """Sequence en curso (de `domain.actions.Seq`)."""

    curr_seq_idx: int = 0
    """Posición dentro de la secuencia."""

    action: Action = Action.STAND

    fall_x: int = 0
    """Momentum horizontal heredado de un salto/empuje."""

    fall_y: int = 0
    """Velocidad vertical de caída (acelera a +3/tick hasta 33)."""

    hp_curr: int = 3

    hp_max: int = 3

    sword: SwordStatus = SwordStatus.SHEATHED

    alive: int = -1
    """-1 vivo, 0 acaba de morir, +N frames muerto."""

    repeat: int = 0
    """Veces que se ha repetido el seq actual (para ciclos)."""

    skill: int = 0
    """Skill (0..11) de un guard. 0 para chars sin combate."""

    float_ticks: int = 0
    """Ticks restantes de caída-pluma (poción FLOAT). 0 = gravedad normal."""

    landed_fall_y: int = 0
    """``fall_y`` que traía el char al aterrizar ESTE tick (0 el resto).
    Lo consumen las trampas (spike mata según velocidad de impacto)."""

    fall_dist: int = 0
    """Distancia acumulada de la caída libre en curso (sub-tile px).
    Decide el daño al aterrizar (soft / med / mortal)."""


@dataclass(frozen=True, slots=True)
class GuardSkill:
    """Parámetros canónicos por skill 0..11. Valores ilustrativos —
    refinar tras dump exacto. Ver `docs/design/07-guard-ai.md`.
    """

    prob_block: float
    """0..1 — probabilidad de bloquear strike entrante."""

    prob_strike_after_block: float
    """Probabilidad de contraatacar tras un block."""

    refractory: int
    """Ticks de pausa tras moverse."""

    advance_chance: float
    """Probabilidad de avanzar vs idle estando en COMBAT."""


GUARD_SKILLS: tuple[GuardSkill, ...] = (
    GuardSkill(0.10, 0.20, 12, 0.10),
    GuardSkill(0.20, 0.30, 10, 0.20),
    GuardSkill(0.30, 0.40, 8, 0.30),
    GuardSkill(0.40, 0.50, 7, 0.40),
    GuardSkill(0.50, 0.55, 6, 0.50),
    GuardSkill(0.60, 0.60, 5, 0.55),
    GuardSkill(0.65, 0.70, 5, 0.60),
    GuardSkill(0.75, 0.75, 4, 0.65),
    GuardSkill(0.80, 0.80, 4, 0.70),
    GuardSkill(0.85, 0.85, 3, 0.75),
    GuardSkill(0.90, 0.90, 3, 0.80),
    GuardSkill(0.95, 0.95, 2, 0.90),
)
"""Tabla con `NUM_GUARD_SKILLS = 12` entradas."""


@dataclass(frozen=True, slots=True)
class GuardSpawn:
    """Spawn-point de un guard en una sala."""

    col: int
    row: int
    direction: int
    skill: int
    """0..11."""

    color: int = 0
    """Variante visual."""
