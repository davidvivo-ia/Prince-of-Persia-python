"""Pantallas de fin de partida: victoria total y derrota."""

from __future__ import annotations

import pygame

from pop2026.presentation.theme import PALETTE


def draw_victory(
    surface: pygame.Surface,
    *,
    time_left_ticks: int,
    font_big: pygame.font.Font,
    font: pygame.font.Font,
) -> None:
    """Pantalla cuando el jugador termina la campaña."""
    surface.fill(PALETTE.bg)
    w, h = surface.get_size()

    # Halo violeta de fondo
    for r_iter in range(8, 0, -1):
        alpha = 12 - r_iter
        layer = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.circle(layer, (*PALETTE.accent, alpha), (w // 2, h // 2), r_iter * 40)
        surface.blit(layer, (0, 0))

    title = font_big.render("VICTORIA", True, PALETTE.accent)
    surface.blit(title, title.get_rect(center=(w // 2, h // 2 - 30)))

    secs = time_left_ticks // 60
    mm, ss = divmod(secs, 60)
    txt = font.render(
        f"Has terminado la campaña con {mm:02d}:{ss:02d} en el reloj.",
        True,
        PALETTE.primary,
    )
    surface.blit(txt, txt.get_rect(center=(w // 2, h // 2 + 10)))

    msg = font.render("Pulsa Esc para salir.", True, PALETTE.muted)
    surface.blit(msg, msg.get_rect(center=(w // 2, h - 40)))


def draw_defeat(
    surface: pygame.Surface,
    *,
    level_index: int,
    timeout: bool,
    font_big: pygame.font.Font,
    font: pygame.font.Font,
) -> None:
    """Pantalla cuando el jugador muere o se queda sin tiempo."""
    surface.fill(PALETTE.bg)
    w, h = surface.get_size()

    overlay = pygame.Surface((w, h), pygame.SRCALPHA)
    overlay.fill((PALETTE.error[0], 0, 0, 20))
    surface.blit(overlay, (0, 0))

    title_text = "TIEMPO AGOTADO" if timeout else "HAS MUERTO"
    color = PALETTE.warning if timeout else PALETTE.error
    title = font_big.render(title_text, True, color)
    surface.blit(title, title.get_rect(center=(w // 2, h // 2 - 20)))

    sub = font.render(
        f"Caíste en el nivel {level_index:02d}.",
        True,
        PALETTE.primary,
    )
    surface.blit(sub, sub.get_rect(center=(w // 2, h // 2 + 16)))

    msg = font.render("Pulsa R para volver a intentarlo  ·  Esc para salir", True, PALETTE.muted)
    surface.blit(msg, msg.get_rect(center=(w // 2, h - 40)))
