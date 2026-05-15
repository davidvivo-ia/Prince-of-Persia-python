"""Cinemáticas entre niveles — poster canon + tarjeta del nivel.

Cada level card pinta el poster con el cast narrativo del nivel
(prince + princesa/Jaffar/guard según corresponda) y superpone:
- Nombre del nivel grande
- Número de nivel
- Tagline narrativo
- Instrucción para continuar
"""

from __future__ import annotations

import math

import pygame

from pop2026canon.domain.level import Level
from pop2026canon.presentation.palette import PALETTE
from pop2026canon.presentation.poster import cast_for_level, draw_poster

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
    t: float = 0.0,
) -> None:
    """Tarjeta de presentación del nivel sobre el poster canon."""
    # Poster como fondo con cast narrativo del nivel y sin título.
    draw_poster(
        surf,
        font_big,
        t=t,
        cast=cast_for_level(level.number),
        curtain_openness=1.0,
        show_title=False,
    )

    w, h = surf.get_size()

    # Panel central con la información del nivel.
    panel_w = int(w * 0.6)
    panel_h = 160
    panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
    pygame.draw.rect(panel, (*PALETTE.bg, 200), panel.get_rect(), border_radius=10)
    pygame.draw.rect(
        panel,
        PALETTE.poster_gold,
        panel.get_rect(),
        2,
        border_radius=10,
    )
    panel_rect = panel.get_rect(center=(w // 2, h // 2))
    surf.blit(panel, panel_rect)

    title = font_big.render(level.name, True, PALETTE.poster_gold)
    surf.blit(title, title.get_rect(center=(w // 2, panel_rect.y + 32)))

    sub = font_small.render(f"NIVEL {level.number} de 14", True, PALETTE.primary)
    surf.blit(sub, sub.get_rect(center=(w // 2, panel_rect.y + 64)))

    tagline = LEVEL_TAGLINES.get(level.number, "")
    if tagline:
        text = font_small.render(tagline, True, PALETTE.primary_dark)
        surf.blit(text, text.get_rect(center=(w // 2, panel_rect.y + 100)))

    blink = abs(math.sin(t * 2.5)) > 0.3
    hint_col = PALETTE.warning if blink else PALETTE.poster_gold_dark
    hint = font_small.render("Pulsa ENTER", True, hint_col)
    surf.blit(hint, hint.get_rect(center=(w // 2, panel_rect.y + panel_h - 24)))
