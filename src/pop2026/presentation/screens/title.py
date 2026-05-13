"""Pantalla de título: logo, subtítulo, instrucción de continuar."""

from __future__ import annotations

import math

import pygame

from pop2026.presentation.theme import PALETTE


def draw(
    surface: pygame.Surface, font_big: pygame.font.Font, font: pygame.font.Font, t: float
) -> None:
    """Dibuja la pantalla de título.

    Args:
        surface: superficie destino.
        font_big: fuente grande para el logo.
        font: fuente normal.
        t: tiempo (segundos) para animar el parpadeo del "pulsa ENTER".
    """
    surface.fill(PALETTE.bg)
    w, h = surface.get_size()

    # Pared trasera con degradado
    for i in range(h):
        ratio = i / h
        col = tuple(int(PALETTE.bg_far[k] * (1 - ratio) + PALETTE.bg[k] * ratio) for k in range(3))
        pygame.draw.line(surface, col, (0, i), (w, i))

    # Banda decorativa de ladrillo arriba y abajo
    pygame.draw.rect(surface, PALETTE.brick, (0, 0, w, 14))
    pygame.draw.rect(surface, PALETTE.brick_top, (0, 0, w, 2))
    pygame.draw.rect(surface, PALETTE.brick, (0, h - 14, w, 14))
    pygame.draw.rect(surface, PALETTE.brick_top, (0, h - 14, w, 2))

    # Logo
    title_img = font_big.render("POP · 2026", True, PALETTE.primary)
    title_rect = title_img.get_rect(center=(w // 2, h // 2 - 40))
    # Sombra
    shadow = font_big.render("POP · 2026", True, PALETTE.bg_far)
    shadow_rect = title_rect.move(3, 3)
    surface.blit(shadow, shadow_rect)
    surface.blit(title_img, title_rect)

    # Subtítulo
    sub = font.render(
        "Prince of Persia (1989), reimaginado en Python 2026",
        True,
        PALETTE.cloth,
    )
    surface.blit(sub, sub.get_rect(center=(w // 2, h // 2 + 4)))

    # "Pulsa ENTER" parpadeante
    alpha = int((math.sin(t * 3.0) + 1.0) * 0.5 * 255)
    msg = font.render("Pulsa ENTER para comenzar  ·  Esc para salir", True, PALETTE.accent)
    msg.set_alpha(alpha)
    surface.blit(msg, msg.get_rect(center=(w // 2, h // 2 + 48)))

    # Crédito pequeño abajo
    credit = font.render("Diseño y código originales · v1.0.0", True, PALETTE.muted)
    surface.blit(credit, credit.get_rect(center=(w // 2, h - 26)))
