"""Geometría visual — escala canónica al tile de 32x63 px del POP1.

Nota: las 14 unidades horizontales de la lógica (``TILE_SIZE_X``) son
unidades de *simulación*, no píxeles. El tile en pantalla del original
mide 32x63 px (DOS 320x200, sala de 10x3 tiles).

El lienzo interno es HD: el canon a 4x (1280x852). Las medidas de
diseño de la interfaz se escriben en la escala clásica 2x (640x426) y
se pasan por :func:`px`, así que todo el arte se pinta nítido a la
resolución final en vez de ampliarse.
"""

from __future__ import annotations

from dataclasses import dataclass

SCALE = 2
"""Factor del lienzo HD respecto a la escala de diseño 2x del canon."""


@dataclass(frozen=True, slots=True)
class VisualLayout:
    """Tamaños finales en pantalla (lienzo HD)."""

    scale: int = SCALE
    """Píxeles HD por píxel de diseño."""

    tile_w: int = 64 * SCALE
    """32 x 4 — ancho px (canon POP1)."""

    tile_h: int = 126 * SCALE
    """63 x 4 — alto px."""

    room_cols: int = 10
    """Canon."""

    room_rows: int = 3
    """Canon."""

    hud_top: int = 48 * SCALE
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

    @property
    def floor_top(self) -> int:
        """Profundidad visible de la cara superior de una losa (px)."""
        return 10 * self.scale

    @property
    def floor_face(self) -> int:
        """Alto de la cara frontal de la losa, al pie de la celda (px)."""
        return 16 * self.scale

    @property
    def foot_lift(self) -> int:
        """Los pies pisan el centro de la cara superior de la losa: tanto
        por encima del borde inferior de la celda."""
        return self.floor_face + self.floor_top // 2

    @property
    def base_size(self) -> tuple[int, int]:
        """Tamaño de diseño (canon 2x): la ventana "1x" de los ajustes."""
        return self.window_w // self.scale, self.window_h // self.scale


LAYOUT = VisualLayout()


def px(v: float) -> int:
    """Medida de diseño (escala 2x clásica) → píxeles del lienzo HD."""
    return round(v * LAYOUT.scale)
