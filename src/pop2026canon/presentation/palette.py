"""Paleta tributo — homenaje al estilo Apple II HGR del POP original.

Todos los hex son propios. Inspirados en la limitación cromática del
hardware original (6 colores HGR) pero sin reproducir colores literales.
"""

from __future__ import annotations

from dataclasses import dataclass

RGB = tuple[int, int, int]


@dataclass(frozen=True, slots=True)
class Palette:
    """Paleta canon tributo POP1."""

    bg: RGB = (0x0A, 0x06, 0x18)
    bg_far: RGB = (0x18, 0x10, 0x28)
    brick: RGB = (0xC4, 0x5A, 0x24)
    brick_top: RGB = (0xE8, 0x8A, 0x40)
    brick_dark: RGB = (0x5C, 0x28, 0x0C)
    mortar: RGB = (0x10, 0x08, 0x04)
    pillar: RGB = (0x3C, 0x24, 0x14)
    primary: RGB = (0xE8, 0xDC, 0xB0)
    primary_dark: RGB = (0x80, 0x6C, 0x40)
    cloth: RGB = (0xD8, 0x2C, 0x18)
    accent: RGB = (0xA8, 0x40, 0xC8)
    success: RGB = (0x44, 0xC8, 0x44)
    warning: RGB = (0xE8, 0xB8, 0x40)
    error: RGB = (0xE0, 0x20, 0x20)
    muted: RGB = (0x5C, 0x4C, 0x6C)
    guard_skin: RGB = (0xA0, 0x70, 0x50)
    guard_armor: RGB = (0x40, 0x40, 0x50)
    blade: RGB = (0xE0, 0xE0, 0xE8)
    shadow_silhouette: RGB = (0x48, 0x18, 0x6C)
    princess_robe: RGB = (0xE0, 0x50, 0xA0)
    vizier_robe: RGB = (0x20, 0x10, 0x18)
    # Piel y ropa del kid — canon tributo
    kid_skin: RGB = (0xD8, 0xA0, 0x70)
    """Tono piel del kid: bronceado cálido."""
    kid_hair: RGB = (0x60, 0x30, 0x18)
    """Pelo castaño oscuro."""
    kid_tunic: RGB = (0xE8, 0xE4, 0xD0)
    """Túnica blanca-hueso."""
    kid_tunic_dark: RGB = (0xA8, 0xA0, 0x88)
    """Sombra de la túnica."""
    kid_belt: RGB = (0xC8, 0x28, 0x18)
    """Cinturón rojo canon."""
    kid_boot: RGB = (0x38, 0x20, 0x14)
    """Botas marrón muy oscuro."""


PALETTE = Palette()
