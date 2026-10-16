"""Pared del fondo en HD, generada por sala y tema de nivel, y cacheada.

Mampostería según el tema (sillares, roca viva, mármol con vetas o
ladrillo), con bisel, grano y manchas (numpy), sombra bajo cada techo y
humedad al pie. Encima, la decoración propia del nivel (``themes``):
grietas, regueros, musgo, cadenas, telarañas, huesos y hornacinas con
calaveras, estalactitas, raíces, cristales luminosos, ventanas con el
cielo de fuera, hornacinas lobuladas, frisos de azulejos, tapices,
estandartes del visir, velas, jeroglíficos, cascotes, rosas...

Las piezas que dan luz (velas, cristales, ventanas) se colocan con
``decor_spots``, que también usa ``fx.Lighting``: la luz cae justo donde
está dibujada la pieza.

La luz (``fx.Lighting``) multiplica sobre esto: lejos de las antorchas
queda en penumbra, cerca brilla la piedra. Además, ``backdrop`` recibe
las luces fijas de la sala (antorchas, velas, cristales, ventanas) y
**hornea** su luz con relieve: de la propia mampostería se deriva un
mapa de normales (gradiente de la luminancia) y cada sillar recibe luz
difusa según mire o no hacia la antorcha — bordes que brillan por el
lado de la llama y se apagan por el otro, como un *normal map* de un
juego actual. Se calcula una vez por sala y se cachea.
"""

from __future__ import annotations

import functools
import math
import random
from collections.abc import Callable

import numpy as np
import pygame

from pop2026canon.presentation.layout import LAYOUT, px
from pop2026canon.presentation.themes import LevelTheme, theme_by_key

RGB = tuple[int, int, int]

LIGHT_DECOR: frozenset[str] = frozenset({"candles", "crystals", "windows"})


# ---------------------------------------------------------------------------
# Mampostería
# ---------------------------------------------------------------------------


