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
    """Parámetros canónicos por skill 0..11.

    Valores extraídos de las tablas de la versión DOS (verificadas en
    el desensamblado de SDLPoP, `seg002.c`): probabilidades sobre 255
    convertidas a [0, 1]. El skill 8 es el guard "pasivo" (no ataca ni
    bloquea — aparece en escenas scriptadas).
    """

    prob_strike: float
    """Probabilidad de iniciar un strike estando en rango."""

    prob_strike_after_block: float
    """Probabilidad de contraatacar tras bloquear (restrike)."""

    prob_block: float
    """Probabilidad de bloquear un strike entrante."""

    prob_imp_block: float
    """Probabilidad de bloquear cuando el guard está "impaired"."""

    advance_chance: float
    """Probabilidad de avanzar hacia el kid vs quedarse."""

    refractory: int
    """Ticks de pausa tras atacar/bloquear."""

    extra_hp: int
    """HP extra sobre el `TBL_GUARD_HP` del nivel."""


def _skill(s: int, r: int, b: int, i: int, a: int, refract: int, hp: int) -> GuardSkill:
    return GuardSkill(s / 255, r / 255, b / 255, i / 255, a / 255, refract, hp)


GUARD_SKILLS: tuple[GuardSkill, ...] = (
    #      strike restrike block impblock adv  refract hp
    _skill(61, 0, 0, 0, 255, 16, 0),
    _skill(100, 0, 150, 61, 200, 16, 0),
    _skill(61, 0, 150, 61, 200, 16, 0),
    _skill(61, 5, 200, 100, 200, 16, 0),
    _skill(61, 5, 200, 100, 255, 8, 1),
    _skill(40, 175, 255, 145, 255, 8, 0),
    _skill(100, 16, 200, 100, 200, 8, 0),
    _skill(220, 8, 250, 250, 0, 8, 0),
    _skill(0, 0, 0, 0, 0, 0, 0),  # 8: guard pasivo (scripted)
    _skill(48, 255, 255, 145, 255, 8, 0),
    _skill(32, 255, 255, 255, 100, 0, 0),
    _skill(48, 150, 255, 175, 100, 0, 0),
)
"""Tabla canon con `NUM_GUARD_SKILLS = 12` entradas (DOS v1.0)."""


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
