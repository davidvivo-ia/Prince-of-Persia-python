"""Geometría visual — escala canónica al tile de 32x63 px del POP1.

Nota: las 14 unidades horizontales de la lógica (``TILE_SIZE_X``) son
unidades de *simulación*, no píxeles. El tile en pantalla del original
mide 32x63 px (DOS 320x200, sala de 10x3 tiles).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VisualLayout:
    """Tamaños finales en pantalla. Escala 2x del canon."""

    tile_w: int = 64
    """32 x 2 — ancho px (canon POP1)."""

    tile_h: int = 126
    """63 x 2 — alto px."""

    room_cols: int = 10
    """Canon."""

    room_rows: int = 3
    """Canon."""

    hud_top: int = 48
    """Banda HUD arriba."""

    @property
    def room_w(self) -> int:
        return self.tile_w * self.room_cols

    @property
    def room_h(self) -> int:
        return self.tile_h * self.room_rows

    @property
    def window_w(self) -> int:
        return self.room_w

    @property
    def window_h(self) -> int:
        return self.hud_top + self.room_h


LAYOUT = VisualLayout()
