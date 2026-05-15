"""Pantalla de título — poster canon animado + instrucciones.

Si ``t < INTRO_DURATION`` se reproduce la intro animada (cortinas que
se abren, luna saliendo, título apareciendo). Después se queda en el
estado final con las instrucciones.
"""

from __future__ import annotations

import math

import pygame

from pop2026canon.presentation.palette import PALETTE
from pop2026canon.presentation.poster import PosterCast, draw_poster

INTRO_DURATION: float = 3.5
"""Segundos que dura la cinemática de apertura."""


def _ease_out_cubic(x: float) -> float:
    return 1 - (1 - x) ** 3


def draw(
    surf: pygame.Surface, font_big: pygame.font.Font, font_small: pygame.font.Font, t: float
) -> None:
    """Pinta el título con animación de apertura si ``t < INTRO_DURATION``."""
    if t < INTRO_DURATION:
        # Fase de intro: cortinas opening + título fade-in.
        progress = _ease_out_cubic(min(1.0, t / INTRO_DURATION))
        openness = progress  # 0 → cerradas → 1 → abiertas
        show_title = progress > 0.45
        draw_poster(
            surf,
            font_big,
            t=t,
            cast=PosterCast(),
            curtain_openness=openness,
            show_title=show_title,
        )
        # Fundido a negro al inicio (las cortinas tapan todo)
        if progress < 0.05:
            overlay = pygame.Surface(surf.get_size())
            overlay.fill(PALETTE.bg)
            overlay.set_alpha(int(255 * (1 - progress / 0.05)))
            surf.blit(overlay, (0, 0))
        return

    # Estado estable post-intro: poster + subtítulo + controles.
    draw_poster(surf, font_big, t=t, cast=PosterCast(), curtain_openness=1.0)

    w, h = surf.get_size()
    subtitle = font_small.render("Canon Edition — Python 2026", True, PALETTE.poster_gold)
    surf.blit(subtitle, subtitle.get_rect(center=(w // 2, h // 4 + 30)))

    # Panel semi-transparente para los controles al pie
    controls = [
        "← → ↑ ↓   Mover",
        "SHIFT    Agarrar / Andar lento",
        "SPACE    Atacar",
        "ESC      Salir",
        "",
        "Pulsa ENTER para empezar",
    ]
    panel_h = 22 * len(controls) + 16
    panel = pygame.Surface((w // 2, panel_h), pygame.SRCALPHA)
    pygame.draw.rect(panel, (*PALETTE.bg, 180), panel.get_rect(), border_radius=8)
    surf.blit(panel, panel.get_rect(center=(w // 2, h - panel_h // 2 - 12)))

    base_y = h - panel_h - 4 + 16
    blink = abs(math.sin(t * 2.5)) > 0.3
    for i, line in enumerate(controls):
        if i == len(controls) - 1:
            col = PALETTE.warning if blink else PALETTE.poster_gold_dark
        else:
            col = PALETTE.primary
        text = font_small.render(line, True, col)
        surf.blit(text, text.get_rect(center=(w // 2, base_y + i * 22)))
