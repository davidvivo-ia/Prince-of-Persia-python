"""Guardias enemigos: IA por estados.

IA mínima pero suficiente:

- Si el príncipe está en la misma fila y a ≤8 celdas en la dirección del
  guardia → modo ALERTA: avanza hacia él.
- Si está adyacente → modo COMBATE: alterna ``STRIKE`` y ``PARRY`` según
  el RNG (modulado por la ``skill`` del guardia).
- En cualquier otro caso, patrulla (avanza 3 celdas, luego invierte).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import IntEnum

from pop2026.domain.actions import Action, duration_ticks
from pop2026.domain.geometry import Facing, Position
from pop2026.domain.level import Level, LevelState, effective_tile
from pop2026.domain.ports import Rng
from pop2026.domain.tiles import SOLID


class GuardMode(IntEnum):
    """Modo del guardia."""

    PATROL = 0
    ALERT = 1
    COMBAT = 2
    DEAD = 3


@dataclass(frozen=True, slots=True)
class Guard:
    """Estado de un guardia."""

    pos: Position
    facing: Facing = Facing.LEFT
    action: Action = Action.STAND
    ticks_in_action: int = 0
    hp: int = 3
    skill: int = 1
    mode: GuardMode = GuardMode.PATROL
    patrol_steps_left: int = 3

    @property
    def alive(self) -> bool:
        """``True`` si el guardia sigue vivo."""
        return self.hp > 0 and self.mode is not GuardMode.DEAD

    def with_damage(self, amount: int) -> Guard:
        """Aplica daño; si llega a 0 HP pasa a ``DEAD``."""
        new_hp = max(0, self.hp - amount)
        if new_hp == 0:
            return replace(
                self,
                hp=0,
                mode=GuardMode.DEAD,
                action=Action.DEAD,
                ticks_in_action=0,
            )
        return replace(self, hp=new_hp, action=Action.HURT, ticks_in_action=0)


def _is_solid(level: Level, state: LevelState, pos: Position) -> bool:
    return effective_tile(level, state, pos) in SOLID


def _spots_prince(guard: Guard, prince_pos: Position) -> bool:
    """¿Ve el guardia al príncipe en la misma fila a ≤8 celdas?"""
    if guard.pos.row != prince_pos.row:
        return False
    dx = prince_pos.col - guard.pos.col
    if dx == 0:
        return True
    return (dx > 0 and guard.facing is Facing.RIGHT and dx <= 8) or (
        dx < 0 and guard.facing is Facing.LEFT and -dx <= 8
    )


def step(
    guard: Guard,
    level: Level,
    state: LevelState,
    prince_pos: Position,
    rng: Rng,
) -> Guard:
    """Avanza el guardia un tick."""
    if not guard.alive:
        return guard

    new_ticks = guard.ticks_in_action + 1
    if new_ticks < duration_ticks(guard.action):
        return replace(guard, ticks_in_action=new_ticks)

    return _next_action(guard, level, state, prince_pos, rng)


def _next_action(
    guard: Guard,
    level: Level,
    state: LevelState,
    prince_pos: Position,
    rng: Rng,
) -> Guard:
    """Elige siguiente acción según modo."""
    # Re-evalúa modo
    adjacent = abs(prince_pos.col - guard.pos.col) <= 1 and prince_pos.row == guard.pos.row
    if adjacent:
        new_mode = GuardMode.COMBAT
        # Encara al príncipe
        new_facing = Facing.RIGHT if prince_pos.col > guard.pos.col else Facing.LEFT
        if guard.action is Action.HURT:
            return replace(
                guard, mode=new_mode, facing=new_facing, action=Action.STAND, ticks_in_action=0
            )
        # 50/50 entre strike y parry; skill 2 más agresivo
        attack_prob = 0.6 if guard.skill >= 2 else 0.45
        if rng.coin(attack_prob):
            return replace(
                guard, mode=new_mode, facing=new_facing, action=Action.STRIKE, ticks_in_action=0
            )
        return replace(
            guard, mode=new_mode, facing=new_facing, action=Action.PARRY, ticks_in_action=0
        )

    if _spots_prince(guard, prince_pos):
        new_mode = GuardMode.ALERT
        target = guard.pos.step(guard.facing)
        # No pisar la celda del príncipe ni atravesar muros.
        if _is_solid(level, state, target) or target == prince_pos:
            return replace(guard, mode=new_mode, action=Action.STAND, ticks_in_action=0)
        return replace(
            guard,
            mode=new_mode,
            pos=target,
            action=Action.WALK,
            ticks_in_action=0,
        )

    # PATROL: avanza N pasos, luego invierte
    if guard.patrol_steps_left <= 0:
        return replace(
            guard,
            mode=GuardMode.PATROL,
            facing=guard.facing.opposite(),
            patrol_steps_left=3,
            action=Action.STAND,
            ticks_in_action=0,
        )
    target = guard.pos.step(guard.facing)
    if _is_solid(level, state, target) or not _is_solid(level, state, target.shifted(drow=1)):
        # pared o precipicio: dar la vuelta
        return replace(
            guard,
            mode=GuardMode.PATROL,
            facing=guard.facing.opposite(),
            patrol_steps_left=3,
            action=Action.STAND,
            ticks_in_action=0,
        )
    return replace(
        guard,
        mode=GuardMode.PATROL,
        pos=target,
        patrol_steps_left=guard.patrol_steps_left - 1,
        action=Action.WALK,
        ticks_in_action=0,
    )


def picks_up_sword(_guard: Guard, _level: Level, _state: LevelState) -> bool:
    """Hook: si el guardia muere sobre el spawn de la espada, el jugador la coge.

    Implementado vacío en v1.0; la espada se entrega al matar al primer
    guardia. Ver :mod:`pop2026.domain.game`.
    """
    return False
