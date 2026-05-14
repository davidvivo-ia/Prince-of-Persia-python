"""Física continua: integrador y colisión AABB contra grid de tiles.

Este módulo es **cimiento** para la migración futura del príncipe a
coordenadas continuas (ver `plan.md` F-1). Por ahora vive en paralelo
con el FSM por celdas; no se inyecta automáticamente en `game.advance`.

Convenciones:

- Las coordenadas están en celdas (1.0 == 1 tile). El renderer las
  multiplica por ``tile_w``/``tile_h`` al pintar.
- ``dt`` está en ticks lógicos. Un tick = 1/60 s nominal.
- ``gravity`` y ``run_speed`` son constantes documentadas como módulo,
  no como parámetros mágicos.

Diseño:

- Las funciones son **puras**: reciben estado y devuelven estado nuevo.
  No mutan, no leen tiempo del reloj.
- La colisión es AABB vs grid: para cada eje (X, Y) por separado,
  se barre la AABB sobre las celdas que toca y se ajusta a la primera
  pared. Esto previene "tunneling" a velocidades razonables (<1 celda
  por tick).
"""

from __future__ import annotations

from dataclasses import dataclass

from pop2026.domain.geometry import AABB, PositionF, Velocity
from pop2026.domain.level import Level, LevelState, effective_tile
from pop2026.domain.tiles import SOLID

# ---------------------------------------------------------------------------
# Constantes — tuneadas para "feel" estilo POP. Documentadas para revisión.
# ---------------------------------------------------------------------------

GRAVITY: float = 0.06
"""Aceleración descendente por tick (celdas/tick²). ~ 21 cells/s²."""

WALK_SPEED: float = 0.10
"""Velocidad de andar (celdas/tick). ~ 6 cells/s."""

RUN_SPEED: float = 0.22
"""Velocidad de correr (celdas/tick). ~ 13 cells/s."""

JUMP_VEL: float = -0.42
"""Velocidad inicial de salto vertical (celdas/tick, negativa = arriba)."""

MAX_FALL_VEL: float = 0.45
"""Velocidad de caída máxima (celdas/tick) — terminal velocity."""

PRINCE_W: float = 0.55
"""Anchura de la AABB del príncipe en celdas."""

PRINCE_H: float = 0.90
"""Altura de la AABB del príncipe en celdas."""

# --- Constantes de game-feel (R1) ----------------------------------------

COYOTE_TICKS: int = 6
"""Ticks tras dejar el suelo en los que aún se admite salto."""

JUMP_BUFFER_TICKS: int = 6
"""Ticks antes de aterrizar en los que un JUMP queda buffereado."""

VAR_JUMP_CUT: float = 0.45
"""Si se suelta JUMP mientras ``vy < 0``, se multiplica por este valor."""

GROUND_ACCEL: float = 0.10
"""Aceleración horizontal pedida al input estando en suelo (lerp objetivo)."""

AIR_ACCEL: float = 0.025
"""Aceleración horizontal en el aire — menor que en suelo (air control)."""

KNOCKBACK_VX: float = 0.30
"""Magnitud horizontal del empujón al recibir un golpe."""

KNOCKBACK_VY: float = -0.18
"""Componente vertical del knockback (un poco hacia arriba)."""

KNOCKBACK_TICKS: int = 10
"""Ticks durante los que el input horizontal queda bloqueado tras hit."""

SPIKE_LETHAL_VY: float = 0.30
"""Velocidad vertical mínima al pisar pinchos para que sean letales."""


@dataclass(frozen=True, slots=True)
class BodyState:
    """Estado físico continuo (sustituirá a Position en Prince para F-1)."""

    pos: PositionF
    vel: Velocity

    def with_pos(self, pos: PositionF) -> BodyState:
        """Inmutable: devuelve nuevo estado con otra posición."""
        return BodyState(pos=pos, vel=self.vel)

    def with_vel(self, vel: Velocity) -> BodyState:
        """Inmutable: devuelve nuevo estado con otra velocidad."""
        return BodyState(pos=self.pos, vel=vel)


