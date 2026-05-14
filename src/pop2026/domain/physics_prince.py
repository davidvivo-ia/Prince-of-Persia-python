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
from typing import TYPE_CHECKING

from pop2026.domain.actions import Action, duration_ticks
from pop2026.domain.geometry import Facing, Position, PositionF, Velocity
from pop2026.domain.input import InputFrame, PlayerCommand
from pop2026.domain.level import Level, LevelState
from pop2026.domain.physics import (
    ADVANCE_IMPULSE,
    ADVANCE_WINDOW,
    AIR_ACCEL,
    COMBAT_NEAR_CELLS,
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

if TYPE_CHECKING:
    from pop2026.domain.guard import Guard


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
    guards: tuple[Guard, ...] = (),
) -> PhysicsPrince:
    """Avanza un tick aplicando input + game-feel + integrador.

    El argumento opcional ``guards`` se usa para detectar combate cuerpo
    a cuerpo: si el príncipe tiene espada y hay un guardia vivo en la
    misma fila a ``COMBAT_NEAR_CELLS`` celdas, las teclas LEFT/RIGHT se
    interpretan como :data:`Action.ADVANCE` / :data:`Action.RETREAT` —
    micro-pasos de medio tile en lugar de carrera completa.
    """
    if prince.action is Action.DEAD:
        return prince

    cmd = inp.command
    grounded = is_grounded(prince.body, level, state)

    # --- Coyote y jump buffer -------------------------------------------------
    new_coyote = COYOTE_TICKS if grounded else max(0, prince.coyote_left - 1)
    jump_pressed_this_tick = inp.jump_pressed or cmd is PlayerCommand.JUMP
    new_buffer = JUMP_BUFFER_TICKS if jump_pressed_this_tick else max(0, prince.buffer_left - 1)

    new_knockback = max(0, prince.knockback_left - 1)
    input_blocked = prince.knockback_left > 0

    # --- Micro-pasos de combate (ADVANCE / RETREAT) ---------------------------
    guard_dir = _nearest_guard_dir(prince, guards)
    combat = _combat_micro_step(
        prince=prince,
        cmd=cmd,
        grounded=grounded,
        guard_dir=guard_dir,
        input_blocked=input_blocked,
    )

    combat_ticks: int | None = None
    if combat is not None:
        new_action, new_facing, desired_vx, combat_ticks = combat
        new_vy = prince.body.vel.vy
    else:
        # --- Input horizontal --------------------------------------------------
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
        max_vx = WALK_SPEED if inp.walk_modifier else RUN_SPEED
        desired_vx = max(-max_vx, min(max_vx, desired_vx))
        if input_blocked:
            desired_vx = prince.body.vel.vx

        # --- Salto: coyote + buffer + variable jump ----------------------------
        new_vy = prince.body.vel.vy
        jump_consumed = False
        if (grounded or prince.coyote_left > 0) and new_buffer > 0 and not input_blocked:
            new_vy = JUMP_VEL
            jump_consumed = True
            new_coyote = 0
            new_buffer = 0

        if prince.prev_jump_held and not inp.jump_held and new_vy < 0 and not jump_consumed:
            new_vy = new_vy * VAR_JUMP_CUT

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

    if combat_ticks is not None:
        new_ticks = combat_ticks
    else:
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


def _nearest_guard_dir(prince: PhysicsPrince, guards: tuple[Guard, ...]) -> int | None:
    """``+1`` / ``-1`` si hay un guardia vivo cercano en la misma fila."""
    best_dir: int | None = None
    best_dist = COMBAT_NEAR_CELLS
    for g in guards:
        if not g.alive:
            continue
        if abs(prince.body.pos.y - (g.pos.row + 0.5)) > 0.6:
            continue
        dx = (g.pos.col + 0.5) - prince.body.pos.x
        d = abs(dx)
        if d <= best_dist:
            best_dist = d
            best_dir = 1 if dx >= 0 else -1
    return best_dir


def _combat_micro_step(
    *,
    prince: PhysicsPrince,
    cmd: PlayerCommand,
    grounded: bool,
    guard_dir: int | None,
    input_blocked: bool,
) -> tuple[Action, Facing, float, int] | None:
    """Si procede, devuelve ``(action, facing, vx, ticks_within)``.

    Continúa una acción ya en curso (lock por duración) o arranca una
    nueva si hay sable + guardia adyacente + LEFT/RIGHT pulsado. El
    tick interno devuelto se asigna directamente a
    ``ticks_in_action`` para que el ciclo ADVANCE/RETREAT no acumule
    indefinidamente al re-disparar.
    """
    # STRIKE/PARRY/LUNGE rompen inmediatamente el micro-paso: el sable
    # tiene prioridad sobre el avance.
    if cmd in (PlayerCommand.STRIKE, PlayerCommand.PARRY, PlayerCommand.LUNGE):
        return None

    continuing = prince.action in (
        Action.ADVANCE,
        Action.RETREAT,
    ) and prince.ticks_in_action + 1 < duration_ticks(prince.action)
    can_start = (
        not continuing
        and not input_blocked
        and grounded
        and prince.has_sword
        and guard_dir is not None
        and cmd in (PlayerCommand.LEFT, PlayerCommand.RIGHT)
    )
    if not continuing and not can_start:
        return None

    if continuing:
        action = prince.action
        ticks_within = prince.ticks_in_action + 1
    else:
        assert guard_dir is not None
        cmd_dir = -1 if cmd is PlayerCommand.LEFT else 1
        action = Action.ADVANCE if cmd_dir == guard_dir else Action.RETREAT
        ticks_within = 0

    # Facing mira al guardia más cercano si lo hay; si no, conserva.
    if guard_dir is not None:
        facing = Facing.RIGHT if guard_dir > 0 else Facing.LEFT
    else:
        facing = prince.facing

    sign_to_guard = guard_dir if guard_dir is not None else int(facing)
    impulse_sign = sign_to_guard if action is Action.ADVANCE else -sign_to_guard
    in_window = ADVANCE_WINDOW[0] <= ticks_within < ADVANCE_WINDOW[1]
    desired_vx = float(impulse_sign) * ADVANCE_IMPULSE if in_window else 0.0
    return action, facing, desired_vx, ticks_within


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
    # Acción de combate completada: fuerza un tick de STAND para que la
    # siguiente STRIKE/PARRY/LUNGE reinicie ``ticks_in_action`` y vuelva
    # a entrar en su ventana de impacto.
    if prince.action in (
        Action.STRIKE,
        Action.PARRY,
        Action.LUNGE,
    ) and prince.ticks_in_action + 1 >= duration_ticks(prince.action):
        return Action.STAND
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
