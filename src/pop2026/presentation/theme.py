"""Sistema de diseño: paleta, tamaños, glyphs.

Ver ``docs/design.md`` para la justificación.
"""

from __future__ import annotations

from dataclasses import dataclass

RGB = tuple[int, int, int]
"""Triplete RGB en 0..255."""


@dataclass(frozen=True, slots=True)
class Palette:
    """Paleta Persia Nocturna."""

    bg: RGB = (0x1A, 0x13, 0x25)
    bg_elev: RGB = (0x2A, 0x1F, 0x3D)
    primary: RGB = (0xE8, 0xD9, 0xA8)
    accent: RGB = (0xC7, 0x7D, 0xFF)
    success: RGB = (0x8F, 0xE3, 0x88)
    warning: RGB = (0xF2, 0xC1, 0x4E)
    error: RGB = (0xE6, 0x39, 0x46)
    muted: RGB = (0x6E, 0x5F, 0x8A)


PALETTE = Palette()
"""Singleton de paleta por defecto."""


@dataclass(frozen=True, slots=True)
class Layout:
    """Geometría de la ventana y los tiles."""

    tile_size: int = 24
    """Tamaño de un tile en píxeles."""

    cols: int = 40
    """Anchura lógica en celdas."""

    rows: int = 14
    """Altura lógica en celdas (incluye HUD)."""

    hud_rows: int = 2
    """Filas reservadas para HUD arriba/abajo."""

    @property
    def width_px(self) -> int:
        """Anchura total en píxeles."""
        return self.cols * self.tile_size

    @property
    def height_px(self) -> int:
        """Altura total en píxeles."""
        return self.rows * self.tile_size


LAYOUT = Layout()
"""Singleton de layout por defecto."""
