"""Pared del fondo en HD, generada por sala y cacheada.

Sillares con color propio, bisel (arista clara arriba, sombra abajo),
juntas hundidas con oclusión, textura de grano y manchas de baja
frecuencia (numpy), y detalle por estilo:

- Mazmorra: piedra azul grisácea, grietas, humedad y musgo al pie de
  cada piso, regueros de agua, cadenas y argollas.
- Palacio: arenisca cálida, friso de azulejos, hornacinas lobuladas con
  sombra interior y algún tapiz.

La luz (``fx.Lighting``) multiplica sobre esto: lejos de las antorchas
queda en penumbra, cerca brilla la piedra.
"""

from __future__ import annotations

import functools
import random
from dataclasses import dataclass

import numpy as np
import pygame

from pop2026canon.presentation.layout import LAYOUT, px

RGB = tuple[int, int, int]


@dataclass(frozen=True, slots=True)
class _Pal:
    stone: RGB
    stone_var: int
    mortar: RGB
    hi: RGB
    accent: RGB


_DUNGEON = _Pal(
    stone=(92, 94, 122),
    stone_var=12,
    mortar=(30, 30, 44),
    hi=(140, 142, 170),
    accent=(46, 74, 48),
)
_PALACE = _Pal(
    stone=(150, 124, 102),
    stone_var=12,
    mortar=(66, 48, 40),
    hi=(186, 160, 132),
    accent=(40, 84, 130),
)


def _blocks(arr: np.ndarray, pal: _Pal, rng: random.Random, w: int, h: int) -> None:
    """Sillares en ``arr`` (float, forma (w, h, 3))."""
    row_h = px(21)
    bev = max(1, px(1))
    stone = np.array(pal.stone, dtype=np.float32)
    y = 0
    row = 0
    while y < h:
        x = -rng.randint(0, px(30)) if row % 2 else 0
        while x < w:
            bw = rng.randint(px(34), px(60))
            x0, x1 = max(0, x + bev), min(w, x + bw - bev)
            y0, y1 = y + bev, min(h, y + row_h - bev)
            if x1 > x0 and y1 > y0:
                v = rng.uniform(-pal.stone_var, pal.stone_var)
                warm = rng.uniform(-4, 4)
                base = stone + np.array([v + warm, v, v - warm], dtype=np.float32)
                # Degradado vertical dentro del sillar (cara algo abombada)
                grad = np.linspace(1.08, 0.9, y1 - y0, dtype=np.float32)[None, :, None]
                arr[x0:x1, y0:y1] = base[None, None, :] * grad
                # Bisel: arriba e izquierda claros, abajo y derecha oscuros
                arr[x0:x1, y0 : y0 + bev] *= 1.22
                arr[x0 : x0 + bev, y0:y1] *= 1.1
                arr[x0:x1, y1 - bev : y1] *= 0.68
                arr[x1 - bev : x1, y0:y1] *= 0.8
            x += bw
        y += row_h
        row += 1


def _noise(rng: np.random.Generator, w: int, h: int, cell: int) -> np.ndarray:
    """Ruido suave (bilineal) de media 0 y varianza ~1, forma (w, h)."""
    gw, gh = w // cell + 2, h // cell + 2
    g = rng.normal(0.0, 1.0, (gw, gh)).astype(np.float32)
    xs = np.linspace(0, gw - 1.001, w, dtype=np.float32)
    ys = np.linspace(0, gh - 1.001, h, dtype=np.float32)
    x0 = xs.astype(np.int32)
    y0 = ys.astype(np.int32)
    fx = (xs - x0)[:, None]
    fy = (ys - y0)[None, :]
    a = g[x0][:, y0]
    b = g[x0 + 1][:, y0]
    c = g[x0][:, y0 + 1]
    d = g[x0 + 1][:, y0 + 1]
    out: np.ndarray = (
        a * (1 - fx) * (1 - fy) + b * fx * (1 - fy) + c * (1 - fx) * fy + d * fx * fy
    ).astype(np.float32)
    return out


