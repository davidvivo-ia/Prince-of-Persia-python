"""Póster procedural inspirado en la portada de POP1 (1989), en HD.

Capas en composición:

1. **Cielo nocturno** en degradado con nebulosa tenue y estrellas que
   titilan (alguna estrella fugaz).
2. **Luna llena** con halo difuso.
3. **Dunas y palacio** en dos planos de silueta (lejano y cercano) con
   ventanas cálidas que parpadean y el filo azul de la luna.
4. **Jirones de nube** que se desplazan despacio.
5. **Cortinas** de terciopelo con pliegues sombreados y cordón dorado.
6. **Personajes** del nivel en primer plano (bañados por la luna).
7. **Título** en oro metálico con halo.

Las capas estáticas se cachean por tamaño; por frame sólo se mueven
estrellas, nubes, ventanas y cortinas. Todo procedural — sin assets ni
arte del original (tributo *clean-room*).
"""

from __future__ import annotations

import functools
import math
import random
from dataclasses import dataclass

import numpy as np
import pygame

from pop2026canon.presentation import fonts
from pop2026canon.presentation.char_atlas import CharPalette, sprite
from pop2026canon.presentation.layout import px
from pop2026canon.presentation.palette import PALETTE

RGB = tuple[int, int, int]


@dataclass(frozen=True, slots=True)
class PosterCast:
    """Qué personajes incluir en el primer plano del poster."""

    princess: bool = True
    """Silueta de la princesa a la izquierda."""

    vizier: bool = True
    """Silueta amenazante de Jaffar arriba-derecha."""

    prince: bool = True
    """Silueta del prince al centro-bajo."""

    guard: bool = False
    """Guard auxiliar a la derecha."""


# ---------------------------------------------------------------------------
# Capas estáticas (cacheadas por tamaño)
# ---------------------------------------------------------------------------