# ---------------------------------------------------------------------------
# Helpers de consulta del grid
# ---------------------------------------------------------------------------


def _solid_at(level: Level, state: LevelState, col: int, row: int) -> bool:
    """Devuelve True si la celda ``(row, col)`` es sólida en este tick."""
    from pop2026.domain.geometry import Position

    return effective_tile(level, state, Position(row, col)) in SOLID


def _aabb_touches_solid(level: Level, state: LevelState, box: AABB) -> bool:
    """¿La AABB toca alguna celda sólida del grid?"""
    col0 = int(box.x)
    col1 = int(box.x2 - 1e-9)
    row0 = int(box.y)
    row1 = int(box.y2 - 1e-9)
    for r in range(row0, row1 + 1):
        for c in range(col0, col1 + 1):
            if _solid_at(level, state, c, r):
                return True
    return False


# ---------------------------------------------------------------------------
# Integrador con resolución de colisiones por eje
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class StepResult:
    """Resultado de un paso de física."""

    state: BodyState
    hit_wall: bool = False
    hit_ground: bool = False
    hit_ceiling: bool = False
    impact_vy: float = 0.0
    """Velocidad vertical instantes antes de colisionar (0 si no hubo)."""


def integrate(
    body: BodyState,
    level: Level,
    state: LevelState,
    *,
    accel_x: float = 0.0,
    accel_y: float = GRAVITY,
    half_w: float = PRINCE_W / 2.0,
    half_h: float = PRINCE_H / 2.0,
) -> StepResult:
    """Avanza el cuerpo un tick aplicando aceleración y colisión por eje.

    Args:
        body: Estado actual del cuerpo.
        level: Mapa estático.
        state: Mapa dinámico (gates abiertas, etc.).
        accel_x: Aceleración horizontal (celdas/tick²).
        accel_y: Aceleración vertical (gravity por defecto).
        half_w: Mitad de la anchura de la AABB.
        half_h: Mitad de la altura.

    Returns:
        ``StepResult`` con el nuevo estado y banderas de contacto.
    """
    # Actualiza velocidad.
    new_vx = body.vel.vx + accel_x
    new_vy = max(-1.0, min(MAX_FALL_VEL, body.vel.vy + accel_y))

    # Eje X primero.
    candidate_x = body.pos.x + new_vx
    test_pos = PositionF(candidate_x, body.pos.y)
    box = AABB(test_pos.x - half_w, test_pos.y - half_h, half_w * 2, half_h * 2)
    hit_wall = False
    if _aabb_touches_solid(level, state, box):
        hit_wall = True
        candidate_x = body.pos.x
        new_vx = 0.0

    # Eje Y.
    candidate_y = body.pos.y + new_vy
    test_pos = PositionF(candidate_x, candidate_y)
    box = AABB(test_pos.x - half_w, test_pos.y - half_h, half_w * 2, half_h * 2)
    hit_ground = False
    hit_ceiling = False
    impact_vy = 0.0
    if _aabb_touches_solid(level, state, box):
        impact_vy = new_vy  # capturado antes del reset
        if new_vy > 0:
            hit_ground = True
        elif new_vy < 0:
            hit_ceiling = True
        candidate_y = body.pos.y
        new_vy = 0.0

    return StepResult(
        state=BodyState(pos=PositionF(candidate_x, candidate_y), vel=Velocity(new_vx, new_vy)),
        hit_wall=hit_wall,
        hit_ground=hit_ground,
        hit_ceiling=hit_ceiling,
        impact_vy=impact_vy,
    )


def is_grounded(
    body: BodyState,
    level: Level,
    state: LevelState,
    *,
    half_w: float = PRINCE_W / 2.0,
    half_h: float = PRINCE_H / 2.0,
    probe: float = 0.15,
) -> bool:
    """Comprueba si hay suelo justo debajo del cuerpo (sonda corta)."""
    box = AABB(
        body.pos.x - half_w + 0.05,
        body.pos.y + half_h,
        half_w * 2 - 0.10,
        probe,
    )
    return _aabb_touches_solid(level, state, box)
