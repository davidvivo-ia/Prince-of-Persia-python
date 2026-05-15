"""Geometría visual — escala canónica al ratio 14:63 tile size."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VisualLayout:
    """Tamaños finales en pantalla. Escala 2x del canon."""

    tile_w: int = 28
    """14 x 2 — ancho px."""

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