@functools.lru_cache(maxsize=2)
def _sky(w: int, h: int) -> pygame.Surface:
    """Cielo con degradado, nebulosa y halo lunar."""
    ys = np.linspace(0.0, 1.0, h, dtype=np.float32)[None, :, None]
    top = np.array((8, 10, 38), dtype=np.float32)
    mid = np.array((26, 34, 92), dtype=np.float32)
    low = np.array((64, 54, 104), dtype=np.float32)
    k1 = np.clip(ys / 0.6, 0, 1)
    k2 = np.clip((ys - 0.6) / 0.4, 0, 1)
    arr = top * (1 - k1) + mid * k1
    arr = arr * (1 - k2) + low * k2
    arr = np.repeat(arr, w, axis=0)
    rng = np.random.default_rng(1989)
    # Nebulosa: ruido suave teñido
    g = rng.normal(0, 1, (w // 64 + 2, h // 64 + 2)).astype(np.float32)
    small = pygame.surfarray.make_surface(
        np.repeat(((np.clip(g, -2, 2) + 2) * 60)[:, :, None], 3, axis=2).astype(np.uint8)
    )
    neb = pygame.surfarray.array3d(pygame.transform.smoothscale(small, (w, h))).astype(np.float32)
    arr += (neb / 255.0 - 0.45) * np.array((26, 14, 40), dtype=np.float32)
    # Halo de la luna
    mx, my = w * 0.3, h * 0.24
    xx = np.arange(w, dtype=np.float32)[:, None]
    yy = np.arange(h, dtype=np.float32)[None, :]
    d = np.sqrt((xx - mx) ** 2 + (yy - my) ** 2) / (h * 0.45)
    halo = np.clip(1.0 - d, 0, 1) ** 2.2
    arr += halo[:, :, None] * np.array((70, 80, 120), dtype=np.float32)
    arr += rng.normal(0, 1.6, (w, h, 1)).astype(np.float32)
    surf = pygame.Surface((w, h))
    pygame.surfarray.blit_array(surf, np.clip(arr, 0, 255).astype(np.uint8))
    # Luna con mares y borde suave
    r = max(px(24), h // 13)
    cx, cy = int(mx), int(my)
    glow = pygame.Surface((r * 6, r * 6), pygame.SRCALPHA)
    pygame.draw.circle(glow, (200, 210, 255, 60), (r * 3, r * 3), int(r * 1.6))
    glow = pygame.transform.box_blur(glow, r // 2)
    surf.blit(glow, (cx - r * 3, cy - r * 3))
    pygame.draw.circle(surf, PALETTE.poster_moon, (cx, cy), r)
    mrng = random.Random(7)
    for _ in range(7):
        a = mrng.uniform(0, math.tau)
        dd = mrng.uniform(0, r * 0.6)
        rr = mrng.uniform(r * 0.12, r * 0.3)
        pygame.draw.circle(
            surf,
            (214, 206, 182),
            (int(cx + math.cos(a) * dd), int(cy + math.sin(a) * dd)),
            int(rr),
        )
    shade = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
    pygame.draw.circle(shade, (40, 40, 90, 70), (r + r // 3, r + r // 4), r)
    mask = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
    pygame.draw.circle(mask, (255, 255, 255, 255), (r, r), r)
    shade.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    surf.blit(shade, (cx - r, cy - r))
    return surf


def _skyline(
    w: int, h: int, *, near: bool
) -> tuple[pygame.Surface, list[tuple[int, int, int, int]]]:
    """Silueta del palacio (lejano o cercano) y sus ventanas (x, y, w, h)."""
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    rng = random.Random(14 if near else 4)
    col = (30, 30, 62) if near else (58, 60, 108)
    rim = (120, 140, 210) if near else (110, 120, 180)
    base_y = int(h * (0.74 if near else 0.66))
    windows: list[tuple[int, int, int, int]] = []
    # Dunas / muralla
    pts = [(0, h)]
    for x in range(0, w + px(40), px(40)):
        pts.append((x, base_y + int(math.sin(x * 0.01 + (1 if near else 0)) * px(6))))
    pts.append((w, h))
    pygame.draw.polygon(surf, col, pts)
    # Edificios
    x = int(w * 0.12)
    while x < w * 0.9:
        bw = rng.randint(px(30), px(70)) if near else rng.randint(px(20), px(46))
        bh = rng.randint(px(30), px(90)) if near else rng.randint(px(40), px(110))
        top = base_y - bh
        pygame.draw.rect(surf, col, (x, top, bw, bh + px(4)))
        pygame.draw.line(surf, rim, (x, top), (x, base_y), 1)
        kind = rng.random()
        if kind < 0.45:
            # Cúpula bulbosa con aguja
            dw = bw + px(6)
            pygame.draw.ellipse(surf, col, (x - px(3), top - dw * 2 // 3, dw, dw))
            pygame.draw.arc(
                surf, rim, (x - px(3), top - dw * 2 // 3, dw, dw), 1.6, 3.1, max(1, px(1))
            )
            tip = top - dw * 2 // 3
            pygame.draw.line(
                surf,
                PALETTE.poster_gold if near else rim,
                (x + bw // 2, tip + px(2)),
                (x + bw // 2, tip - px(12)),
                max(1, px(1)),
            )
        elif kind < 0.7:
            # Minarete
            mw = max(px(8), bw // 4)
            mx = x + bw // 2 - mw // 2
            mh = rng.randint(px(50), px(110))
            pygame.draw.rect(surf, col, (mx, top - mh, mw, mh))
            pygame.draw.ellipse(surf, col, (mx - px(3), top - mh - mw, mw + px(6), mw * 2))
            pygame.draw.line(surf, rim, (mx, top - mh), (mx, top), 1)
            pygame.draw.rect(surf, col, (mx - px(4), top - mh // 2, mw + px(8), px(4)))
        if near:
            for _ in range(rng.randint(1, 3)):
                wx = x + rng.randint(px(4), max(px(5), bw - px(10)))
                wy = top + rng.randint(px(8), max(px(9), bh - px(14)))
                windows.append((wx, wy, px(4), px(7)))
        x += bw + rng.randint(px(4), px(24))
    # Cúpula central grande (plano cercano)
    if near:
        dw = int(w * 0.22)
        dx = w // 2 - dw // 2
        top = base_y - px(60)
        pygame.draw.rect(surf, col, (dx + px(10), top, dw - px(20), px(64)))
        pygame.draw.ellipse(surf, col, (dx, top - dw * 3 // 5, dw, dw))
        pygame.draw.arc(surf, rim, (dx, top - dw * 3 // 5, dw, dw), 1.7, 3.0, px(2))
        pygame.draw.line(
            surf,
            PALETTE.poster_gold,
            (w // 2, top - dw * 3 // 5),
            (w // 2, top - dw * 3 // 5 - px(24)),
            px(2),
        )
        pygame.draw.circle(surf, PALETTE.poster_gold, (w // 2, top - dw * 3 // 5 - px(26)), px(3))
        for k in range(5):
            windows.append((dx + px(20) + k * (dw - px(40)) // 4, top + px(20), px(5), px(10)))
    return surf, windows


@functools.lru_cache(maxsize=2)
def _skylines(
    w: int, h: int
) -> tuple[pygame.Surface, pygame.Surface, tuple[tuple[int, int, int, int], ...]]:
    far, _ = _skyline(w, h, near=False)
    near, win = _skyline(w, h, near=True)
    return far, near, tuple(win)


@functools.lru_cache(maxsize=2)
def _clouds(w: int, h: int) -> pygame.Surface:
    surf = pygame.Surface((w * 2, h // 2), pygame.SRCALPHA)
    rng = random.Random(33)
    for _ in range(14):
        cw = rng.randint(w // 8, w // 3)
        ch = rng.randint(px(8), px(22))
        x = rng.randint(0, w * 2 - cw)
        y = rng.randint(0, h // 2 - ch)
        pygame.draw.ellipse(surf, (150, 150, 200, rng.randint(14, 34)), (x, y, cw, ch))
    return pygame.transform.box_blur(surf, px(6))


@functools.lru_cache(maxsize=2)
def _stars(w: int, h: int) -> tuple[tuple[int, int, float, float], ...]:
    rng = random.Random(1989)
    out = []
    for _ in range(170):
        out.append(
            (
                rng.randrange(w),
                rng.randrange(int(h * 0.62)),
                rng.uniform(0, math.tau),
                rng.uniform(0.6, 2.4),
            )
        )
    return tuple(out)


@functools.lru_cache(maxsize=2)
def _curtain(w: int, h: int) -> pygame.Surface:
    """Cortina de terciopelo (lado izquierdo) con pliegues sombreados."""
    cw = int(w * 0.36)
    xs = np.arange(cw, dtype=np.float32)[:, None]
    ys = np.arange(h, dtype=np.float32)[None, :]
    folds = 0.62 + 0.38 * np.sin(xs * (math.tau / (cw / 4.6)) + ys * 0.002) ** 2
    edge = np.clip((cw - xs) / (cw * 0.15), 0.35, 1.0)
    shade = folds * edge * (0.75 + 0.25 * (1 - ys / h))
    base = np.array(PALETTE.poster_curtain, dtype=np.float32)
    arr = shade[:, :, None] * base[None, None, :]
    arr += (np.clip(folds - 0.92, 0, 1) * 600)[:, :, None] * np.array(
        (1.0, 0.5, 0.5), dtype=np.float32
    )
    surf = pygame.Surface((cw, h), pygame.SRCALPHA)
    rgb = np.clip(arr, 0, 255).astype(np.uint8)
    pygame.surfarray.blit_array(surf, rgb)
    alpha = pygame.surfarray.pixels_alpha(surf)
    alpha[:] = 255
    del alpha
    # Borde inferior ondulado
    for x in range(cw):
        cut = int(px(10) * (0.5 + 0.5 * math.sin(x * 0.08)))
        pygame.draw.line(surf, (0, 0, 0, 0), (x, h - cut), (x, h))
    # Galón dorado en el borde interior
    pygame.draw.line(surf, PALETTE.poster_gold_dark, (cw - px(5), 0), (cw - px(5), h), px(4))
    pygame.draw.line(surf, PALETTE.poster_gold, (cw - px(4), 0), (cw - px(4), h), px(2))
    return surf


# ---------------------------------------------------------------------------
# Capas animadas
# ---------------------------------------------------------------------------


def _draw_sky(surf: pygame.Surface, t: float) -> None:
    w, h = surf.get_size()
    surf.blit(_sky(w, h), (0, 0))
    for x, y, ph, sp in _stars(w, h):
        b = 0.35 + 0.65 * abs(math.sin(t * sp + ph))
        c = int(90 + 165 * b)
        if b > 0.9:
            surf.fill((c, c, 255), (x - 1, y, 3, 1))
            surf.fill((c, c, 255), (x, y - 1, 1, 3))
        else:
            surf.fill((c, c, min(255, c + 20)), (x, y, max(1, px(1)), max(1, px(1))))
    # Estrella fugaz cada ~7 s
    k = (t % 7.0) / 0.6
    if k < 1.0:
        sx, sy = w * 0.65 + k * w * 0.18, h * 0.08 + k * h * 0.1
        for i in range(12):
            a = (1 - i / 12) * (1 - k)
            pygame.draw.circle(
                surf,
                (int(255 * a), int(255 * a), int(255 * a)),
                (int(sx - i * px(4)), int(sy - i * px(2))),
                max(1, px(1)),
            )


def _draw_palace(surf: pygame.Surface, t: float) -> None:
    w, h = surf.get_size()
    far, near, windows = _skylines(w, h)
    clouds = _clouds(w, h)
    off = int((t * px(6)) % w)
    surf.blit(clouds, (-off, int(h * 0.12)))
    surf.blit(clouds, (w * 2 - off - w, int(h * 0.12)))
    surf.blit(far, (0, 0))
    surf.blit(near, (0, 0))
    for i, (x, y, ww, hh) in enumerate(windows):
        flick = 0.75 + 0.25 * math.sin(t * (2.0 + i % 3) + i)
        col = (int(255 * flick), int(190 * flick), int(90 * flick))
        surf.fill(col, (x, y, ww, hh))


def _draw_curtains(surf: pygame.Surface, rect: pygame.Rect, openness: float = 1.0) -> None:
    w, h = rect.size
    cur = _curtain(w, h)
    cw = cur.get_width()
    # Abiertas: asoma ~50 % de cada cortina; cerradas: se tocan en el centro
    visible = int(cw * (0.5 + 0.9 * (1 - openness)))
    visible = min(visible, w // 2 + px(4))
    surf.blit(cur, (rect.x + visible - cw, rect.y))
    surf.blit(pygame.transform.flip(cur, True, False), (rect.right - visible, rect.y))
    # Cordones con borla
    for side in (-1, 1):
        x = rect.x + visible - px(10) if side < 0 else rect.right - visible + px(10)
        y = rect.y + h // 2
        pygame.draw.line(surf, PALETTE.poster_gold, (x, y), (x - side * px(18), y + px(18)), px(3))
        pygame.draw.circle(surf, PALETTE.poster_gold, (x - side * px(18), y + px(20)), px(5))
        for k in range(-2, 3):
            fx = x - side * px(18) + k * px(2)
            pygame.draw.line(surf, PALETTE.poster_gold_dark, (fx, y + px(24)), (fx, y + px(36)), 1)


def _draw_title(
    surf: pygame.Surface, rect: pygame.Rect, font_big: pygame.font.Font | None, t: float
) -> None:
    """Logo PRINCE OF PERSIA en oro metálico con halo que respira."""
    _ = font_big
    title = fonts.gold_title("PRINCE OF PERSIA", 46, glow=7)
    pulse = 0.88 + 0.12 * abs(math.sin(t * 1.2))
    img = title.copy()
    img.set_alpha(int(255 * min(1.0, pulse + 0.1)))
    surf.blit(img, img.get_rect(center=(rect.centerx, rect.y + rect.height // 8)))


def _actor(
    surf: pygame.Surface,
    frame: int,
    palette: CharPalette,
    facing: int,
    x: int,
    y: int,
    scale: float,
) -> None:
    img, (ax, ay) = sprite(frame, palette, facing)
    if scale != 1.0:
        img = pygame.transform.smoothscale(
            img, (int(img.get_width() * scale), int(img.get_height() * scale))
        )
        ax, ay = int(ax * scale), int(ay * scale)
    else:
        img = img.copy()
    img.fill((150, 156, 210), special_flags=pygame.BLEND_RGB_MULT)
    surf.blit(img, (x - ax, y - ay))


def _draw_silhouettes(surf: pygame.Surface, rect: pygame.Rect, cast: PosterCast) -> None:
    """Personajes en primer plano, bañados por la luz de la luna."""
    base_y = rect.y + rect.height - px(14)
    # Suelo de terraza
    floor = pygame.Rect(rect.x, base_y - px(4), rect.width, rect.bottom - base_y + px(4))
    pygame.draw.rect(surf, (22, 18, 40), floor)
    pygame.draw.line(surf, (90, 96, 150), floor.topleft, floor.topright, px(1))
    if cast.vizier:
        aura = pygame.Surface((px(110), px(130)), pygame.SRCALPHA)
        pygame.draw.ellipse(aura, (*PALETTE.error, 50), aura.get_rect())
        aura = pygame.transform.box_blur(aura, px(10))
        vx, vy = rect.x + rect.width * 3 // 4, rect.y + rect.height * 3 // 5
        surf.blit(aura, (vx - aura.get_width() // 2, vy - px(110)))
        _actor(surf, 15, CharPalette.VIZIER, -1, vx, vy, 1.3)
    if cast.princess:
        _actor(surf, 15, CharPalette.PRINCESS, 0, rect.x + rect.width // 5, base_y, 1.2)
    if cast.prince:
        _actor(surf, 158, CharPalette.KID, 0, rect.x + rect.width // 2, base_y, 1.35)
    if cast.guard:
        _actor(surf, 158, CharPalette.GUARD, -1, rect.x + rect.width * 4 // 5, base_y, 1.2)


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------


def draw_poster(
    surf: pygame.Surface,
    font_big: pygame.font.Font | None = None,
    *,
    t: float = 0.0,
    cast: PosterCast | None = None,
    curtain_openness: float = 1.0,
    show_title: bool = True,
) -> None:
    """Pinta el póster sobre toda la superficie.

    Args:
        surf: superficie destino (pantalla completa).
        font_big: obsoleto (el título usa ``fonts.gold_title``).
        t: tiempo en segundos (estrellas, nubes, ventanas, pulso del oro).
        cast: personajes a incluir (``None`` → princesa, visir y príncipe).
        curtain_openness: 0 cortinas cerradas, 1 abiertas.
        show_title: si dibujar el logo PRINCE OF PERSIA.
    """
    if cast is None:
        cast = PosterCast()
    w, h = surf.get_size()
    full = pygame.Rect(0, 0, w, h)
    _draw_sky(surf, t)
    _draw_palace(surf, t)
    _draw_silhouettes(surf, full, cast)
    _draw_curtains(surf, full, openness=curtain_openness)
    if show_title:
        _draw_title(surf, full, font_big, t)


# ---------------------------------------------------------------------------
# Cast por nivel — qué personajes evocar en el level card de cada nivel
# ---------------------------------------------------------------------------

LEVEL_CASTS: dict[int, PosterCast] = {
    1: PosterCast(princess=False, vizier=True, prince=True, guard=True),
    2: PosterCast(princess=False, vizier=True, prince=True, guard=True),
    3: PosterCast(princess=False, vizier=False, prince=True, guard=False),  # skeleton-only
    4: PosterCast(princess=False, vizier=True, prince=True, guard=False),  # mirror/shadow
    5: PosterCast(princess=False, vizier=True, prince=True, guard=False),
    6: PosterCast(princess=False, vizier=True, prince=True, guard=False),
    7: PosterCast(princess=True, vizier=True, prince=True, guard=True),
    8: PosterCast(princess=True, vizier=True, prince=True, guard=False),
    9: PosterCast(princess=False, vizier=True, prince=True, guard=False),
    10: PosterCast(princess=True, vizier=True, prince=True, guard=True),
    11: PosterCast(princess=True, vizier=True, prince=True, guard=True),
    12: PosterCast(princess=True, vizier=True, prince=True, guard=False),  # vizier finale
    13: PosterCast(princess=True, vizier=False, prince=True, guard=False),  # vizier muerto
    14: PosterCast(princess=True, vizier=False, prince=True, guard=False),  # reunion
}
"""Cast del poster para cada nivel. La presencia/ausencia de personajes
refleja la situación narrativa de ese nivel."""


def cast_for_level(level_number: int) -> PosterCast:
    """Devuelve el cast del poster para ``level_number`` (1..14)."""
    return LEVEL_CASTS.get(level_number, PosterCast())


def draw_backdrop(surf: pygame.Surface, t: float) -> None:
    """Sólo el fondo del póster (cielo, estrellas, nubes y palacio), sin
    personajes ni cortinas: lo usan las cinemáticas."""
    _draw_sky(surf, t)
    _draw_palace(surf, t)
