"""Carta de nivel: pantalla intermedia con número, título y subtítulo."""

from __future__ import annotations

import pygame

from pop2026.application.campaign import LevelInfo
from pop2026.presentation.theme import PALETTE


def draw(
    surface: pygame.Surface,
    info: LevelInfo,
    level_index: int,
    total: int,
    *,
    font_big: pygame.font.Font,
    font: pygame.font.Font,
) -> None:
    """Carta intermedia entre niveles.

    Muestra "NIVEL X / Y" + título + subtítulo + "pulsa una tecla".
    """
    surface.fill(PALETTE.bg)
    w, h = surface.get_size()

    # Marco
    pygame.draw.rect(surface, PALETTE.warning, (16, 16, w - 32, h - 32), 2)
    inner = pygame.Rect(24, 24, w - 48, h - 48)
    pygame.draw.rect(surface, PALETTE.bg_far, inner)

    # Numeración
    num = font.render(f"NIVEL  {level_index:02d}  /  {total:02d}", True, PALETTE.accent)
    surface.blit(num, num.get_rect(center=(w // 2, h // 2 - 56)))

    # Título grande
    title = font_big.render(info.title.upper(), True, PALETTE.primary)
    surface.blit(title, title.get_rect(center=(w // 2, h // 2 - 16)))

    # Subtítulo
    sub = font.render(info.subtitle, True, PALETTE.warning)
    surface.blit(sub, sub.get_rect(center=(w // 2, h // 2 + 24)))

    # Pulsa
    msg = font.render("Pulsa una tecla para entrar", True, PALETTE.muted)
    surface.blit(msg, msg.get_rect(center=(w // 2, h - 60)))
