"""Cinemáticas entre niveles — tarjetas de texto."""

from __future__ import annotations

import pygame

from pop2026canon.domain.level import Level
from pop2026canon.presentation.palette import PALETTE

LEVEL_TAGLINES: dict[int, str] = {
    1: "Despiertas en una mazmorra del palacio.",
    2: "El visir ha tomado el trono. Detenlo.",
    3: "Algo se mueve entre los huesos olvidados.",
    4: "Un espejo... ¿muestra al enemigo verdadero?",
    5: "Tu propia sombra te roba lo que aún tenías.",
    6: "Salta. La sombra salta contigo.",
    7: "Las montañas del palacio se alzan.",
    8: "Cuevas. Un ratón inesperado.",
    9: "La tumba. Más esqueletos. Camina rápido.",
    10: "Torre arriba. No mires abajo.",
    11: "Una sala más. Y otra.",
    12: "El visir Jaffar. La hora final.",
    13: "Corre. Tu sombra ya no te imita.",
    14: "Ella te espera.",
}


def draw_level_card(
    surf: pygame.Surface,
    level: Level,
    font_big: pygame.font.Font,
    font_small: pygame.font.Font,
) -> None:
    """Tarjeta de presentación del nivel."""
    surf.fill(PALETTE.bg)
    w, h = surf.get_size()

    title = font_big.render(level.name, True, PALETTE.brick_top)
    surf.blit(title, title.get_rect(center=(w // 2, h // 3)))

    sub = font_small.render(f"NIVEL {level.number} de 14", True, PALETTE.primary)
    surf.blit(sub, sub.get_rect(center=(w // 2, h // 3 + 40)))

    tagline = LEVEL_TAGLINES.get(level.number, "")
    if tagline:
        text = font_small.render(tagline, True, PALETTE.primary_dark)
        surf.blit(text, text.get_rect(center=(w // 2, h // 2)))

    hint = font_small.render("Pulsa ENTER", True, PALETTE.warning)
    surf.blit(hint, hint.get_rect(center=(w // 2, h * 3 // 4)))
