"""Pantallas de fin: nivel completado (con estadísticas), muerte,
victoria y derrota."""

from __future__ import annotations

import math

import pygame

from pop2026canon.application.stats import LevelStats
from pop2026canon.presentation import fonts
from pop2026canon.presentation.i18n import tr
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
    time_used: str = "",
    medals: int | None = None,
) -> None:
    """Final victorioso: reunión con la princesa, con el resumen de la
    campaña (tiempo consumido, muertes, medallas)."""
    surf.fill(PALETTE.bg)
    w, h = surf.get_size()
    title = fonts.gold_title(tr("VICTORIA"), 60, glow=8)
    surf.blit(title, title.get_rect(center=(w // 2, h // 3)))
    lines = [tr("La princesa está a salvo."), tr("Jaffar ha caído.")]
    if time_used and medals is not None:
        lines.append(
            tr("Tiempo total: {t}  ·  Muertes: {d}  ·  Medallas: {m}").format(
                t=time_used, d=deaths, m=medals
            )
        )
    elif time_left:
        lines.append(tr("Tiempo restante: {t}  ·  Muertes: {d}").format(t=time_left, d=deaths))
    for i, line in enumerate(lines):
        txt = fonts.render(line, 24, PALETTE.primary)
        surf.blit(txt, txt.get_rect(center=(w // 2, h // 2 + px(i * 28))))
    hint = fonts.render(tr("Enter para volver al título"), 20, _blink(t))
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
    msg = tr("TIEMPO AGOTADO") if timeout else tr("HAS MUERTO")
    color = PALETTE.warning if timeout else PALETTE.error
    title = fonts.render(msg, 56, color, bold=True)
    surf.blit(title, title.get_rect(center=(w // 2, h // 3)))
    sub = tr("La princesa ha muerto.") if timeout else tr("El visir gana.")
    line = fonts.render(sub, 24, PALETTE.primary_dark)
    surf.blit(line, line.get_rect(center=(w // 2, h // 2)))
    hint = fonts.render(tr("Enter para volver al título"), 20, _blink(t))
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
    title = fonts.render(tr("HAS MUERTO"), 56, PALETTE.error, bold=True)
    surf.blit(title, title.get_rect(center=(w // 2, h // 3)))
    line = fonts.render(
        tr("Muertes: {n} · el tiempo sigue corriendo").format(n=deaths), 22, PALETTE.primary
    )
    surf.blit(line, line.get_rect(center=(w // 2, h // 2)))
    hints = []
    if can_rewind:
        hints.append(tr("Mantén LB" if pad else "Mantén R") + tr(" para rebobinar el tiempo"))
    confirm = "A" if pad else "Enter"
    hints.append(
        tr("{c} para reaparecer en esta sala" if modern else "{c} para reintentar el nivel").format(
            c=confirm
        )
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
    medals: tuple[str, ...] = (),
    new_medals: tuple[str, ...] = (),
    delta: str = "",
    new_record: bool = False,
) -> None:
    """Resumen del nivel: tiempo, muertes, enemigos, pociones, salas."""
    w, h = surf.get_size()
    _veil(surf, (6, 4, 14), 175)
    k = min(1.0, t / 0.5)
    title = fonts.gold_title(tr("NIVEL SUPERADO"), 44, glow=6).copy()
    title.set_alpha(int(255 * k))
    surf.blit(title, title.get_rect(center=(w // 2, h // 4)))
    name = fonts.render(f"{stats.level} · {level_name}", 24, PALETTE.primary)
    surf.blit(name, name.get_rect(center=(w // 2, h // 4 + px(40))))
    clock = stats.clock + (f"  ({delta})" if delta else "")
    rows = [
        (tr("Tiempo"), clock),
        (tr("Muertes"), str(stats.deaths)),
        (tr("Enemigos derrotados"), str(stats.guards_defeated)),
        (tr("Pociones"), str(stats.potions)),
        (tr("Salas exploradas"), f"{len(stats.visited)}/{rooms_total}"),
    ]
    if stats.rewound_ticks:
        rows.append((tr("Tiempo rebobinado"), f"{stats.rewound_ticks / 12:.1f} s"))
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
    if medals:
        from pop2026canon.presentation.screens.levels import MEDAL_COLORS, MEDAL_NAMES

        shown = [m for m in medals if m != "completed"]
        base_y = top + px(len(rows) * 28 + 16)
        for i, m in enumerate(shown):
            appear = min(1.0, max(0.0, (t - 1.2 - i * 0.25) / 0.3))
            if appear <= 0:
                continue
            cx = w // 2 + (i - (len(shown) - 1) / 2) * px(150)
            r = int(px(12) * (1.6 - 0.6 * appear))
            col = MEDAL_COLORS[m]
            pts = [(cx, base_y - r), (cx + r, base_y), (cx, base_y + r), (cx - r, base_y)]
            pygame.draw.polygon(surf, col, pts)
            pygame.draw.polygon(surf, (16, 10, 22), pts, 1)
            label = tr(MEDAL_NAMES[m]) + ("  " + tr("¡nueva!") if m in new_medals else "")
            txt = fonts.render(label, 17, col if m in new_medals else PALETTE.primary_dark)
            txt.set_alpha(int(255 * appear))
            surf.blit(txt, txt.get_rect(midtop=(int(cx), base_y + px(16))))
    if new_record and t > 0.8:
        k = 1.0 + 0.06 * math.sin(t * 6)
        rec = fonts.gold_title(tr("¡Nuevo récord!"), 26, glow=5)
        rec = pygame.transform.smoothscale(
            rec, (int(rec.get_width() * k), int(rec.get_height() * k))
        )
        surf.blit(rec, rec.get_rect(center=(w // 2, h // 4 + px(68))))
    if t > 1.0:
        hint = fonts.render(("A" if pad else "Enter") + tr(" para continuar"), 20, _blink(t))
        surf.blit(hint, hint.get_rect(center=(w // 2, h - px(22))))