@functools.lru_cache(maxsize=24)
def backdrop(room_id: int, palace: bool) -> pygame.Surface:
    """Superficie del ancho de la sala y alto del mundo (sin HUD)."""
    w, h = LAYOUT.window_w, LAYOUT.room_h
    pal = _PALACE if palace else _DUNGEON
    seed = room_id * 7919 + (1 if palace else 0)
    rng = random.Random(seed)
    nrng = np.random.default_rng(seed)
    arr = np.empty((w, h, 3), dtype=np.float32)
    arr[:] = np.array(pal.mortar, dtype=np.float32)
    _blocks(arr, pal, rng, w, h)
    # Manchas grandes + grano fino
    blotch = _noise(nrng, w, h, px(40))
    grain = nrng.normal(0.0, 1.0, (w, h)).astype(np.float32)
    arr *= (1.0 + 0.07 * blotch)[:, :, None]
    arr += (grain * 5.0)[:, :, None]
    # Oscurecer lo alto de cada piso (el techo/losa de arriba hace sombra)
    th = LAYOUT.tile_h
    yy = np.arange(h, dtype=np.float32) % th
    ceiling = 1.0 - 0.28 * np.clip(1.0 - yy / px(40), 0.0, 1.0) ** 2
    arr *= ceiling[None, :, None]
    if not palace:
        # Humedad: manchas verdosas al pie de cada piso
        damp = np.clip(_noise(nrng, w, h, px(18)), 0.0, None)
        foot = np.clip((yy - (th - px(60))) / px(60), 0.0, 1.0) ** 2
        k = (damp * foot[None, :] * 0.5)[:, :, None]
        arr = arr * (1 - k) + np.array(pal.accent, dtype=np.float32)[None, None, :] * k
    np.clip(arr, 0, 255, out=arr)
    surf = pygame.Surface((w, h))
    pygame.surfarray.blit_array(surf, arr.astype(np.uint8))
    if palace:
        _palace_details(surf, pal, rng, w)
    else:
        _dungeon_details(surf, pal, rng, w, h)
    return surf


