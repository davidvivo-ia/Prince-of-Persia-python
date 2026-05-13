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
