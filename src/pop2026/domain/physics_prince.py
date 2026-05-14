"""Príncipe con física continua y "game-feel" de platformer 2026.

Reemplaza al FSM discreto antiguo (``domain/prince.py``). Implementa
las cinco mecánicas no negociables de un platformer 2D moderno:

1. **Coyote time** — saltar dentro de los ``COYOTE_TICKS`` posteriores
   a dejar una plataforma.
2. **Jump buffer** — un ``JUMP`` pulsado hasta ``JUMP_BUFFER_TICKS``
   antes de aterrizar se consume al tocar suelo.
3. **Variable jump height** — soltar ``JUMP`` mientras subes corta la
   velocidad vertical (``VAR_JUMP_CUT``).
4. **Air control** — input horizontal en el aire usa una aceleración
   menor (``AIR_ACCEL``) que en suelo (``GROUND_ACCEL``).
5. **Knockback** — al recibir un golpe se aplica un impulso opuesto y
   se ignora el input horizontal durante ``KNOCKBACK_TICKS``.

La integración (gravedad + colisión AABB por eje) vive en
:mod:`pop2026.domain.physics`. Este módulo se ocupa solo de mapear el
``InputFrame`` a aceleraciones/impulsos y de mantener el estado
simbólico (``action``) que el renderer y los SFX necesitan.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from pop2026.domain.actions import Action
from pop2026.domain.geometry import Facing, Position, PositionF, Velocity
from pop2026.domain.input import InputFrame, PlayerCommand
from pop2026.domain.level import Level, LevelState
from pop2026.domain.physics import (
    AIR_ACCEL,
    COYOTE_TICKS,
    GRAVITY,
    GROUND_ACCEL,
    JUMP_BUFFER_TICKS,
    JUMP_VEL,
    KNOCKBACK_TICKS,
    KNOCKBACK_VX,
    KNOCKBACK_VY,
    RUN_SPEED,
    VAR_JUMP_CUT,
    WALK_SPEED,
    BodyState,
    integrate,
    is_grounded,
)


@dataclass(frozen=True, slots=True)
class PhysicsPrince:
    """Príncipe en coordenadas continuas con game-feel completo."""

    body: BodyState
    facing: Facing = Facing.RIGHT
    action: Action = Action.STAND
    ticks_in_action: int = 0
    hp: int = 3
    max_hp: int = 3
    has_sword: bool = False

    # --- Estado de game-feel --------------------------------------------------

    coyote_left: int = 0
    """Ticks restantes de coyote time (saltar tras salir de plataforma)."""

    buffer_left: int = 0
    """Ticks restantes del jump buffer (JUMP pulsado en el aire)."""

    prev_jump_held: bool = False
    """``True`` si en el tick anterior la tecla de salto estaba pulsada."""

    knockback_left: int = 0
    """Ticks restantes de knockback. Mientras > 0, el input es ignorado."""

    last_impact_vy: float = 0.0
    """Velocidad vertical justo antes de aterrizar este tick (0 si no aterrizó)."""

    @property
    def alive(self) -> bool:
        """``True`` si sigue vivo."""
        return self.hp > 0 and self.action is not Action.DEAD

    @property
    def pos(self) -> Position:
        """Celda discreta derivada (para lógica de tiles y HUD)."""
        return self.body.pos.to_cell()

    # --- Helpers de mutación inmutable --------------------------------------

    def with_damage(self, amount: int, *, from_direction: int = 0) -> PhysicsPrince:
        """Aplica daño con knockback opcional.

        Args:
            amount: HP a restar.
            from_direction: signo de la dirección del atacante respecto
                al príncipe (-1 a la izquierda, +1 a la derecha). El
                knockback es opuesto a este signo.
        """
        new_hp = max(0, self.hp - amount)
        if new_hp == 0:
            return replace(
                self,
                hp=0,
                action=Action.DEAD,
                ticks_in_action=0,
                body=replace(self.body, vel=Velocity()),
                knockback_left=0,
            )
        # Empujón: opuesto a la dirección del atacante.
        # from_direction +1 = atacante a la derecha → vx negativa (a la izda).
        # from_direction -1 = atacante a la izquierda → vx positiva (a la dcha).
        direction = (
            from_direction if from_direction != 0 else (1 if self.facing is Facing.RIGHT else -1)
        )
        new_vel = Velocity(-direction * KNOCKBACK_VX, KNOCKBACK_VY)
        return replace(
            self,
            hp=new_hp,
            action=Action.HURT,
            ticks_in_action=0,
            body=replace(self.body, vel=new_vel),
            knockback_left=KNOCKBACK_TICKS,
        )

    def with_heal(self, amount: int) -> PhysicsPrince:
        """Cura hasta ``max_hp``."""
        return replace(self, hp=min(self.max_hp, self.hp + amount))

    def with_max_hp_bonus(self, bonus: int) -> PhysicsPrince:
        """Aumenta ``max_hp`` y rellena la vida al máximo."""
        new_max = self.max_hp + bonus
        return replace(self, max_hp=new_max, hp=new_max)


def initial(spawn: Position, *, hp: int = 3, max_hp: int = 3) -> PhysicsPrince:
    """Crea un príncipe físico centrado en la celda ``spawn``."""
    return PhysicsPrince(
        body=BodyState(
            pos=PositionF.from_cell(spawn, dx=0.5, dy=0.5),
            vel=Velocity(),
        ),
        hp=hp,
        max_hp=max_hp,
    )


# ---------------------------------------------------------------------------
# Step principal
# ---------------------------------------------------------------------------


def step(
    prince: PhysicsPrince,
    level: Level,
    state: LevelState,
    inp: InputFrame,
) -> PhysicsPrince:
    """Avanza un tick aplicando input + game-feel + integrador."""
    if prince.action is Action.DEAD:
        return prince

    cmd = inp.command
    grounded = is_grounded(prince.body, level, state)

    # --- Coyote y jump buffer -------------------------------------------------
    new_coyote = COYOTE_TICKS if grounded else max(0, prince.coyote_left - 1)
    # JUMP_BUFFER: si se pulsa JUMP, recarga el buffer.
    jump_pressed_this_tick = cmd is PlayerCommand.JUMP
    new_buffer = JUMP_BUFFER_TICKS if jump_pressed_this_tick else max(0, prince.buffer_left - 1)

    # Knockback: decrementa, bloquea input horizontal mientras > 0
    new_knockback = max(0, prince.knockback_left - 1)
    input_blocked = prince.knockback_left > 0

    # --- Input horizontal -----------------------------------------------------
    target_vx = 0.0
    new_facing = prince.facing
    if not input_blocked:
        if cmd is PlayerCommand.LEFT:
            target_vx = -(WALK_SPEED if inp.walk_modifier else RUN_SPEED)
            new_facing = Facing.LEFT
        elif cmd is PlayerCommand.RIGHT:
            target_vx = WALK_SPEED if inp.walk_modifier else RUN_SPEED
            new_facing = Facing.RIGHT

    accel = GROUND_ACCEL if grounded else AIR_ACCEL
    cur_vx = prince.body.vel.vx
    desired_vx = cur_vx + (target_vx - cur_vx) * accel * 10.0
    # Limitar a la velocidad máxima del modo (suelo o aire).
    max_vx = WALK_SPEED if inp.walk_modifier else RUN_SPEED
    desired_vx = max(-max_vx, min(max_vx, desired_vx))
    # Durante knockback la velocidad horizontal viene de el propio
    # impulso, no del input.
    if input_blocked:
        desired_vx = prince.body.vel.vx

    # --- Salto: coyote + buffer + variable jump -------------------------------
    new_vy = prince.body.vel.vy
    jump_consumed = False
    if (grounded or prince.coyote_left > 0) and new_buffer > 0 and not input_blocked:
        new_vy = JUMP_VEL
        jump_consumed = True
        new_coyote = 0
        new_buffer = 0

    # Variable jump height: soltar la tecla mientras subes corta el salto.
    if prince.prev_jump_held and not inp.jump_held and new_vy < 0 and not jump_consumed:
        new_vy = new_vy * VAR_JUMP_CUT

    # --- Decidir acción simbólica para renderer / SFX -------------------------
    new_action = _decide_action(
        prince=prince,
        cmd=cmd,
        grounded=grounded,
        desired_vx=desired_vx,
        new_vy=new_vy,
        input_blocked=input_blocked,
        walk_modifier=inp.walk_modifier,
    )

    # --- Integrador -----------------------------------------------------------
    pre_body = replace(prince.body, vel=Velocity(desired_vx, new_vy))
    result = integrate(pre_body, level, state, accel_x=0.0, accel_y=GRAVITY)

    # Si toca suelo y aún teníamos buffer pendiente, lo consumimos al
    # siguiente tick (mantener el buffer aquí; el `if` de arriba lo gastará).

    new_ticks = prince.ticks_in_action + 1 if new_action is prince.action else 0
    return PhysicsPrince(
        body=result.state,
        facing=new_facing,
        action=new_action,
        ticks_in_action=new_ticks,
        hp=prince.hp,
        max_hp=prince.max_hp,
        has_sword=prince.has_sword,
        coyote_left=new_coyote,
        buffer_left=new_buffer,
        prev_jump_held=inp.jump_held,
        knockback_left=new_knockback,
        last_impact_vy=result.impact_vy if result.hit_ground else 0.0,
    )


def _decide_action(
    *,
    prince: PhysicsPrince,
    cmd: PlayerCommand,
    grounded: bool,
    desired_vx: float,
    new_vy: float,
    input_blocked: bool,
    walk_modifier: bool,
) -> Action:
    """Mapea el estado a la acción simbólica que el renderer pinta."""
    if input_blocked:
        return Action.HURT
    if cmd is PlayerCommand.STRIKE and prince.has_sword:
        return Action.STRIKE
    if cmd is PlayerCommand.LUNGE and prince.has_sword:
        return Action.LUNGE
    if cmd is PlayerCommand.PARRY and prince.has_sword:
        return Action.PARRY
    if not grounded:
        return Action.FALL if new_vy > 0 else Action.JUMP_V
    if abs(desired_vx) > 0.01:
        return Action.WALK if walk_modifier else Action.RUN
    return Action.STAND


# ---------------------------------------------------------------------------
# Feature flag (mantenido por compatibilidad de tests; el motor ya es default)
# ---------------------------------------------------------------------------


def is_v2_enabled() -> bool:
    """Devuelve ``True`` si ``POP2026_PHYSICS_V2`` apunta a un valor truthy.

    Tras la promoción de física continua a default (R3) este flag deja
    de cambiar el comportamiento del juego; se mantiene la función para
    no romper el contrato de tests existentes.
    """
    import os

    val = os.environ.get("POP2026_PHYSICS_V2", "").strip().lower()
    return val in {"1", "true", "yes", "on"}
