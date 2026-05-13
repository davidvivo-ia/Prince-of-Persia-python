"""Sistema de diseño: paleta, tamaños, glyphs.

Ver ``docs/design.md`` para la justificación.
"""

from __future__ import annotations

from dataclasses import dataclass

RGB = tuple[int, int, int]
"""Triplete RGB en 0..255."""


@dataclass(frozen=True, slots=True)
class Palette:
    """Paleta Persia Nocturna refinada para silueta tipo POP."""

    bg: RGB = (0x14, 0x0E, 0x1F)
    """Fondo profundo, casi negro violáceo."""

    bg_far: RGB = (0x22, 0x18, 0x33)
    """Pared lejana de fondo, ligeramente más clara."""

    brick: RGB = (0x6E, 0x4A, 0x2A)
    """Color principal del ladrillo del suelo."""

    brick_top: RGB = (0xA8, 0x7C, 0x4E)
    """Borde superior iluminado del suelo."""

    brick_dark: RGB = (0x3C, 0x26, 0x14)
    """Sombra inferior del ladrillo."""

    mortar: RGB = (0x1A, 0x10, 0x08)
    """Líneas entre ladrillos."""

    pillar: RGB = (0x46, 0x33, 0x22)
    """Pilares de columna vertical."""

    primary: RGB = (0xE8, 0xD9, 0xA8)
    """Skin/ropa del príncipe (pergamino dorado)."""

    primary_dark: RGB = (0x8C, 0x6E, 0x3F)
    """Sombras del príncipe."""

    cloth: RGB = (0xB8, 0x4A, 0x2E)
    """Cinturón / banda roja del príncipe (acento clásico de POP)."""

    accent: RGB = (0xC7, 0x7D, 0xFF)
    """Violeta para halos, salida, magia."""

    success: RGB = (0x6F, 0xD8, 0x5F)
    """Verde de poción curativa."""

    warning: RGB = (0xF2, 0xC1, 0x4E)
    """Oro polvoriento — reloj, rejas."""

    error: RGB = (0xE6, 0x39, 0x46)
    """Rojo — daño, guardia, sangre."""

    muted: RGB = (0x6E, 0x5F, 0x8A)
    """Lila apagado — tile inactivo, sombras."""

    guard_skin: RGB = (0xB5, 0x8A, 0x5C)
    """Tono del guardia."""

    guard_armor: RGB = (0x4C, 0x4C, 0x58)
    """Armadura plomiza del guardia."""

    blade: RGB = (0xDD, 0xDD, 0xE8)
    """Filo del sable."""


PALETTE = Palette()
"""Singleton de paleta por defecto."""


@dataclass(frozen=True, slots=True)
class Layout:
    """Geometría de la ventana y los tiles."""

    tile_w: int = 48
    """Anchura de un tile en píxeles."""

    tile_h: int = 64
    """Altura de un tile en píxeles. POP usa tiles altos (~63 px)."""

    cols: int = 20
    """Anchura lógica en celdas."""

    rows: int = 6
    """Altura lógica en celdas. Estilo POP: dos pisos compactos."""

    hud_top: int = 32
    """Banda de HUD arriba en píxeles."""

    @property
    def width_px(self) -> int:
        """Anchura total en píxeles."""
        return self.cols * self.tile_w

    @property
    def height_px(self) -> int:
        """Altura total en píxeles, incluyendo HUD."""
        return self.rows * self.tile_h + self.hud_top


LAYOUT = Layout()
"""Singleton de layout por defecto."""
