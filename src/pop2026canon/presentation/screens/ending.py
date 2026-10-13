"""Pantallas de fin: nivel completado (con estadísticas), muerte,
victoria y derrota."""

from __future__ import annotations

import math

import pygame

from pop2026canon.application.stats import LevelStats
from pop2026canon.presentation import fonts
from pop2026canon.presentation.layout import px
from pop2026canon.presentation.palette import PALETTE


def _veil(surf: pygame.Surface, color: tuple[int, int, int], alpha: int) -> None:
    veil = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    veil.fill((*color, alpha))
    surf.blit(veil, (0, 0))


def _blink(t: float) -> tuple[int, int, int]:
    return PALETTE.warning if abs(math.sin(t * 2.5)) > 0.3 else PALETTE.poster_gold_dark


def draw_victory(
    surf: pygame.Surface,
    font_big: pygame.font.Font | None = None,
    font: pygame.font.Font | None = None,
    *,
    t: float = 0.0,
    deaths: int = 0,
    time_left: str = "",
) -> None:
    """Final victorioso: reunión con la princesa."""
    surf.fill(PALETTE.bg)
    w, h = surf.get_size()
    title = fonts.gold_title("VICTORIA", 60, glow=8)
    surf.blit(title, title.get_rect(center=(w // 2, h // 3)))
    lines = ["La princesa está a salvo.", "Jaffar ha caído."]
    if time_left:
        lines.append(f"Tiempo restante: {time_left}  ·  Muertes: {deaths}")
    for i, line in enumerate(lines):
        txt = fonts.render(line, 24, PALETTE.primary)
        surf.blit(txt, txt.get_rect(center=(w // 2, h // 2 + px(i * 28))))
    hint = fonts.render("Enter para volver al título", 20, _blink(t))
    surf.blit(hint, hint.get_rect(center=(w // 2, h * 5 // 6)))


def draw_defeat(
    surf: pygame.Surface,
    font_big: pygame.font.Font | None = None,
    font: pygame.font.Font | None = None,
    *,
    timeout: bool,
    t: float = 0.0,
) -> None:
    """Game over definitivo (timeout de los 60 minutos)."""
    surf.fill(PALETTE.bg)
    w, h = surf.get_size()
    msg = "TIEMPO AGOTADO" if timeout else "HAS MUERTO"
    color = PALETTE.warning if timeout else PALETTE.error
    title = fonts.render(msg, 56, color, bold=True)
    surf.blit(title, title.get_rect(center=(w // 2, h // 3)))
    sub = "La princesa ha muerto." if timeout else "El visir gana."
    line = fonts.render(sub, 24, PALETTE.primary_dark)
    surf.blit(line, line.get_rect(center=(w // 2, h // 2)))
    hint = fonts.render("Enter para volver al título", 20, _blink(t))
    surf.blit(hint, hint.get_rect(center=(w // 2, h * 3 // 4)))


def draw_death_overlay(
    surf: pygame.Surface,
    font_big: pygame.font.Font | None = None,
    font: pygame.font.Font | None = None,
    *,
    deaths: int,
    can_rewind: bool = False,
    modern: bool = False,
    pad: bool = False,
    t: float = 0.0,
) -> None:
    """Velo de muerte sobre el nivel: el reloj sigue corriendo (canon)."""
    w, h = surf.get_size()
    _veil(surf, (30, 0, 0), 150)
    title = fonts.render("HAS MUERTO", 56, PALETTE.error, bold=True)
    surf.blit(title, title.get_rect(center=(w // 2, h // 3)))
    line = fonts.render(f"Muertes: {deaths} · el tiempo sigue corriendo", 22, PALETTE.primary)
    surf.blit(line, line.get_rect(center=(w // 2, h // 2)))
    hints = []
    if can_rewind:
        hints.append(("Mantén LB" if pad else "Mantén R") + " para rebobinar el tiempo")
    confirm = "A" if pad else "Enter"
    hints.append(
        f"{confirm} para reaparecer en esta sala"
        if modern
        else f"{confirm} para reintentar el nivel"
    )
    for i, hint in enumerate(hints):
        col = _blink(t) if i == len(hints) - 1 else PALETTE.poster_gold
        txt = fonts.render(hint, 21, col)
        surf.blit(txt, txt.get_rect(center=(w // 2, h * 2 // 3 + px(i * 28))))


def draw_level_complete(
    surf: pygame.Surface,
    stats: LevelStats,
    level_name: str,
    rooms_total: int,
    t: float,
    *,
    pad: bool = False,
) -> None:
    """Resumen del nivel: tiempo, muertes, enemigos, pociones, salas."""
    w, h = surf.get_size()
    _veil(surf, (6, 4, 14), 175)
    k = min(1.0, t / 0.5)
    title = fonts.gold_title("NIVEL SUPERADO", 44, glow=6).copy()
    title.set_alpha(int(255 * k))
    surf.blit(title, title.get_rect(center=(w // 2, h // 4)))
    name = fonts.render(f"{stats.level} · {level_name}", 24, PALETTE.primary)
    surf.blit(name, name.get_rect(center=(w // 2, h // 4 + px(40))))
    rows = [
        ("Tiempo", stats.clock),
        ("Muertes", str(stats.deaths)),
        ("Enemigos derrotados", str(stats.guards_defeated)),
        ("Pociones", str(stats.potions)),
        ("Salas exploradas", f"{len(stats.visited)}/{rooms_total}"),
    ]
    if stats.rewound_ticks:
        rows.append(("Tiempo rebobinado", f"{stats.rewound_ticks / 12:.1f} s"))
    top = h // 2 - px(20)
    for i, (label, value) in enumerate(rows):
        appear = min(1.0, max(0.0, (t - 0.3 - i * 0.12) / 0.25))
        if appear <= 0:
            continue
        y = top + px(i * 28)
        lt = fonts.render(label, 22, PALETTE.primary_dark)
        vt = fonts.render(value, 22, PALETTE.warning)
        lt.set_alpha(int(255 * appear))
        vt.set_alpha(int(255 * appear))
        surf.blit(lt, lt.get_rect(midleft=(w // 2 - px(170), y)))
        surf.blit(vt, vt.get_rect(midright=(w // 2 + px(170), y)))
    if t > 1.0:
        hint = fonts.render(("A" if pad else "Enter") + " para continuar", 20, _blink(t))
        surf.blit(hint, hint.get_rect(center=(w // 2, h - px(40))))
