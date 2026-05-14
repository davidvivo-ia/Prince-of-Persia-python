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
from pop2026.domain.input import PlayerCommand
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
    """Estado de un guardia (o esqueleto si ``is_skeleton``)."""

    pos: Position
    facing: Facing = Facing.LEFT
    action: Action = Action.STAND
    ticks_in_action: int = 0
    hp: int = 3
    skill: int = 1
    mode: GuardMode = GuardMode.PATROL
    patrol_steps_left: int = 3
    is_skeleton: bool = False
    """Variante inmortal: nunca llega a HP 0; se recupera tras HURT."""

    is_mirror: bool = False
    """Clon-espejo: copia el input del príncipe con LEFT↔RIGHT invertidos."""

    @property
    def alive(self) -> bool:
        """``True`` si el guardia sigue vivo."""
        return self.hp > 0 and self.mode is not GuardMode.DEAD

    def with_damage(self, amount: int) -> Guard:
        """Aplica daño; si llega a 0 HP pasa a ``DEAD`` (salvo esqueleto)."""
        new_hp = max(0, self.hp - amount)
        if new_hp == 0:
            if self.is_skeleton:
                # Inmortal: queda en 1 HP recuperándose, no muere.
                return replace(self, hp=1, action=Action.HURT, ticks_in_action=0)
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
    prince_cmd: PlayerCommand = PlayerCommand.NONE,
) -> Guard:
    """Avanza el guardia un tick.

    Para guardias normales ``prince_cmd`` se ignora; sólo el clon-espejo
    (``is_mirror``) lo lee para reflejarlo (LEFT↔RIGHT).
    """
    if not guard.alive:
        return guard

    new_ticks = guard.ticks_in_action + 1
    if new_ticks < duration_ticks(guard.action):
        return replace(guard, ticks_in_action=new_ticks)

    if guard.is_mirror:
        return _mirror_next(guard, level, state, prince_cmd)
    return _next_action(guard, level, state, prince_pos, rng)


def _mirror_next(
    guard: Guard,
    level: Level,
    state: LevelState,
    prince_cmd: PlayerCommand,
) -> Guard:
    """Decide la acción del clon-espejo a partir del input del príncipe.

    Mapeo:

    - ``LEFT``  → mirror anda a la derecha.
    - ``RIGHT`` → mirror anda a la izquierda.
    - ``STRIKE`` / ``PARRY`` → mismo gesto.
    - resto → ``STAND``.
    """
    if prince_cmd is PlayerCommand.LEFT:
        target = guard.pos.step(Facing.RIGHT)
        if _is_solid(level, state, target):
            return replace(guard, facing=Facing.RIGHT, action=Action.STAND, ticks_in_action=0)
        return replace(
            guard,
            pos=target,
            facing=Facing.RIGHT,
            action=Action.WALK,
            ticks_in_action=0,
        )
    if prince_cmd is PlayerCommand.RIGHT:
        target = guard.pos.step(Facing.LEFT)
        if _is_solid(level, state, target):
            return replace(guard, facing=Facing.LEFT, action=Action.STAND, ticks_in_action=0)
        return replace(
            guard,
            pos=target,
            facing=Facing.LEFT,
            action=Action.WALK,
            ticks_in_action=0,
        )
    if prince_cmd is PlayerCommand.STRIKE:
        return replace(guard, action=Action.STRIKE, ticks_in_action=0)
    if prince_cmd is PlayerCommand.PARRY:
        return replace(guard, action=Action.PARRY, ticks_in_action=0)
    return replace(guard, action=Action.STAND, ticks_in_action=0)


def _next_action(
    guard: Guard,
    level: Level,
    state: LevelState,
    prince_pos: Position,
    rng: Rng,
) -> Guard:
    """Elige siguiente acción según modo.

    Decisión por distancia:

    - dist 0-1 (cuerpo a cuerpo): STRIKE o PARRY (skill 2 más agresivo).
    - dist 2 (rango LUNGE, solo skill ≥ 2): LUNGE ocasional.
    - dist 3-8 (visión): avanza si comparte fila; si no, patrulla.
    - dist > 8: patrulla.
    """
    same_row = prince_pos.row == guard.pos.row
    dist = abs(prince_pos.col - guard.pos.col) if same_row else 99
    new_facing = (
        guard.facing
        if not same_row
        else (Facing.RIGHT if prince_pos.col > guard.pos.col else Facing.LEFT)
    )

    # Distancia 0-1: cuerpo a cuerpo
    if dist <= 1 and same_row:
        new_mode = GuardMode.COMBAT
        if guard.action is Action.HURT:
            return replace(
                guard, mode=new_mode, facing=new_facing, action=Action.STAND, ticks_in_action=0
            )
        attack_prob = 0.65 if guard.skill >= 2 else 0.5
        action = Action.STRIKE if rng.coin(attack_prob) else Action.PARRY
        return replace(guard, mode=new_mode, facing=new_facing, action=action, ticks_in_action=0)

    # Distancia 2 (rango LUNGE): solo jefe (skill 2) lo usa, con probabilidad.
    if dist == 2 and same_row and guard.skill >= 2:
        if rng.coin(0.55):
            return replace(
                guard,
                mode=GuardMode.COMBAT,
                facing=new_facing,
                action=Action.LUNGE,
                ticks_in_action=0,
            )
        # Si no estoca, retrocede / avanza (queda en STAND y deja la IA al
        # siguiente tick decidir).
        return replace(
            guard,
            mode=GuardMode.COMBAT,
            facing=new_facing,
            action=Action.STAND,
            ticks_in_action=0,
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
