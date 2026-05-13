"""Entidad Príncipe + FSM de transiciones.

La FSM resuelve, en cada tick:

1. Si la acción actual sigue en curso (``ticks_in_action < duration``):
   incrementa el contador y devuelve sin cambios estructurales.
2. Si la acción terminó: evalúa input + mundo y decide la siguiente
   acción. Aplica desplazamiento de celda asociado.

Modelo simplificado vs. el original:

- El movimiento es **por celda** completo al final de la acción. Esto
  preserva la sensación de "peso" porque hay 6-10 ticks de animación
  antes de que el sprite cambie de celda.
- ``HANG`` y ``CLIMB`` simplificados a una sola celda.
- ``CROUCH`` permite "descolgarse" sobre loose-floor sin romperlo.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from pop2026.domain.actions import (
    Action,
    duration_ticks,
)
from pop2026.domain.geometry import Facing, Position
from pop2026.domain.input import InputFrame, PlayerCommand
from pop2026.domain.level import Level, LevelState, effective_tile
from pop2026.domain.tiles import SOLID

MAX_FALL_SAFE: int = 2
"""Máxima caída en celdas sin recibir daño."""

FALL_LETHAL: int = 4
"""Caída a partir de la cual el príncipe muere al impactar."""


@dataclass(frozen=True, slots=True)
class Prince:
    """Estado del príncipe.

    Inmutable: cada step devuelve una nueva instancia. La gestión de
    pociones, gates y demás efectos secundarios sobre el nivel se hace
    desde ``game.py`` que orquesta esto.
    """

    pos: Position
    facing: Facing = Facing.RIGHT
    action: Action = Action.STAND
    ticks_in_action: int = 0
    hp: int = 3
    max_hp: int = 3
    has_sword: bool = False
    fall_distance: int = 0
    """Celdas caídas consecutivas; se usa para calcular daño al aterrizar."""

    @property
    def alive(self) -> bool:
        """``True`` si el príncipe sigue vivo."""
        return self.hp > 0 and self.action is not Action.DEAD

    def with_damage(self, amount: int) -> Prince:
        """Aplica daño, transiciona a ``HURT`` o ``DEAD``."""
        new_hp = max(0, self.hp - amount)
        if new_hp == 0:
            return replace(self, hp=0, action=Action.DEAD, ticks_in_action=0)
        return replace(self, hp=new_hp, action=Action.HURT, ticks_in_action=0)

    def with_heal(self, amount: int) -> Prince:
        """Cura hasta ``max_hp``."""
        return replace(self, hp=min(self.max_hp, self.hp + amount))

    def with_max_hp_bonus(self, bonus: int) -> Prince:
        """Aumenta ``max_hp`` y cura al máximo. Algunas pociones lo dan."""
        new_max = self.max_hp + bonus
        return replace(self, max_hp=new_max, hp=new_max)


def _is_solid(level: Level, state: LevelState, pos: Position) -> bool:
    return effective_tile(level, state, pos) in SOLID


def _can_stand_on_floor(level: Level, state: LevelState, pos: Position) -> bool:
    """¿Hay suelo justo bajo ``pos``?"""
    return _is_solid(level, state, pos.shifted(drow=1))


def _is_blocked_ahead(prince: Prince, level: Level, state: LevelState) -> bool:
    """¿Hay tile sólido en la celda adyacente en la dirección de mirada?"""
    target = prince.pos.step(prince.facing)
    return _is_solid(level, state, target)


def step(
    prince: Prince,
    level: Level,
    state: LevelState,
    inp: InputFrame,
) -> Prince:
    """Avanza el estado del príncipe **un tick**.

    No produce efectos secundarios sobre ``level``/``state``: las
    interacciones (pociones, placas, gates) las orquesta :mod:`game`.
    """
    if prince.action is Action.DEAD:
        return prince

    # 1. Tick interno
    new_ticks = prince.ticks_in_action + 1
    if new_ticks < duration_ticks(prince.action):
        return replace(prince, ticks_in_action=new_ticks)

    # 2. La acción ha terminado: aplicar efecto y elegir siguiente
    after_effect = _apply_action_effect(prince, level, state)
    return _next_action(after_effect, level, state, inp)


def _apply_action_effect(
    prince: Prince,
    level: Level,
    state: LevelState,
) -> Prince:
    """Aplica desplazamiento/daño asociado a una acción al completarse."""
    action = prince.action
    if action in (Action.WALK, Action.RUN):
        target = prince.pos.step(prince.facing)
        if not _is_solid(level, state, target):
            return replace(prince, pos=target, fall_distance=0)
        return prince

    if action is Action.JUMP_V:
        # Salto vertical en sitio: no desplaza, sirve para evitar golpes.
        return replace(prince, fall_distance=0)

    if action is Action.JUMP_R:
        # Salto direccional: hasta 2 celdas hacia adelante saltando un hueco.
        target2 = prince.pos.step(prince.facing, 2)
        if not _is_solid(level, state, target2):
            return replace(prince, pos=target2, fall_distance=0)
        target1 = prince.pos.step(prince.facing, 1)
        if not _is_solid(level, state, target1):
            return replace(prince, pos=target1, fall_distance=0)
        return prince

    if action is Action.FALL:
        below = prince.pos.shifted(drow=1)
        if _is_solid(level, state, below):
            # aterriza en suelo: aplica daño según fall_distance
            d = prince.fall_distance
            if d >= FALL_LETHAL:
                return replace(prince, hp=0, action=Action.DEAD, ticks_in_action=0)
            if d > MAX_FALL_SAFE:
                # 1 HP por celda extra
                dmg = d - MAX_FALL_SAFE
                return prince.with_damage(dmg)
            return replace(prince, fall_distance=0)
        # sigue cayendo
        return replace(prince, pos=below, fall_distance=prince.fall_distance + 1)

    if action is Action.CLIMB_UP:
        # Trepa: el príncipe se sube encima de la repisa adelante.
        # La repisa es la celda sólida en (r-1, c+1); queda parado en (r-2, c+1).
        target = prince.pos.step(prince.facing).shifted(drow=-2)
        return replace(prince, pos=target, fall_distance=0)

    if action is Action.CLIMB_DOWN:
        # Se descuelga: queda colgado y luego cae hasta el suelo de abajo.
        fwd_down = prince.pos.step(prince.facing).shifted(drow=1)
        return replace(prince, pos=fwd_down, fall_distance=0)

    return prince


def _next_action(
    prince: Prince,
    level: Level,
    state: LevelState,
    inp: InputFrame,
) -> Prince:
    """Decide la siguiente acción según input y entorno."""
    # gravedad: si no hay suelo bajo nosotros (y no estamos colgados),
    # caemos sin importar input
    if prince.action not in (
        Action.HANG,
        Action.CLIMB_UP,
        Action.CLIMB_DOWN,
    ) and not _can_stand_on_floor(level, state, prince.pos):
        return replace(prince, action=Action.FALL, ticks_in_action=0)

    cmd = inp.command

    if prince.action is Action.HURT:
        return replace(prince, action=Action.STAND, ticks_in_action=0)

    if cmd is PlayerCommand.STRIKE and prince.has_sword:
        return replace(prince, action=Action.STRIKE, ticks_in_action=0)
    if cmd is PlayerCommand.PARRY and prince.has_sword:
        return replace(prince, action=Action.PARRY, ticks_in_action=0)

    if cmd is PlayerCommand.JUMP:
        # Si venía corriendo o andando, salto direccional; si no, vertical.
        if prince.action in (Action.RUN, Action.WALK):
            return replace(prince, action=Action.JUMP_R, ticks_in_action=0)
        return replace(prince, action=Action.JUMP_V, ticks_in_action=0)

    if cmd is PlayerCommand.UP:
        # Trepa si hay una repisa accesible: bloque sólido en (r-1, c+1),
        # con hueco delante a la altura de los pies y aire encima de la cabeza.
        fwd = prince.pos.step(prince.facing)
        above_fwd = fwd.shifted(drow=-1)
        above = prince.pos.shifted(drow=-1)
        landing = fwd.shifted(drow=-2)
        if (
            _is_solid(level, state, above_fwd)
            and not _is_solid(level, state, fwd)
            and not _is_solid(level, state, above)
            and not _is_solid(level, state, landing)
        ):
            return replace(prince, action=Action.CLIMB_UP, ticks_in_action=0)

    if cmd is PlayerCommand.DOWN:
        # agacharse o descolgarse hacia abajo si hay hueco
        below = prince.pos.shifted(drow=1)
        if not _is_solid(level, state, below):
            return replace(prince, action=Action.CLIMB_DOWN, ticks_in_action=0)
        return replace(prince, action=Action.CROUCH, ticks_in_action=0)

    if cmd in (PlayerCommand.LEFT, PlayerCommand.RIGHT):
        new_facing = Facing.LEFT if cmd is PlayerCommand.LEFT else Facing.RIGHT
        prince = replace(prince, facing=new_facing)
        if _is_blocked_ahead(prince, level, state):
            return replace(prince, action=Action.STAND, ticks_in_action=0)
        nxt = Action.WALK if inp.walk_modifier else Action.RUN
        return replace(prince, action=nxt, ticks_in_action=0)

    return replace(prince, action=Action.STAND, ticks_in_action=0)
