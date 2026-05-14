"""Sistema de diseño: paleta, tamaños, glyphs.

Ver ``docs/design.md`` para la justificación.
"""

from __future__ import annotations

from dataclasses import dataclass

RGB = tuple[int, int, int]
"""Triplete RGB en 0..255."""


@dataclass(frozen=True, slots=True)
class Palette:
    """Paleta-homenaje a la presentación Apple II HGR del original.

    HGR sólo permitía 6 colores (negro, blanco, violeta, naranja, verde,
    azul) y obligaba a alternarlos por línea. Esta paleta toma esa
    severidad cromática como inspiración: tonos saturados, dominio del
    naranja-ladrillo y el violeta de fondo, contrastes altos. Los hex
    son originales — ningún tono se copia de ningún asset existente.
    """

    bg: RGB = (0x0A, 0x06, 0x18)
    """Fondo profundo (negro con tinte violeta HGR)."""

    bg_far: RGB = (0x18, 0x10, 0x28)
    """Pared lejana, ligeramente más clara."""

    brick: RGB = (0xC4, 0x5A, 0x24)
    """Naranja-ladrillo saturado (artifact HGR clásico)."""

    brick_top: RGB = (0xE8, 0x8A, 0x40)
    """Brillo superior del ladrillo."""

    brick_dark: RGB = (0x5C, 0x28, 0x0C)
    """Sombra inferior del ladrillo."""

    mortar: RGB = (0x10, 0x08, 0x04)
    """Líneas oscuras entre ladrillos."""

    pillar: RGB = (0x3C, 0x24, 0x14)
    """Pilares de columna vertical (madera oscura)."""

    primary: RGB = (0xE8, 0xDC, 0xB0)
    """Túnica clara del príncipe (blanco-pergamino)."""

    primary_dark: RGB = (0x80, 0x6C, 0x40)
    """Sombras del príncipe."""

    cloth: RGB = (0xD8, 0x2C, 0x18)
    """Faja roja del príncipe — acento icónico."""

    accent: RGB = (0xA8, 0x40, 0xC8)
    """Violeta HGR — exits, magia, acentos."""

    success: RGB = (0x44, 0xC8, 0x44)
    """Verde HGR — pociones curativas."""

    warning: RGB = (0xE8, 0xB8, 0x40)
    """Oro polvoriento — reloj, rejas."""

    error: RGB = (0xE0, 0x20, 0x20)
    """Rojo — daño, guardia, sangre."""

    muted: RGB = (0x5C, 0x4C, 0x6C)
    """Lila apagado — tile inactivo, sombras."""

    guard_skin: RGB = (0xA0, 0x70, 0x50)
    """Tono del guardia — distinguible del príncipe."""

    guard_armor: RGB = (0x40, 0x40, 0x50)
    """Armadura plomiza del guardia."""

    blade: RGB = (0xE0, 0xE0, 0xE8)
    """Filo del sable — blanco metálico."""


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