def _blocks(
    arr: np.ndarray, th: LevelTheme, rng: random.Random, w: int, h: int, *, brick: bool
) -> None:
    """Sillares (o ladrillos) en ``arr`` (float, forma (w, h, 3))."""
    row_h = px(14) if brick else px(21)
    widths = (px(26), px(34)) if brick else (px(34), px(60))
    bev = max(1, px(1))
    stone = np.array(th.stone, dtype=np.float32)
    y = 0
    row = 0
    while y < h:
        x = -rng.randint(0, widths[1] // 2) if row % 2 else 0
        while x < w:
            bw = rng.randint(*widths)
            x0, x1 = max(0, x + bev), min(w, x + bw - bev)
            y0, y1 = y + bev, min(h, y + row_h - bev)
            if x1 > x0 and y1 > y0:
                v = rng.uniform(-th.stone_var, th.stone_var)
                warm = rng.uniform(-4, 4)
                base = stone + np.array([v + warm, v, v - warm], dtype=np.float32)
                grad = np.linspace(1.08, 0.9, y1 - y0, dtype=np.float32)[None, :, None]
                arr[x0:x1, y0:y1] = base[None, None, :] * grad
                arr[x0:x1, y0 : y0 + bev] *= 1.22
                arr[x0 : x0 + bev, y0:y1] *= 1.1
                arr[x0:x1, y1 - bev : y1] *= 0.68
                arr[x1 - bev : x1, y0:y1] *= 0.8
            x += bw
        y += row_h
        row += 1


def _marble(arr: np.ndarray, th: LevelTheme, rng: random.Random, w: int, h: int) -> None:
    """Grandes placas de mármol pulido (juntas finas, bisel suave)."""
    stone = np.array(th.stone, dtype=np.float32)
    row_h = px(42)
    y = 0
    row = 0
    while y < h:
        x = -px(40) if row % 2 else 0
        while x < w:
            bw = px(84)
            x0, x1 = max(0, x + 1), min(w, x + bw - 1)
            y0, y1 = y + 1, min(h, y + row_h - 1)
            if x1 > x0 and y1 > y0:
                v = rng.uniform(-th.stone_var * 0.6, th.stone_var * 0.6)
                base = stone + v
                grad = np.linspace(1.06, 0.94, y1 - y0, dtype=np.float32)[None, :, None]
                arr[x0:x1, y0:y1] = base[None, None, :] * grad
                arr[x0:x1, y0 : y0 + 1] *= 1.18
                arr[x0:x1, y1 - 1 : y1] *= 0.8
            x += bw
        y += row_h
        row += 1


def _rough(arr: np.ndarray, th: LevelTheme, nrng: np.random.Generator, w: int, h: int) -> None:
    """Roca viva: relieve por ruido a dos escalas, con grietas oscuras."""
    stone = np.array(th.stone, dtype=np.float32)
    big = _noise(nrng, w, h, px(56))
    mid = _noise(nrng, w, h, px(18))
    relief = 0.85 + 0.16 * big + 0.1 * mid
    # Sombreado direccional del relieve (luz de arriba a la izquierda)
    shade = np.zeros_like(relief)
    shade[1:, 1:] = (relief[1:, 1:] - relief[:-1, :-1]) * 3.5
    k = np.clip(relief + shade, 0.45, 1.35)
    arr[:] = stone[None, None, :] * k[:, :, None]
    seams = np.abs(_noise(nrng, w, h, px(30))) < 0.035
    arr[seams] *= 0.72


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


# ---------------------------------------------------------------------------
# Colocación determinista de la decoración
# ---------------------------------------------------------------------------


def _seed(room_id: int, key: str, name: str) -> int:
    h = 2166136261
    for ch in f"{room_id}:{key}:{name}":
        h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return h


@functools.lru_cache(maxsize=512)
def decor_spots(room_id: int, theme_key: str, name: str) -> tuple[tuple[int, int], ...]:
    """Puntos (x, fila) donde va una pieza de decoración en la sala —
    deterministas, y compartidos por el dibujo y por la iluminación."""
    th = theme_by_key(theme_key)
    if name not in th.decor:
        return ()
    rng = random.Random(_seed(room_id, theme_key, name))
    counts = {
        "candles": (1, 3),
        "crystals": (2, 4),
        "windows": (1, 2),
        "banners": (1, 2),
        "skull_niches": (1, 3),
        "tapestry": (0, 1),
        "cobwebs": (2, 4),
        "bones": (1, 3),
    }
    lo, hi = counts.get(name, (1, 3))
    n = rng.randint(lo, hi)
    cols = rng.sample(range(LAYOUT.room_cols), k=min(n, LAYOUT.room_cols))
    top_row = 1 if name in ("windows", "banners", "tapestry") else 2
    return tuple(
        (
            c * LAYOUT.tile_w + LAYOUT.tile_w // 2 + rng.randint(-px(10), px(10)),
            rng.randint(0, top_row),
        )
        for c in sorted(cols)
    )


def decor_lights(room_id: int, theme_key: str) -> tuple[tuple[int, int, int, RGB], ...]:
    """Luces de la decoración ``(x, y, radio, color)`` en coordenadas del
    mundo (y desde lo alto de la sala, sin HUD)."""
    th = theme_by_key(theme_key)
    out: list[tuple[int, int, int, RGB]] = []
    tile_h = LAYOUT.tile_h
    for x, row in decor_spots(room_id, theme_key, "candles"):
        out.append((x, row * tile_h + px(70), px(70), (255, 170, 80)))
    for x, row in decor_spots(room_id, theme_key, "crystals"):
        out.append((x, (row + 1) * tile_h - px(44), px(60), (60, 200, 210)))
    sky = _SKY_LIGHT.get(th.sky, (90, 100, 150))
    for x, row in decor_spots(room_id, theme_key, "windows"):
        out.append(
            (x, row * tile_h + px(58), px(90), (sky[0] * 3 // 4, sky[1] * 3 // 4, sky[2] * 3 // 4))
        )
    return tuple(out)


_SKY_LIGHT: dict[str, RGB] = {
    "night": (70, 84, 140),
    "moon": (110, 124, 180),
    "dusk": (190, 110, 90),
    "dawn": (210, 150, 120),
}


# ---------------------------------------------------------------------------
# Decoración
# ---------------------------------------------------------------------------

Decor = Callable[[pygame.Surface, LevelTheme, int, random.Random], None]


def _cracks(surf: pygame.Surface, th: LevelTheme, room: int, rng: random.Random) -> None:
    w, h = surf.get_size()
    for _ in range(rng.randint(2, 4)):
        cx, cy = rng.randint(px(20), w - px(20)), rng.randint(px(20), h - px(60))
        pts = [(cx, cy)]
        for _ in range(rng.randint(4, 8)):
            cx += rng.randint(-px(8), px(8))
            cy += rng.randint(px(4), px(12))
            pts.append((cx, cy))
        pygame.draw.lines(surf, th.mortar, False, pts, px(1))
        pygame.draw.lines(surf, th.hi, False, [(x + 1, y + 1) for x, y in pts], 1)


def _streaks(surf: pygame.Surface, th: LevelTheme, room: int, rng: random.Random) -> None:
    w, h = surf.get_size()
    tile_h = LAYOUT.tile_h
    layer = pygame.Surface((w, h), pygame.SRCALPHA)
    for _ in range(rng.randint(1, 3)):
        sx = rng.randint(0, w)
        top = rng.choice((0, tile_h, 2 * tile_h)) + px(4)
        length = rng.randint(px(40), px(100))
        for i in range(length):
            a = int(46 * (1 - i / length))
            pygame.draw.line(layer, (10, 14, 24, a), (sx - px(2), top + i), (sx + px(2), top + i))
    surf.blit(layer, (0, 0))


def _moss(surf: pygame.Surface, th: LevelTheme, room: int, rng: random.Random) -> None:
    w, _ = surf.get_size()
    for floor in range(3):
        base_y = (floor + 1) * LAYOUT.tile_h - px(28)
        for _ in range(rng.randint(5, 10)):
            mx = rng.randint(0, w)
            for _k in range(rng.randint(6, 16)):
                pygame.draw.circle(
                    surf,
                    (
                        min(255, th.accent[0] + rng.randint(-8, 14)),
                        min(255, th.accent[1] + rng.randint(-8, 20)),
                        th.accent[2],
                    ),
                    (mx + rng.randint(-px(8), px(8)), base_y - rng.randint(0, px(8))),
                    rng.randint(1, px(2)),
                )


def _chains(surf: pygame.Surface, th: LevelTheme, room: int, rng: random.Random) -> None:
    w, _ = surf.get_size()
    if rng.random() < 0.6:
        cx = rng.randint(px(40), w - px(40))
        top = rng.choice((0, 1, 2)) * LAYOUT.tile_h
        length = rng.randint(px(40), px(90))
        for i, yy in enumerate(range(0, length, px(6))):
            rect = (
                (cx - px(2), top + yy, px(5), px(7))
                if i % 2
                else (cx - px(1), top + yy, px(3), px(7))
            )
            pygame.draw.ellipse(surf, (34, 34, 42), rect, max(1, px(1)))
            pygame.draw.ellipse(surf, (96, 96, 110), (rect[0], rect[1], rect[2], rect[3] // 2), 1)


def _rings(surf: pygame.Surface, th: LevelTheme, room: int, rng: random.Random) -> None:
    w, _ = surf.get_size()
    if rng.random() < 0.6:
        rx = rng.randint(px(30), w - px(30))
        ry = rng.choice((0, 1, 2)) * LAYOUT.tile_h + px(60)
        pygame.draw.rect(surf, (40, 40, 50), (rx - px(4), ry - px(3), px(8), px(6)))
        pygame.draw.circle(surf, (28, 28, 36), (rx, ry + px(9)), px(7), px(2))
        pygame.draw.arc(
            surf, (110, 110, 126), (rx - px(7), ry + px(2), px(14), px(14)), 2.4, 3.6, 1
        )


def _cobwebs(surf: pygame.Surface, th: LevelTheme, room: int, rng: random.Random) -> None:
    """Telarañas tendidas en el ángulo del techo de cada piso."""
    silk = (200, 204, 210)
    layer = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    for x, row in decor_spots(room, th.key, "cobwebs"):
        top = row * LAYOUT.tile_h
        r = rng.randint(px(26), px(42))
        side = rng.choice((-1, 1))
        ox = x - side * r // 2
        spokes = [math.radians(a) for a in range(0, 91, 18)]
        ends = []
        for a in spokes:
            ex = ox + side * int(math.cos(a) * r)
            ey = top + int(math.sin(a) * r)
            ends.append((ex, ey))
            pygame.draw.line(layer, (*silk, 70), (ox, top), (ex, ey), 1)
        for k in (0.35, 0.6, 0.85):
            pts = [(ox + (ex - ox) * k, top + (ey - top) * k) for ex, ey in ends]
            pygame.draw.lines(layer, (*silk, 60), False, pts, 1)
    surf.blit(layer, (0, 0))


def _bone(surf: pygame.Surface, x: int, y: int, length: int, angle: float, col: RGB) -> None:
    dx, dy = math.cos(angle) * length / 2, math.sin(angle) * length / 2
    a, b = (x - dx, y - dy), (x + dx, y + dy)
    pygame.draw.line(surf, col, a, b, px(2))
    for p in (a, b):
        pygame.draw.circle(surf, col, (int(p[0]), int(p[1])), px(2))


def _skull(surf: pygame.Surface, x: int, y: int, r: int, bone: RGB) -> None:
    pygame.draw.circle(surf, bone, (x, y), r)
    pygame.draw.rect(surf, bone, (x - r * 2 // 3, y, r * 4 // 3, r * 3 // 4))
    for s in (-1, 1):
        pygame.draw.circle(surf, (20, 14, 14), (x + s * r // 3, y), max(1, r // 3))
    pygame.draw.line(surf, (40, 30, 26), (x, y + r // 3), (x, y + r // 2), 1)


def _bones(surf: pygame.Surface, th: LevelTheme, room: int, rng: random.Random) -> None:
    """Huesos amontonados al pie de la pared (asoman sobre la losa)."""
    bone = (196, 190, 168)
    for x, row in decor_spots(room, th.key, "bones"):
        base = (row + 1) * LAYOUT.tile_h - LAYOUT.floor_face - LAYOUT.floor_top
        for _ in range(rng.randint(3, 6)):
            _bone(
                surf,
                x + rng.randint(-px(18), px(18)),
                base - rng.randint(px(1), px(6)),
                rng.randint(px(10), px(18)),
                rng.uniform(-0.5, 0.5),
                bone,
            )
        if rng.random() < 0.7:
            _skull(surf, x + rng.randint(-px(10), px(10)), base - px(8), px(5), bone)


def _skull_niches(surf: pygame.Surface, th: LevelTheme, room: int, rng: random.Random) -> None:
    """Nichos funerarios con calaveras (osario / tumba)."""
    bone = (206, 198, 176)
    for x, row in decor_spots(room, th.key, "skull_niches"):
        top = row * LAYOUT.tile_h + px(46)
        rect = pygame.Rect(x - px(26), top, px(52), px(30))
        pygame.draw.rect(
            surf, (18, 14, 14), rect, border_top_left_radius=px(14), border_top_right_radius=px(14)
        )
        pygame.draw.rect(
            surf, th.hi, rect, px(1), border_top_left_radius=px(14), border_top_right_radius=px(14)
        )
        for k in (-1, 0, 1):
            _skull(surf, x + k * px(14), top + px(18), px(5), bone)


def _stalactites(surf: pygame.Surface, th: LevelTheme, room: int, rng: random.Random) -> None:
    w, _ = surf.get_size()
    for row in range(3):
        top = row * LAYOUT.tile_h
        x = rng.randint(0, px(30))
        while x < w:
            length = rng.randint(px(10), px(46))
            half = rng.randint(px(4), px(9))
            col = tuple(min(255, int(c * rng.uniform(0.85, 1.15))) for c in th.stone)
            pygame.draw.polygon(
                surf,
                col,
                [(x - half, top), (x + half, top), (x + rng.randint(-px(2), px(2)), top + length)],
            )
            pygame.draw.line(surf, th.hi, (x - half + px(1), top), (x, top + length - px(2)), 1)
            x += rng.randint(px(16), px(60))


def _roots(surf: pygame.Surface, th: LevelTheme, room: int, rng: random.Random) -> None:
    w, _ = surf.get_size()
    col = (62, 46, 30)
    for _ in range(rng.randint(2, 5)):
        x = rng.randint(0, w)
        y = rng.choice((0, 1, 2)) * LAYOUT.tile_h
        pts = [(x, y)]
        for _ in range(rng.randint(5, 10)):
            x += rng.randint(-px(6), px(6))
            y += rng.randint(px(5), px(12))
            pts.append((x, y))
        pygame.draw.lines(surf, col, False, pts, px(2))
        pygame.draw.lines(surf, (96, 74, 50), False, [(a + 1, b) for a, b in pts], 1)


def _crystals(surf: pygame.Surface, th: LevelTheme, room: int, rng: random.Random) -> None:
    for x, row in decor_spots(room, th.key, "crystals"):
        base = (row + 1) * LAYOUT.tile_h - px(30)
        for _ in range(rng.randint(3, 5)):
            h = rng.randint(px(12), px(26))
            wd = rng.randint(px(4), px(7))
            cx = x + rng.randint(-px(10), px(10))
            lean = rng.randint(-px(5), px(5))
            pts = [(cx - wd, base), (cx + lean, base - h), (cx + wd, base)]
            pygame.draw.polygon(surf, (50, 170, 190), pts)
            pygame.draw.polygon(
                surf, (150, 240, 250), [(cx - wd // 3, base), (cx + lean, base - h), (cx, base)]
            )
            pygame.draw.polygon(surf, (20, 70, 90), pts, 1)


def _sky_colors(sky: str) -> tuple[RGB, RGB]:
    return {
        "night": ((10, 14, 46), (36, 44, 100)),
        "moon": ((16, 22, 64), (60, 70, 140)),
        "dusk": ((60, 34, 80), (230, 120, 80)),
        "dawn": ((70, 90, 160), (250, 170, 130)),
    }.get(sky, ((10, 14, 46), (36, 44, 100)))


def _windows(surf: pygame.Surface, th: LevelTheme, room: int, rng: random.Random) -> None:
    """Ventanas en arco abiertas al cielo del nivel (noche, luna, alba)."""
    top_c, low_c = _sky_colors(th.sky)
    for x, row in decor_spots(room, th.key, "windows"):
        rect = pygame.Rect(x - px(20), row * LAYOUT.tile_h + px(30), px(40), px(66))
        win = pygame.Surface(rect.size)
        for yy in range(rect.h):
            k = yy / rect.h
            pygame.draw.line(
                win,
                tuple(int(top_c[i] + (low_c[i] - top_c[i]) * k) for i in range(3)),
                (0, yy),
                (rect.w, yy),
            )
        for _ in range(8):
            win.fill((230, 230, 255), (rng.randrange(rect.w), rng.randrange(rect.h * 2 // 3), 2, 2))
        if th.sky == "moon" and rng.random() < 0.7:
            pygame.draw.circle(win, (244, 236, 200), (rect.w * 2 // 3, rect.h // 3), px(7))
        if th.sky in ("dawn", "dusk"):
            # Silueta lejana de cúpulas recortada contra el alba
            pygame.draw.ellipse(win, (50, 34, 50), (-px(4), rect.h - px(16), px(26), px(26)))
            pygame.draw.rect(win, (50, 34, 50), (0, rect.h - px(6), rect.w, px(6)))
        mask = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(
            mask,
            (255, 255, 255, 255),
            mask.get_rect(),
            border_top_left_radius=rect.w // 2,
            border_top_right_radius=rect.w // 2,
        )
        win_a = pygame.Surface(rect.size, pygame.SRCALPHA)
        win_a.blit(win, (0, 0))
        win_a.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
        surf.blit(win_a, rect)
        pygame.draw.rect(
            surf,
            th.hi,
            rect.inflate(px(6), px(6)),
            px(3),
            border_top_left_radius=rect.w // 2 + px(3),
            border_top_right_radius=rect.w // 2 + px(3),
        )
        # Parteluz y alféizar
        pygame.draw.line(
            surf, th.hi, (rect.centerx, rect.top + px(12)), (rect.centerx, rect.bottom), px(2)
        )
        pygame.draw.rect(surf, th.hi, (rect.x - px(6), rect.bottom, rect.w + px(12), px(5)))


def _niches(surf: pygame.Surface, th: LevelTheme, room: int, rng: random.Random) -> None:
    tile_h = LAYOUT.tile_h
    for floor in range(3):
        for i in range(0, LAYOUT.room_cols, 2):
            ax = i * LAYOUT.tile_w + px(16)
            ay = floor * tile_h + px(52)
            rect = pygame.Rect(ax, ay, LAYOUT.tile_w * 2 - px(32), tile_h - px(84))
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
                th.hi,
                rect,
                px(2),
                border_top_left_radius=radius,
                border_top_right_radius=radius,
            )
            for k in (-1, 0, 1):
                pygame.draw.circle(
                    surf, th.hi, (rect.centerx + k * rect.w // 4, rect.top + px(6)), px(6), px(1)
                )


def _tile_band(surf: pygame.Surface, th: LevelTheme, room: int, rng: random.Random) -> None:
    w, _ = surf.get_size()
    for floor in range(3):
        band_y = floor * LAYOUT.tile_h + px(28)
        band_h = px(14)
        pygame.draw.rect(surf, (54, 40, 36), (0, band_y, w, band_h))
        pygame.draw.line(surf, (220, 186, 90), (0, band_y), (w, band_y), px(1))
        pygame.draw.line(surf, (220, 186, 90), (0, band_y + band_h), (w, band_y + band_h), px(1))
        step = px(16)
        for bx in range(0, w, step):
            c = th.accent if (bx // step) % 2 == 0 else (196, 150, 64)
            cx, cy = bx + step // 2, band_y + band_h // 2
            d = band_h // 2 - px(1)
            pygame.draw.polygon(surf, c, [(cx, cy - d), (cx + d, cy), (cx, cy + d), (cx - d, cy)])
            pygame.draw.circle(surf, (240, 228, 200), (cx, cy), max(1, px(1)))


def _hanging_cloth(
    surf: pygame.Surface, x: int, y: int, w: int, h: int, base: RGB, trim: RGB, emblem: bool
) -> None:
    for yy in range(h):
        fade = yy / h
        col = tuple(max(0, int(c * (1 - 0.35 * fade))) for c in base)
        pygame.draw.line(surf, col, (x, y + yy), (x + w, y + yy))
    for k in range(1, 4):
        pygame.draw.line(
            surf, trim, (x + px(4), y + h * k // 4), (x + w - px(4), y + h * k // 4), px(1)
        )
    pygame.draw.rect(surf, trim, (x, y, w, h), px(2))
    pygame.draw.line(surf, (60, 40, 30), (x - px(4), y), (x + w + px(4), y), px(3))
    for fx in range(x + px(2), x + w, px(5)):
        pygame.draw.line(surf, trim, (fx, y + h), (fx, y + h + px(6)), 1)
    if emblem:
        cx, cy = x + w // 2, y + h // 3
        pygame.draw.circle(surf, trim, (cx, cy), px(9))
        pygame.draw.circle(surf, base, (cx + px(4), cy - px(2)), px(8))
        pygame.draw.polygon(
            surf,
            trim,
            [(cx + px(5), cy - px(3)), (cx + px(7), cy + px(1)), (cx + px(3), cy + px(1))],
        )


def _tapestry(surf: pygame.Surface, th: LevelTheme, room: int, rng: random.Random) -> None:
    for x, row in decor_spots(room, th.key, "tapestry"):
        _hanging_cloth(
            surf,
            x - px(22),
            row * LAYOUT.tile_h + px(46),
            px(44),
            px(84),
            (130, 22, 36),
            (220, 180, 80),
            False,
        )


def _banners(surf: pygame.Surface, th: LevelTheme, room: int, rng: random.Random) -> None:
    """Estandartes del visir: carmesí con la media luna dorada."""
    for x, row in decor_spots(room, th.key, "banners"):
        _hanging_cloth(
            surf,
            x - px(18),
            row * LAYOUT.tile_h + px(20),
            px(36),
            px(110),
            (120, 14, 30),
            (230, 186, 70),
            True,
        )


def _candles(surf: pygame.Surface, th: LevelTheme, room: int, rng: random.Random) -> None:
    for x, row in decor_spots(room, th.key, "candles"):
        y = row * LAYOUT.tile_h + px(80)
        pygame.draw.rect(surf, (90, 70, 40), (x - px(10), y, px(20), px(4)))
        pygame.draw.line(surf, (90, 70, 40), (x, y), (x, y + px(10)), px(2))
        for k in (-1, 0, 1):
            cx = x + k * px(7)
            h = px(10) if k else px(14)
            pygame.draw.rect(surf, (236, 226, 200), (cx - px(2), y - h, px(4), h))
            pygame.draw.polygon(
                surf,
                (255, 200, 90),
                [(cx - px(2), y - h), (cx, y - h - px(6)), (cx + px(2), y - h)],
            )
            pygame.draw.circle(surf, (255, 250, 210), (cx, y - h - px(2)), max(1, px(1)))


def _glyphs(surf: pygame.Surface, th: LevelTheme, room: int, rng: random.Random) -> None:
    """Friso de signos tallados (tumba)."""
    w, _ = surf.get_size()
    col = tuple(max(0, int(c * 0.55)) for c in th.stone)
    hi = th.hi
    for floor in range(3):
        y0 = floor * LAYOUT.tile_h + px(26)
        pygame.draw.line(surf, hi, (0, y0), (w, y0), px(1))
        pygame.draw.line(surf, hi, (0, y0 + px(26)), (w, y0 + px(26)), px(1))
        x = px(6)
        while x < w - px(10):
            kind = rng.randrange(5)
            cx, cy = x + px(6), y0 + px(13)
            if kind == 0:
                pygame.draw.circle(surf, col, (cx, cy), px(5), px(2))
            elif kind == 1:
                pygame.draw.line(surf, col, (cx, cy - px(8)), (cx, cy + px(8)), px(2))
                pygame.draw.line(
                    surf, col, (cx - px(5), cy - px(3)), (cx + px(5), cy - px(3)), px(2)
                )
            elif kind == 2:
                pygame.draw.polygon(
                    surf,
                    col,
                    [(cx - px(6), cy + px(7)), (cx, cy - px(7)), (cx + px(6), cy + px(7))],
                    px(2),
                )
            elif kind == 3:
                pygame.draw.arc(
                    surf, col, (cx - px(6), cy - px(6), px(12), px(12)), 0, math.pi, px(2)
                )
                pygame.draw.line(surf, col, (cx, cy), (cx, cy + px(7)), px(2))
            else:
                pygame.draw.ellipse(surf, col, (cx - px(6), cy - px(3), px(12), px(6)), px(2))
                pygame.draw.circle(surf, col, (cx, cy), max(1, px(1)))
            x += px(16)


def _rubble(surf: pygame.Surface, th: LevelTheme, room: int, rng: random.Random) -> None:
    """Pared que se desmorona: boquetes oscuros y piedras sueltas."""
    w, h = surf.get_size()
    for _ in range(rng.randint(1, 2)):
        # Boquete: hueco oscuro, borde de sillares rotos iluminado arriba
        cx, cy = rng.randint(px(30), w - px(30)), rng.randint(px(30), h - px(70))
        pts = []
        for k in range(11):
            a = k / 11 * math.tau
            r = rng.randint(px(10), px(18))
            pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r * 0.75))
        rim = [(x + (x - cx) * 0.18, y + (y - cy) * 0.18) for x, y in pts]
        pygame.draw.polygon(surf, tuple(int(c * 0.55) for c in th.stone), rim)
        pygame.draw.polygon(surf, (10, 6, 6), pts)
        upper = [p for p in pts if p[1] <= cy]
        if len(upper) > 1:
            pygame.draw.lines(surf, th.hi, False, sorted(upper), max(1, px(1)))
    for floor in range(3):
        base = (floor + 1) * LAYOUT.tile_h - LAYOUT.floor_face - LAYOUT.floor_top
        for _ in range(rng.randint(2, 5)):
            x = rng.randint(0, w)
            r = rng.randint(px(3), px(7))
            col = tuple(max(0, int(c * rng.uniform(0.6, 1.0))) for c in th.stone)
            pygame.draw.circle(surf, col, (x, base - r // 2), r)


def _roses(surf: pygame.Surface, th: LevelTheme, room: int, rng: random.Random) -> None:
    """Guirnaldas de rosas que cuelgan de cada techo (aposentos)."""
    w, _ = surf.get_size()
    for floor in range(3):
        top = floor * LAYOUT.tile_h + px(10)
        pts = [
            (x, top + int(px(14) * (0.5 + 0.5 * math.sin(x / px(64) * math.pi))))
            for x in range(0, w + 1, px(16))
        ]
        pygame.draw.lines(surf, (40, 90, 50), False, pts, px(2))
        for x, y in pts[::2]:
            pygame.draw.circle(surf, (190, 40, 80), (x, y + px(2)), px(4))
            pygame.draw.circle(surf, (240, 110, 150), (x - px(1), y + px(1)), px(2))
            pygame.draw.ellipse(surf, (60, 120, 60), (x + px(3), y - px(2), px(6), px(3)))


def _veins(surf: pygame.Surface, th: LevelTheme, room: int, rng: random.Random) -> None:
    """Vetas del mármol."""
    w, h = surf.get_size()
    col = tuple(min(255, int(c * 1.12)) for c in th.stone)
    dark = tuple(max(0, int(c * 0.8)) for c in th.stone)
    for _ in range(rng.randint(5, 9)):
        x, y = rng.randint(0, w), rng.randint(0, h)
        pts = [(x, y)]
        for _ in range(rng.randint(5, 9)):
            x += rng.randint(px(6), px(20))
            y += rng.randint(-px(8), px(8))
            pts.append((x, y))
        pygame.draw.lines(surf, rng.choice((col, dark)), False, pts, 1)


_DECOR: dict[str, Decor] = {
    "cracks": _cracks,
    "streaks": _streaks,
    "moss": _moss,
    "chains": _chains,
    "rings": _rings,
    "cobwebs": _cobwebs,
    "bones": _bones,
    "skull_niches": _skull_niches,
    "stalactites": _stalactites,
    "roots": _roots,
    "crystals": _crystals,
    "windows": _windows,
    "niches": _niches,
    "tile_band": _tile_band,
    "tapestry": _tapestry,
    "banners": _banners,
    "candles": _candles,
    "glyphs": _glyphs,
    "rubble": _rubble,
    "roses": _roses,
    "veins": _veins,
}

# Orden de pintado: lo estructural primero, lo que cuelga encima.
_ORDER = (
    "veins",
    "niches",
    "tile_band",
    "glyphs",
    "cracks",
    "rubble",
    "streaks",
    "moss",
    "windows",
    "skull_niches",
    "crystals",
    "roots",
    "stalactites",
    "chains",
    "rings",
    "tapestry",
    "banners",
    "candles",
    "cobwebs",
    "bones",
    "roses",
)


Light = tuple[int, int, int, RGB]
"""Luz fija de la sala: ``(x, y, radio, color)`` en píxeles del mundo (``y``
desde lo alto de la sala, sin HUD)."""

RELIEF_BASE = 0.58
"""Factor de luz de la pared lejos de toda luz (antes del mapa de luz)."""
RELIEF_GAIN = 1.0
"""Cuánto suma cada luz a plena potencia sobre una cara que la mira."""
RELIEF_DEPTH = 0.075
"""Inclinación de las normales por unidad de gradiente de luminancia."""
RELIEF_Z = 46
"""Altura (px de diseño) de las luces sobre el plano de la pared."""
RELIEF_AMBIENT = 0.48
"""Luz ambiente direccional que marca el relieve en toda la pared."""
RELIEF_MAX = 1.45


def _norm3(x: float, y: float, z: float) -> tuple[float, float, float]:
    d = math.sqrt(x * x + y * y + z * z) or 1.0
    return x / d, y / d, z / d


def relief_factor(surf: pygame.Surface, lights: tuple[Light, ...], *, scale: int = 2) -> np.ndarray:
    """Factor de luz (w, h, 3) float32 para ``surf`` con las ``lights``:
    difusa lambertiana sobre el relieve de la pared con atenuación por
    distancia. Se calcula a ``1/scale`` de la resolución y se amplía."""
    w, h = surf.get_size()
    small = pygame.transform.smoothscale(surf, (max(2, w // scale), max(2, h // scale)))
    arr = pygame.surfarray.array3d(small).astype(np.float32)
    lum = arr[:, :, 0] * 0.3 + arr[:, :, 1] * 0.59 + arr[:, :, 2] * 0.11
    # Suavizado 3x3 para que el grano no chispee
    pad = np.pad(lum, 1, mode="edge")
    lum = (
        pad[:-2, :-2]
        + pad[:-2, 1:-1]
        + pad[:-2, 2:]
        + pad[1:-1, :-2]
        + pad[1:-1, 1:-1]
        + pad[1:-1, 2:]
        + pad[2:, :-2]
        + pad[2:, 1:-1]
        + pad[2:, 2:]
    ) / 9.0
    gx = np.zeros_like(lum)
    gy = np.zeros_like(lum)
    gx[1:-1, :] = (lum[2:, :] - lum[:-2, :]) * 0.5
    gy[:, 1:-1] = (lum[:, 2:] - lum[:, :-2]) * 0.5
    nx = -gx * RELIEF_DEPTH
    ny = -gy * RELIEF_DEPTH
    nz = np.ones_like(lum)
    inv = 1.0 / np.sqrt(nx * nx + ny * ny + 1.0)
    nx *= inv
    ny *= inv
    nz *= inv
    sw, sh = lum.shape
    xs = (np.arange(sw, dtype=np.float32) * scale)[:, None]
    ys = (np.arange(sh, dtype=np.float32) * scale)[None, :]
    # Luz ambiente direccional (de arriba, un poco por delante y a la
    # izquierda): el relieve se lee también lejos de toda llama.
    ax, ay, az = _norm3(-0.35, -0.6, 0.72)
    amb = np.clip(nx * ax + ny * ay + nz * az, 0.0, None) * RELIEF_AMBIENT
    total = np.repeat((RELIEF_BASE + amb)[:, :, None], 3, axis=2)
    z = float(px(RELIEF_Z))
    for lx, ly, radius, color in lights:
        dx = lx - xs
        dy = ly - ys
        dist = np.sqrt(dx * dx + dy * dy + z * z)
        ndotl = np.clip((nx * dx + ny * dy + nz * z) / dist, 0.0, None)
        att = 1.0 / (1.0 + (dist / max(1.0, float(radius))) ** 2)
        # Las luces pequeñas (velas, cristales) aportan menos que una antorcha
        power = min(1.0, radius / float(px(320)))
        k = (ndotl * att * RELIEF_GAIN * power)[:, :, None]
        total += k * (np.array(color, dtype=np.float32) / 255.0)[None, None, :]
    np.clip(total, 0.4, RELIEF_MAX, out=total)
    if scale == 1:
        return total
    up = np.repeat(np.repeat(total, scale, axis=0), scale, axis=1)
    return up[:w, :h]


def bake_relief(surf: pygame.Surface, lights: tuple[Light, ...]) -> None:
    """Multiplica ``surf`` (en sitio) por :func:`relief_factor`."""
    if not lights:
        return
    fac = relief_factor(surf, lights)
    arr = pygame.surfarray.pixels3d(surf)
    lit = arr.astype(np.float32) * fac
    np.clip(lit, 0, 255, out=lit)
    arr[:] = lit.astype(np.uint8)
    del arr


TILE_LIGHT_SCALE = 8


@functools.lru_cache(maxsize=32)
def tile_light(lights: tuple[Light, ...]) -> tuple[pygame.Surface, pygame.Surface]:
    """Luz horneada para la capa de tiles (losas, muros, columnas, rejas):
    la misma caída por distancia y color que la pared, sin relieve (las
    piezas miran al jugador). Devuelve dos superficies del tamaño de la
    sala para aplicar como ``factor = mult/255 + add/255``: la primera se
    multiplica (0..1) y la segunda se suma (lo que pasa de 1)."""
    w, h = LAYOUT.window_w, LAYOUT.room_h
    q = TILE_LIGHT_SCALE
    sw, sh = w // q, h // q
    xs = (np.arange(sw, dtype=np.float32) * q + q / 2)[:, None]
    ys = (np.arange(sh, dtype=np.float32) * q + q / 2)[None, :]
    z = float(px(RELIEF_Z))
    az = _norm3(-0.35, -0.6, 0.72)[2]
    total = np.full((sw, sh, 3), RELIEF_BASE + RELIEF_AMBIENT * az, dtype=np.float32)
    for lx, ly, radius, color in lights:
        dx = lx - xs
        dy = ly - ys
        dist = np.sqrt(dx * dx + dy * dy + z * z)
        ndotl = z / dist
        att = 1.0 / (1.0 + (dist / max(1.0, float(radius))) ** 2)
        power = min(1.0, radius / float(px(320)))
        k = (ndotl * att * RELIEF_GAIN * power)[:, :, None]
        total += k * (np.array(color, dtype=np.float32) / 255.0)[None, None, :]
    np.clip(total, 0.4, RELIEF_MAX, out=total)
    mult = (np.clip(total, 0.0, 1.0) * 255).astype(np.uint8)
    add = (np.clip(total - 1.0, 0.0, 1.0) * 255).astype(np.uint8)
    out = []
    for arr in (mult, add):
        small = pygame.Surface((sw, sh))
        pygame.surfarray.blit_array(small, arr)
        out.append(pygame.transform.smoothscale(small, (w, h)))
    return out[0], out[1]


def light_tiles(tiles: pygame.Surface, lights: tuple[Light, ...], top: int) -> pygame.Surface:
    """Copia de la capa de tiles (con alfa) iluminada por ``tile_light``."""
    if not lights:
        return tiles
    mult, add = tile_light(lights)
    lit = tiles.copy()
    lit.blit(mult, (0, top), special_flags=pygame.BLEND_RGB_MULT)
    extra = tiles.copy()
    extra.blit(add, (0, top), special_flags=pygame.BLEND_RGB_MULT)
    lit.blit(extra, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
    return lit


@functools.lru_cache(maxsize=24)
def backdrop(room_id: int, theme: str | bool, lights: tuple[Light, ...] = ()) -> pygame.Surface:
    """Superficie del ancho de la sala y alto del mundo (sin HUD).

    ``theme``: clave de un tema de nivel (``"l1"``...), o ``True``/``False``
    para el palacio/mazmorra genéricos. ``lights``: luces fijas de la
    sala cuya luz se hornea con relieve (vacío: pared sin hornear)."""
    if isinstance(theme, bool):
        theme = "l4" if theme else "l1"
    th = theme_by_key(theme)
    w, h = LAYOUT.window_w, LAYOUT.room_h
    seed = _seed(room_id, th.key, "wall")
    rng = random.Random(seed)
    nrng = np.random.default_rng(seed)
    arr = np.empty((w, h, 3), dtype=np.float32)
    arr[:] = np.array(th.mortar, dtype=np.float32)
    if th.masonry == "rough":
        _rough(arr, th, nrng, w, h)
    elif th.masonry == "marble":
        _marble(arr, th, rng, w, h)
    else:
        _blocks(arr, th, rng, w, h, brick=th.masonry == "brick")
    blotch = _noise(nrng, w, h, px(40))
    grain = nrng.normal(0.0, 1.0, (w, h)).astype(np.float32)
    arr *= (1.0 + 0.07 * blotch)[:, :, None]
    arr += (grain * (3.0 if th.masonry == "marble" else 5.0))[:, :, None]
    tile_h = LAYOUT.tile_h
    yy = np.arange(h, dtype=np.float32) % tile_h
    ceiling = 1.0 - 0.28 * np.clip(1.0 - yy / px(40), 0.0, 1.0) ** 2
    arr *= ceiling[None, :, None]
    if th.damp > 0:
        damp = np.clip(_noise(nrng, w, h, px(18)), 0.0, None)
        foot = np.clip((yy - (tile_h - px(60))) / px(60), 0.0, 1.0) ** 2
        k = (damp * foot[None, :] * th.damp)[:, :, None]
        arr = arr * (1 - k) + np.array(th.accent, dtype=np.float32)[None, None, :] * k
    np.clip(arr, 0, 255, out=arr)
    surf = pygame.Surface((w, h))
    pygame.surfarray.blit_array(surf, arr.astype(np.uint8))
    for name in _ORDER:
        if name in th.decor:
            _DECOR[name](surf, th, room_id, random.Random(_seed(room_id, th.key, name + "/draw")))
    bake_relief(surf, lights)
    return surf
