"""Pantallas finales — victoria, derrota, timeout."""

from __future__ import annotations

import pygame

from pop2026canon.presentation.palette import PALETTE


def draw_victory(surf: pygame.Surface, font_big: pygame.font.Font, font: pygame.font.Font) -> None:
    """Final victorioso: reunión con la princesa."""
    surf.fill(PALETTE.bg)
    w, h = surf.get_size()
    title = font_big.render("VICTORIA", True, PALETTE.accent)
    surf.blit(title, title.get_rect(center=(w // 2, h // 3)))
    line1 = font.render("La princesa está a salvo.", True, PALETTE.primary)
    line2 = font.render("Jaffar ha caído.", True, PALETTE.primary)
    surf.blit(line1, line1.get_rect(center=(w // 2, h // 2)))
    surf.blit(line2, line2.get_rect(center=(w // 2, h // 2 + 24)))


def draw_defeat(
    surf: pygame.Surface, font_big: pygame.font.Font, font: pygame.font.Font, *, timeout: bool
) -> None:
    """Game over definitivo (timeout de los 60 minutos)."""
    surf.fill(PALETTE.bg)
    w, h = surf.get_size()
    msg = "TIEMPO AGOTADO" if timeout else "HAS MUERTO"
    color = PALETTE.warning if timeout else PALETTE.error
    title = font_big.render(msg, True, color)
    surf.blit(title, title.get_rect(center=(w // 2, h // 3)))
    sub = "La princesa ha muerto." if timeout else "El visir gana."
    line = font.render(sub, True, PALETTE.primary_dark)
    surf.blit(line, line.get_rect(center=(w // 2, h // 2)))
    hint = font.render("R reinicia la campaña — ESC sale", True, PALETTE.muted)
    surf.blit(hint, hint.get_rect(center=(w // 2, h * 3 // 4)))


def draw_death_overlay(
    surf: pygame.Surface,
    font_big: pygame.font.Font,
    font: pygame.font.Font,
    *,
    deaths: int,
) -> None:
    """Velo de muerte sobre el nivel: el reloj sigue corriendo (canon)."""
    w, h = surf.get_size()
    veil = pygame.Surface((w, h), pygame.SRCALPHA)
    veil.fill((20, 0, 0, 150))
    surf.blit(veil, (0, 0))
    title = font_big.render("HAS MUERTO", True, PALETTE.error)
    surf.blit(title, title.get_rect(center=(w // 2, h // 3)))
    line = font.render(f"Muertes: {deaths} — el tiempo sigue corriendo", True, PALETTE.primary)
    surf.blit(line, line.get_rect(center=(w // 2, h // 2)))
    hint = font.render("Enter para reintentar el nivel", True, PALETTE.muted)
    surf.blit(hint, hint.get_rect(center=(w // 2, h * 3 // 4)))
