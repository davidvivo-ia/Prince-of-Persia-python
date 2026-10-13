"""Pared del fondo con textura de sillería, generada por sala y cacheada.

Mazmorra: piedra azul grisácea, juntas profundas, grietas y musgo.
Palacio: arenisca cálida con franja de azulejos y arcos lobulados.
La luz (``fx.Lighting``) multiplica sobre esto: lejos de las antorchas
queda en penumbra, cerca brilla la piedra.
"""

from __future__ import annotations

import functools
import random
from dataclasses import dataclass

import pygame

from pop2026canon.presentation.layout import LAYOUT

RGB = tuple[int, int, int]


@dataclass(frozen=True, slots=True)
class _Pal:
    stone: RGB
    stone_var: int
    mortar: RGB
    hi: RGB
    accent: RGB


_DUNGEON = _Pal(
    stone=(104, 106, 132),
    stone_var=14,
    mortar=(34, 34, 48),
    hi=(130, 132, 158),
    accent=(40, 66, 44),
)
_PALACE = _Pal(
    stone=(158, 130, 108),
    stone_var=16,
    mortar=(70, 52, 44),
    hi=(150, 126, 104),
    accent=(40, 84, 120),
)


@functools.lru_cache(maxsize=48)
def backdrop(room_id: int, palace: bool) -> pygame.Surface:
    """Superficie del ancho de la sala y alto del mundo (sin HUD)."""
    w, h = LAYOUT.window_w, LAYOUT.room_h
    pal = _PALACE if palace else _DUNGEON
    rng = random.Random(room_id * 7919 + (1 if palace else 0))
    surf = pygame.Surface((w, h))
    surf.fill(pal.mortar)
    row_h = 21
    y = 0
    row = 0
    while y < h:
        x = -rng.randint(0, 30) if row % 2 else 0
        while x < w:
            bw = rng.randint(34, 58)
            v = rng.randint(-pal.stone_var, pal.stone_var)
            base = tuple(max(0, min(255, c + v)) for c in pal.stone)
            rect = pygame.Rect(x + 1, y + 1, bw - 2, row_h - 2)
            pygame.draw.rect(surf, base, rect)
            # bisel: borde superior claro, inferior oscuro
            hi = tuple(min(255, c + 14) for c in base)
            lo = tuple(max(0, c - 18) for c in base)
            pygame.draw.line(surf, hi, rect.topleft, rect.topright)
            pygame.draw.line(surf, lo, rect.bottomleft, rect.bottomright)
            # moteado
            for _ in range(rng.randint(2, 6)):
                px = rng.randint(rect.left, rect.right - 1)
                py = rng.randint(rect.top, rect.bottom - 1)
                d = rng.randint(-12, 12)
                surf.set_at((px, py), tuple(max(0, min(255, c + d)) for c in base))
            x += bw
        y += row_h
        row += 1
    # Grietas
    for _ in range(rng.randint(1, 3)):
        cx, cy = rng.randint(20, w - 20), rng.randint(20, h - 40)
        pts = [(cx, cy)]
        for _ in range(rng.randint(3, 6)):
            cx += rng.randint(-8, 8)
            cy += rng.randint(4, 12)
            pts.append((cx, cy))
        pygame.draw.lines(surf, pal.mortar, False, pts, 1)
    if palace:
        # Franja de azulejos a media altura de cada piso
        for floor in range(3):
            band_y = floor * LAYOUT.tile_h + 30
            pygame.draw.rect(surf, (60, 46, 40), (0, band_y, w, 12))
            for bx in range(0, w, 16):
                c = pal.accent if (bx // 16) % 2 == 0 else (150, 120, 60)
                pygame.draw.polygon(
                    surf,
                    c,
                    [
                        (bx + 8, band_y + 1),
                        (bx + 15, band_y + 6),
                        (bx + 8, band_y + 11),
                        (bx + 1, band_y + 6),
                    ],
                )
        # Arcos lobulados ciegos
        for floor in range(3):
            for i in range(0, LAYOUT.room_cols, 2):
                ax = i * LAYOUT.tile_w + 14
                ay = floor * LAYOUT.tile_h + 48
                rect = pygame.Rect(ax, ay, LAYOUT.tile_w * 2 - 28, LAYOUT.tile_h - 70)
                pygame.draw.rect(
                    surf,
                    tuple(int(c * 0.55) for c in pal.stone),
                    rect,
                    border_top_left_radius=rect.w // 2,
                    border_top_right_radius=rect.w // 2,
                )
                pygame.draw.rect(
                    surf,
                    pal.hi,
                    rect,
                    2,
                    border_top_left_radius=rect.w // 2,
                    border_top_right_radius=rect.w // 2,
                )
    else:
        # Musgo y humedad en la base de cada piso
        for floor in range(3):
            base_y = (floor + 1) * LAYOUT.tile_h - 26
            for _ in range(rng.randint(4, 9)):
                mx = rng.randint(0, w)
                for k in range(rng.randint(3, 9)):
                    surf.set_at(
                        (
                            min(w - 1, mx + rng.randint(-6, 6)),
                            min(h - 1, base_y + rng.randint(-k, 0)),
                        ),
                        pal.accent,
                    )
        # Cadenas colgando en algunas salas
        if rng.random() < 0.5:
            cx = rng.randint(40, w - 40)
            for yy in range(0, rng.randint(40, 90), 6):
                pygame.draw.ellipse(surf, (40, 40, 48), (cx - 2, yy, 5, 7), 1)
    return surf