def _dungeon_details(surf: pygame.Surface, pal: _Pal, rng: random.Random, w: int, h: int) -> None:
    th = LAYOUT.tile_h
    # Grietas ramificadas
    for _ in range(rng.randint(2, 4)):
        cx, cy = rng.randint(px(20), w - px(20)), rng.randint(px(20), h - px(60))
        pts = [(cx, cy)]
        for _ in range(rng.randint(4, 8)):
            cx += rng.randint(-px(8), px(8))
            cy += rng.randint(px(4), px(12))
            pts.append((cx, cy))
        pygame.draw.lines(surf, pal.mortar, False, pts, px(1))
        pygame.draw.lines(surf, pal.hi, False, [(x + 1, y + 1) for x, y in pts], 1)
    # Regueros de agua
    streaks = pygame.Surface((w, h), pygame.SRCALPHA)
    for _ in range(rng.randint(1, 3)):
        sx = rng.randint(0, w)
        top = rng.choice((0, th, 2 * th)) + px(4)
        length = rng.randint(px(40), px(100))
        for i in range(length):
            a = int(46 * (1 - i / length))
            pygame.draw.line(streaks, (10, 14, 24, a), (sx - px(2), top + i), (sx + px(2), top + i))
    surf.blit(streaks, (0, 0))
    # Musgo al pie de cada piso
    for floor in range(3):
        base_y = (floor + 1) * th - px(28)
        for _ in range(rng.randint(5, 10)):
            mx = rng.randint(0, w)
            for _k in range(rng.randint(6, 16)):
                r = rng.randint(1, px(2))
                pygame.draw.circle(
                    surf,
                    (
                        pal.accent[0] + rng.randint(-8, 14),
                        pal.accent[1] + rng.randint(-8, 20),
                        pal.accent[2],
                    ),
                    (mx + rng.randint(-px(8), px(8)), base_y - rng.randint(0, px(8))),
                    r,
                )
    # Cadenas y argollas
    if rng.random() < 0.55:
        cx = rng.randint(px(40), w - px(40))
        length = rng.randint(px(40), px(90))
        for i, yy in enumerate(range(0, length, px(6))):
            rect = (cx - px(2), yy, px(5), px(7)) if i % 2 else (cx - px(1), yy, px(3), px(7))
            pygame.draw.ellipse(surf, (34, 34, 42), rect, max(1, px(1)))
            pygame.draw.ellipse(surf, (96, 96, 110), (rect[0], rect[1], rect[2], rect[3] // 2), 1)
    if rng.random() < 0.6:
        rx = rng.randint(px(30), w - px(30))
        ry = rng.choice((0, 1, 2)) * th + px(60)
        pygame.draw.rect(surf, (40, 40, 50), (rx - px(4), ry - px(3), px(8), px(6)))
        pygame.draw.circle(surf, (28, 28, 36), (rx, ry + px(9)), px(7), px(2))
        pygame.draw.arc(
            surf, (110, 110, 126), (rx - px(7), ry + px(2), px(14), px(14)), 2.4, 3.6, 1
        )


def _palace_details(surf: pygame.Surface, pal: _Pal, rng: random.Random, w: int) -> None:
    th = LAYOUT.tile_h
    for floor in range(3):
        # Hornacinas lobuladas con sombra interior
        for i in range(0, LAYOUT.room_cols, 2):
            ax = i * LAYOUT.tile_w + px(16)
            ay = floor * th + px(52)
            rect = pygame.Rect(ax, ay, LAYOUT.tile_w * 2 - px(32), th - px(84))
            niche = pygame.Surface(rect.size, pygame.SRCALPHA)
            for yy in range(rect.h):
                a = int(150 - 70 * yy / rect.h)
                pygame.draw.line(niche, (30, 18, 16, a), (0, yy), (rect.w, yy))
            mask = pygame.Surface(rect.size, pygame.SRCALPHA)
            radius = rect.w // 2
            pygame.draw.rect(
                mask,
                (255, 255, 255, 255),
                mask.get_rect(),
                border_top_left_radius=radius,
                border_top_right_radius=radius,
            )
            niche.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            surf.blit(niche, rect)
            pygame.draw.rect(
                surf,
                pal.hi,
                rect,
                px(2),
                border_top_left_radius=radius,
                border_top_right_radius=radius,
            )
            # Lóbulos del arco
            for k in (-1, 0, 1):
                pygame.draw.circle(
                    surf, pal.hi, (rect.centerx + k * rect.w // 4, rect.top + px(6)), px(6), px(1)
                )
        # Friso de azulejos
        band_y = floor * th + px(28)
        band_h = px(14)
        pygame.draw.rect(surf, (54, 40, 36), (0, band_y, w, band_h))
        pygame.draw.line(surf, (220, 186, 90), (0, band_y), (w, band_y), px(1))
        pygame.draw.line(surf, (220, 186, 90), (0, band_y + band_h), (w, band_y + band_h), px(1))
        step = px(16)
        for bx in range(0, w, step):
            c = pal.accent if (bx // step) % 2 == 0 else (196, 150, 64)
            cx, cy = bx + step // 2, band_y + band_h // 2
            d = band_h // 2 - px(1)
            pygame.draw.polygon(surf, c, [(cx, cy - d), (cx + d, cy), (cx, cy + d), (cx - d, cy)])
            pygame.draw.circle(surf, (240, 228, 200), (cx, cy), max(1, px(1)))
    # Tapiz
    if rng.random() < 0.45:
        tx = rng.randint(1, LAYOUT.room_cols - 2) * LAYOUT.tile_w + px(8)
        ty = rng.randint(0, 2) * th + px(46)
        tw, tht = px(44), px(84)
        for yy in range(tht):
            fade = yy / tht
            pygame.draw.line(
                surf,
                (int(130 - 40 * fade), int(22 - 6 * fade), int(36 - 8 * fade)),
                (tx, ty + yy),
                (tx + tw, ty + yy),
            )
        for k in range(1, 4):
            pygame.draw.line(
                surf,
                (200, 160, 70),
                (tx + px(4), ty + tht * k // 4),
                (tx + tw - px(4), ty + tht * k // 4),
                px(1),
            )
        pygame.draw.rect(surf, (220, 180, 80), (tx, ty, tw, tht), px(2))
        pygame.draw.line(surf, (60, 40, 30), (tx - px(4), ty), (tx + tw + px(4), ty), px(3))
        for fx in range(tx + px(2), tx + tw, px(5)):
            pygame.draw.line(surf, (220, 180, 80), (fx, ty + tht), (fx, ty + tht + px(6)), 1)
