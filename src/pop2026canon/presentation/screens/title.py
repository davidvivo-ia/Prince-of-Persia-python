"""Pantalla de título — PRINCE OF PERSIA con instrucciones."""

from __future__ import annotations

import math

import pygame

from pop2026canon.presentation.palette import PALETTE


def draw(
    surf: pygame.Surface, font_big: pygame.font.Font, font_small: pygame.font.Font, t: float
) -> None:
    """Pinta el título con un sutil pulso."""
    surf.fill(PALETTE.bg)
    w, h = surf.get_size()

    # Título grande pulsante
    pulse = abs(math.sin(t * 1.5))
    color = (
        int(PALETTE.brick_top[0] * (0.7 + 0.3 * pulse)),
        int(PALETTE.brick_top[1] * (0.7 + 0.3 * pulse)),
        int(PALETTE.brick_top[2] * (0.7 + 0.3 * pulse)),
    )
    title = font_big.render("PRINCE OF PERSIA", True, color)
    surf.blit(title, title.get_rect(center=(w // 2, h // 3)))

    subtitle = font_small.render("Canon Edition — Python 2026", True, PALETTE.primary_dark)
    surf.blit(subtitle, subtitle.get_rect(center=(w // 2, h // 3 + 40)))

    # Controles
    controls = [
        "← → ↑ ↓   Mover",
        "SHIFT    Agarrar / Andar lento",
        "SPACE    Atacar",
        "ESC      Salir",
        "",
        "Pulsa ENTER para empezar",
    ]
    for i, line in enumerate(controls):
        col = PALETTE.warning if i == len(controls) - 1 else PALETTE.primary
        text = font_small.render(line, True, col)
        surf.blit(text, text.get_rect(center=(w // 2, h * 2 // 3 + i * 22)))
