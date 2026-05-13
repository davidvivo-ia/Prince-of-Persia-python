"""F-1 fase 1: príncipe con coordenadas continuas (físicas).

Implementación **paralela** al FSM discreto en :mod:`pop2026.domain.prince`.
Se activa con la variable de entorno ``POP2026_PHYSICS_V2=1``. Mientras
no se promueva a default, el FSM discreto sigue siendo la ruta principal.

Diferencias clave con el FSM discreto:

- Posición y velocidad en :class:`PositionF` / :class:`Velocity`.
- Integrador con AABB por eje (ver :mod:`pop2026.domain.physics`).
- Acciones del jugador se traducen a *aceleraciones* y *impulsos*,
  no a desplazamientos por celda.
- La FSM lógica (qué acción está activa) sigue existiendo para que el
  renderer pinte la pose correcta.

Esta versión cubre el caso básico (correr, caer, saltar). Combate,
hang/climb se mapean al estado del FSM discreto y se delegan al
:mod:`prince` cuando hace falta. La migración completa queda para v2.0.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from pop2026.domain.actions import Action
from pop2026.domain.geometry import Facing, Position, PositionF, Velocity
from pop2026.domain.input import InputFrame, PlayerCommand
from pop2026.domain.level import Level, LevelState
from pop2026.domain.physics import (
    GRAVITY,
    JUMP_VEL,
    RUN_SPEED,
    WALK_SPEED,
    BodyState,
    integrate,
    is_grounded,
)


@dataclass(frozen=True, slots=True)
class PhysicsPrince:
    """Príncipe en coordenadas continuas.

    Mantiene la acción simbólica para preservar el contrato con el
    renderer y los SFX, pero el movimiento sale del integrador.
    """

    body: BodyState
    facing: Facing = Facing.RIGHT
    action: Action = Action.STAND
    ticks_in_action: int = 0
    hp: int = 3
    max_hp: int = 3
    has_sword: bool = False

    @property
    def alive(self) -> bool:
        """``True`` si sigue vivo."""
        return self.hp > 0 and self.action is not Action.DEAD

    @property
    def pos(self) -> Position:
        """Celda discreta derivada (para el HUD y la lógica de tiles)."""
        return self.body.pos.to_cell()


def initial(spawn: Position, *, hp: int = 3, max_hp: int = 3) -> PhysicsPrince:
    """Crea un príncipe físico en la celda de spawn (centrado en la celda)."""
    return PhysicsPrince(
        body=BodyState(
            pos=PositionF.from_cell(spawn, dx=0.5, dy=0.5),
            vel=Velocity(),
        ),
        hp=hp,
        max_hp=max_hp,
    )


def step(
    prince: PhysicsPrince,
    level: Level,
    state: LevelState,
    inp: InputFrame,
) -> PhysicsPrince:
    """Avanza el cuerpo un tick aplicando entrada y física.

    Mapea ``PlayerCommand`` a aceleraciones:

    - LEFT/RIGHT: aceleración horizontal hacia esa dirección.
    - JUMP: impulso vertical si está en suelo.
    - DOWN: agacharse (se modela bajando la AABB un poco).
    - STRIKE/PARRY/LUNGE: cambia ``action`` pero no afecta físicas
      directamente (estado lógico para combate y render).

    Args:
        prince: Estado actual.
        level: Mapa estático.
        state: Estado dinámico (gates abiertas, suelos caídos).
        inp: Comando del frame.

    Returns:
        Nuevo ``PhysicsPrince`` tras el tick.
    """
    if prince.action is Action.DEAD:
        return prince

    cmd = inp.command
    grounded = is_grounded(prince.body, level, state)

    # Aceleración horizontal a partir del input
    target_vx = 0.0
    new_facing = prince.facing
    if cmd is PlayerCommand.LEFT:
        target_vx = -(WALK_SPEED if inp.walk_modifier else RUN_SPEED)
        new_facing = Facing.LEFT
    elif cmd is PlayerCommand.RIGHT:
        target_vx = WALK_SPEED if inp.walk_modifier else RUN_SPEED
        new_facing = Facing.RIGHT

    # Lerp suave hacia la velocidad objetivo (inercia)
    smoothing = 0.3 if grounded else 0.08
    desired_vx = prince.body.vel.vx + (target_vx - prince.body.vel.vx) * smoothing

    # Salto: impulso si está en suelo y se pulsa JUMP
    new_vy = prince.body.vel.vy
    if cmd is PlayerCommand.JUMP and grounded:
        new_vy = JUMP_VEL

    # Decide la acción simbólica para el renderer
    new_action = prince.action
    if cmd is PlayerCommand.STRIKE and prince.has_sword:
        new_action = Action.STRIKE
    elif cmd is PlayerCommand.LUNGE and prince.has_sword:
        new_action = Action.LUNGE
    elif cmd is PlayerCommand.PARRY and prince.has_sword:
        new_action = Action.PARRY
    elif not grounded:
        new_action = Action.FALL if new_vy > 0 else Action.JUMP_V
    elif abs(desired_vx) > 0.01:
        new_action = Action.WALK if inp.walk_modifier else Action.RUN
    else:
        new_action = Action.STAND

    # Aplica el integrador con la aceleración ya pre-calculada
    pre_body = replace(prince.body, vel=Velocity(desired_vx, new_vy))
    result = integrate(pre_body, level, state, accel_x=0.0, accel_y=GRAVITY)

    new_ticks = prince.ticks_in_action + 1 if new_action is prince.action else 0
    return PhysicsPrince(
        body=result.state,
        facing=new_facing,
        action=new_action,
        ticks_in_action=new_ticks,
        hp=prince.hp,
        max_hp=prince.max_hp,
        has_sword=prince.has_sword,
    )


# ---------------------------------------------------------------------------
# Helper: ¿está activado el flag de física V2?
# ---------------------------------------------------------------------------


def is_v2_enabled() -> bool:
    """Devuelve ``True`` si ``POP2026_PHYSICS_V2`` apunta a un valor truthy."""
    import os

    val = os.environ.get("POP2026_PHYSICS_V2", "").strip().lower()
    return val in {"1", "true", "yes", "on"}
