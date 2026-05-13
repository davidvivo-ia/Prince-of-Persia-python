"""Value-objects geométricos: posición y dirección.

Coordenadas en celdas (row, col). Origen arriba-izquierda. ``row`` crece
hacia abajo, ``col`` hacia la derecha (estándar de TUI/pygame).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class Facing(IntEnum):
    """Dirección de mirada/movimiento horizontal."""

    LEFT = -1
    RIGHT = 1

    def opposite(self) -> Facing:
        """Devuelve la dirección opuesta."""
        return Facing.RIGHT if self is Facing.LEFT else Facing.LEFT


@dataclass(frozen=True, slots=True)
class Position:
    """Posición en celda discreta del mapa."""

    row: int
    col: int

    def shifted(self, drow: int = 0, dcol: int = 0) -> Position:
        """Devuelve una nueva posición desplazada."""
        return Position(self.row + drow, self.col + dcol)

    def step(self, facing: Facing, n: int = 1) -> Position:
        """Avanza ``n`` celdas en la dirección dada."""
        return Position(self.row, self.col + int(facing) * n)


@dataclass(frozen=True, slots=True)
class PositionF:
    """Posición continua en coordenadas de celda (sub-celda permitida).

    ``x``/``y`` son fracciones de celda; ``int(x)`` da la columna lógica
    y ``int(y)`` la fila. Las celdas son cuadradas conceptualmente: el
    renderer multiplica por ``tile_w``/``tile_h`` antes de pintar.
    """

    x: float
    y: float

    @classmethod
    def from_cell(cls, pos: Position, *, dx: float = 0.5, dy: float = 0.5) -> PositionF:
        """Coordenadas continuas centradas en la celda ``pos`` por defecto."""
        return cls(pos.col + dx, pos.row + dy)

    def to_cell(self) -> Position:
        """Truncado a celda discreta (suelo)."""
        return Position(int(self.y), int(self.x))

    def translated(self, dx: float = 0.0, dy: float = 0.0) -> PositionF:
        """Devuelve una posición desplazada."""
        return PositionF(self.x + dx, self.y + dy)


@dataclass(frozen=True, slots=True)
class Velocity:
    """Velocidad en celdas-por-tick (no en píxeles)."""

    vx: float = 0.0
    vy: float = 0.0

    def scaled(self, factor: float) -> Velocity:
        """Multiplica componente a componente."""
        return Velocity(self.vx * factor, self.vy * factor)

    def with_added(self, dvx: float = 0.0, dvy: float = 0.0) -> Velocity:
        """Devuelve una nueva velocidad con incrementos sumados."""
        return Velocity(self.vx + dvx, self.vy + dvy)


@dataclass(frozen=True, slots=True)
class AABB:
    """Caja de colisión axis-aligned. Coordenadas en celdas (no píxeles).

    Origen ``(x, y)`` es la esquina superior-izquierda; ``w``/``h`` son
    anchura/altura en fracciones de celda.
    """

    x: float
    y: float
    w: float
    h: float

    @property
    def x2(self) -> float:
        """Borde derecho (exclusivo)."""
        return self.x + self.w

    @property
    def y2(self) -> float:
        """Borde inferior (exclusivo)."""
        return self.y + self.h

    def centered(self, pos: PositionF, *, w: float, h: float) -> AABB:
        """Devuelve una AABB con dimensiones dadas centrada en ``pos``."""
        return AABB(pos.x - w / 2.0, pos.y - h / 2.0, w, h)
