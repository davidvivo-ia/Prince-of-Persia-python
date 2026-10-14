"""Atlas procedural de tiles en HD.

Cada tile se pinta una vez por variante (tipo, estado, estilo, vecinos)
en un sprite con volumen — losas con cara superior y frontal biseladas,
columnas cilíndricas, rastrillos de hierro, frascos de vidrio, cuchillas
metálicas — y se cachea: un frame cuesta un ``blit`` por celda.

Geometría (ver ``LAYOUT.floor_*``): la losa de suelo ocupa el pie de la
celda — cara superior (donde se pisa) y cara frontal debajo. Los pies
de los personajes pisan el centro de la cara superior.

Las llamas de las antorchas son lo único animado: ``draw_torch_flame``.
"""

from __future__ import annotations

import functools
import math
import random
from dataclasses import dataclass

import pygame

from pop2026canon.domain.tiles import PotionType
from pop2026canon.presentation.layout import LAYOUT, px
from pop2026canon.presentation.themes import (
    PALACE_LEVELS,
    LevelTheme,
    level_is_palace,
    theme_by_key,
)

__all__ = ["PALACE_LEVELS", "level_is_palace"]

RGB = tuple[int, int, int]

POTION_COLORS: dict[int, RGB] = {
    int(PotionType.HEAL): (255, 70, 60),
    int(PotionType.MAX_HP): (90, 255, 120),
    int(PotionType.POISON): (80, 120, 255),
    int(PotionType.FLOAT): (180, 220, 255),
    int(PotionType.TIME): (255, 220, 90),
}


# ---------------------------------------------------------------------------
# Paletas y utilidades
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class StonePal:
    top: RGB
    top_hi: RGB
    face: RGB
    face_dark: RGB
    joint: RGB
    column: RGB
    trim: RGB


DUNGEON = StonePal(
    top=(182, 186, 214),
    top_hi=(236, 238, 252),
    face=(98, 100, 130),
    face_dark=(48, 48, 70),
    joint=(38, 38, 54),
    column=(128, 130, 160),
    trim=(150, 150, 176),
)
PALACE = StonePal(
    top=(240, 220, 186),
    top_hi=(255, 248, 228),
    face=(160, 128, 102),
    face_dark=(96, 72, 58),
    joint=(78, 58, 46),
    column=(222, 204, 178),
    trim=(232, 192, 64),
)

IRON: RGB = (64, 66, 80)
IRON_HI: RGB = (150, 154, 176)
STEEL: RGB = (196, 202, 218)
GOLD: RGB = (232, 192, 64)


def _mix(a: RGB, b: RGB, t: float) -> RGB:
    return (
        int(a[0] * (1 - t) + b[0] * t),
        int(a[1] * (1 - t) + b[1] * t),
        int(a[2] * (1 - t) + b[2] * t),
    )


def _shade(c: RGB, k: float) -> RGB:
    return (min(255, int(c[0] * k)), min(255, int(c[1] * k)), min(255, int(c[2] * k)))


def _vgrad(s: pygame.Surface, rect: pygame.Rect, top: RGB, bottom: RGB) -> None:
    h = max(1, rect.h)
    for i in range(rect.h):
        pygame.draw.line(
            s, _mix(top, bottom, i / h), (rect.x, rect.y + i), (rect.right - 1, rect.y + i)
        )


def _hgrad_cyl(s: pygame.Surface, rect: pygame.Rect, base: RGB) -> None:
    """Relleno cilíndrico: luz por la izquierda, sombra a la derecha."""
    w = max(1, rect.w)
    for i in range(rect.w):
        u = i / w
        k = 0.62 + 0.55 * math.cos((u - 0.32) * math.pi * 0.95) ** 2 * (1 if u > 0.05 else 0.8)
        if u > 0.8:
            k *= 0.8
        pygame.draw.line(s, _shade(base, k), (rect.x + i, rect.y), (rect.x + i, rect.bottom - 1))


# ---------------------------------------------------------------------------
# Marco del sprite
# ---------------------------------------------------------------------------

PADX = px(4)
EXT_TOP = LAYOUT.floor_face + LAYOUT.floor_top + px(6)
"""Lo que un sprite puede subir por encima de su celda (muros)."""
EXT_BOT = px(16)
"""Sombra bajo la losa (cae sobre la fila de abajo)."""


@dataclass(frozen=True, slots=True)
class Ctx:
    pal: StonePal
    palace: bool
    variant: int
    left_open: bool
    right_open: bool

    @property
    def tw(self) -> int:
        return LAYOUT.tile_w

    @property
    def th(self) -> int:
        return LAYOUT.tile_h

    @property
    def ox(self) -> int:
        return PADX

    @property
    def oy(self) -> int:
        return EXT_TOP

    @property
    def bottom(self) -> int:
        return self.oy + self.th

    @property
    def face_y(self) -> int:
        return self.bottom - LAYOUT.floor_face

    @property
    def top_y(self) -> int:
        return self.face_y - LAYOUT.floor_top

    @property
    def floor_y(self) -> int:
        """Línea donde apoyan los pies (centro de la cara superior)."""
        return self.bottom - LAYOUT.foot_lift


def _new_sprite() -> pygame.Surface:
    return pygame.Surface(
        (LAYOUT.tile_w + PADX * 2, LAYOUT.tile_h + EXT_TOP + EXT_BOT), pygame.SRCALPHA
    )


# ---------------------------------------------------------------------------
# Losa de suelo
# ---------------------------------------------------------------------------


_AO_H = px(26)


@functools.lru_cache(maxsize=2)
def _ao_strip(w: int) -> pygame.Surface:
    strip = pygame.Surface((w, _AO_H), pygame.SRCALPHA)
    for i in range(_AO_H):
        a = int(120 * (i / _AO_H) ** 1.8)
        pygame.draw.line(strip, (0, 0, 0, a), (0, i), (w, i))
    return strip


def _slab(s: pygame.Surface, c: Ctx, x: int, top_y: int, *, cracked: bool = False) -> None:
    """Losa completa (cara superior + frontal) con su esquina superior
    izquierda de la cara superior en ``(x, top_y)``."""
    tw = c.tw
    t, f = LAYOUT.floor_top, LAYOUT.floor_face
    pal = c.pal
    rng = random.Random(c.variant * 31 + (7 if c.palace else 0))
    face_y = top_y + t
    # Sombra proyectada bajo la losa
    shadow = pygame.Surface((tw, EXT_BOT), pygame.SRCALPHA)
    for i in range(EXT_BOT):
        a = int(130 * (1 - i / EXT_BOT) ** 1.6)
        pygame.draw.line(shadow, (0, 0, 0, a), (0, i), (tw, i))
    s.blit(shadow, (x, face_y + f))
    # Oclusión ambiental: la pared se oscurece justo encima de la losa
    # (asienta el suelo y lo separa de la pared iluminada).
    s.blit(_ao_strip(tw), (x, top_y - _AO_H))
    # Cara frontal: dos hiladas de sillares con juntas alternas
    face = pygame.Rect(x, face_y, tw, f)
    _vgrad(s, face, pal.face, _shade(pal.face, 0.72))
    course = f // 2
    joints = (tw * (3 + c.variant % 3) // 8, tw * (1 + (c.variant // 3) % 2) // 4 + tw // 2)
    for i in range(2):
        cy0 = face_y + i * course
        jx = x + joints[i] % tw
        pygame.draw.line(s, pal.joint, (jx, cy0 + 1), (jx, cy0 + course - 1), max(1, px(1)))
        pygame.draw.line(
            s, _shade(pal.face, 1.18), (jx + px(1), cy0 + 1), (jx + px(1), cy0 + course - 2), 1
        )
        if i == 1:
            pygame.draw.line(s, pal.joint, (x, cy0), (x + tw - 1, cy0), max(1, px(1) // 2 + 1))
    pygame.draw.line(s, _shade(pal.face, 1.25), (x, face_y), (x + tw - 1, face_y), px(1))
    pygame.draw.line(
        s, pal.face_dark, (x, face_y + f - px(1)), (x + tw - 1, face_y + f - px(1)), px(1)
    )
    # Cara superior: más oscura al fondo, clara en el borde delantero
    top = pygame.Rect(x, top_y, tw, t)
    _vgrad(s, top, _shade(pal.top, 0.7), pal.top)
    pygame.draw.line(s, pal.top_hi, (x, face_y - px(1)), (x + tw - 1, face_y - px(1)), px(1))
    pygame.draw.line(s, _shade(pal.top, 0.45), (x, top_y), (x + tw - 1, top_y), 1)
    jx = x + joints[0] % tw
    pygame.draw.line(s, _shade(pal.top, 0.72), (jx - px(2), top_y + 1), (jx, face_y - px(1)), 1)
    # Moteado y desgaste
    for _ in range(10):
        mx = x + rng.randrange(tw)
        my = top_y + rng.randrange(max(1, t - 2))
        s.fill(_shade(pal.top, rng.uniform(0.8, 1.08)), (mx, my, px(2), 1))
    for _ in range(14):
        mx = x + rng.randrange(tw)
        my = face_y + px(2) + rng.randrange(max(1, f - px(4)))
        s.fill(_shade(pal.face, rng.uniform(0.75, 1.15)), (mx, my, px(1) + 1, px(1)))
    if c.variant % 5 == 1 or cracked:
        cx = x + rng.randrange(tw // 5, tw * 4 // 5)
        pts = [(cx, face_y + 1)]
        yy = face_y + 1
        while yy < face_y + f - px(2):
            yy += rng.randint(px(2), px(5))
            cx += rng.randint(-px(3), px(3))
            pts.append((cx, min(yy, face_y + f - px(2))))
        pygame.draw.lines(s, pal.joint, False, pts, max(1, px(1)))
    # Extremos al aire: canto biselado
    if c.left_open:
        pygame.draw.line(s, _shade(pal.top_hi, 1.0), (x, top_y + 1), (x, face_y + f - 1), px(1))
        pygame.draw.polygon(s, (0, 0, 0, 0), [(x, top_y), (x + px(3), top_y), (x, top_y + px(3))])
    if c.right_open:
        pygame.draw.line(
            s, pal.face_dark, (x + tw - px(1), top_y + 1), (x + tw - px(1), face_y + f - 1), px(2)
        )


def _floor(s: pygame.Surface, c: Ctx) -> None:
    _slab(s, c, c.ox, c.top_y)


# ---------------------------------------------------------------------------
# Piezas
# ---------------------------------------------------------------------------


def _spikes(s: pygame.Surface, c: Ctx, modifier: int) -> None:
    if modifier == 0:
        extent = 0.0
    elif modifier == 0xFF or modifier & 0x80:
        extent = 1.0
    elif modifier < 5:
        extent = modifier / 4.0
    else:
        extent = max(0.0, (9 - modifier) / 4.0)
    tw = c.tw
    base_y = c.floor_y + px(2)
    slot = pygame.Rect(c.ox + px(8), c.floor_y - px(1), tw - px(16), px(3))
    pygame.draw.rect(s, (14, 12, 20), slot, border_radius=px(1))
    if extent <= 0.0:
        return
    n = 5
    sw = (tw - px(16)) / n
    height = px(36) * extent
    for i in range(n):
        sx = c.ox + px(8) + i * sw
        jitter = ((i * 37 + c.variant) % 5 - 2) * px(1)
        tip = (sx + sw / 2 + jitter * 0.3, base_y - height - jitter)
        left = (sx + px(1), base_y)
        right = (sx + sw - px(1), base_y)
        mid = (sx + sw / 2, base_y)
        pygame.draw.polygon(s, _shade(STEEL, 0.55), [left, tip, right])
        pygame.draw.polygon(s, STEEL, [left, tip, mid])
        pygame.draw.line(s, (255, 255, 255), tip, (tip[0] - sw * 0.18, tip[1] + height * 0.35), 1)
        if modifier == 0xFF and i in (1, 2, 3):
            drip = [
                (tip[0] - sw * 0.2, tip[1] + height * 0.15),
                tip,
                (tip[0] + sw * 0.2, tip[1] + height * 0.2),
                (tip[0], tip[1] + height * 0.55),
            ]
            pygame.draw.polygon(s, (150, 10, 14), drip)
    if modifier == 0xFF:
        pygame.draw.ellipse(s, (120, 8, 12), (c.ox + px(10), c.floor_y - px(3), tw - px(20), px(6)))


def _column(
    s: pygame.Surface,
    c: Ctx,
    cx: int,
    width: int,
    top: int,
    bottom: int,
    *,
    base: bool,
    capital: bool,
) -> None:
    color = c.pal.column
    shaft = pygame.Rect(cx - width // 2, top, width, bottom - top)
    _hgrad_cyl(s, shaft, color)
    # Estrías verticales
    for k in (0.3, 0.55, 0.78):
        xx = shaft.x + int(shaft.w * k)
        pygame.draw.line(s, _shade(color, 0.7), (xx, top), (xx, bottom), 1)
    if capital:
        cap = pygame.Rect(cx - width // 2 - px(5), top, width + px(10), px(10))
        _hgrad_cyl(s, cap, _mix(color, c.pal.trim, 0.25))
        pygame.draw.line(s, _shade(color, 0.5), cap.bottomleft, cap.bottomright, px(1))
        ring = pygame.Rect(cx - width // 2 - px(2), cap.bottom, width + px(4), px(4))
        _hgrad_cyl(s, ring, _shade(color, 0.9))
    if base:
        plinth = pygame.Rect(cx - width // 2 - px(6), bottom - px(12), width + px(12), px(12))
        _hgrad_cyl(s, plinth, _shade(color, 0.92))
        pygame.draw.line(s, _shade(color, 1.2), plinth.topleft, plinth.topright, 1)
        torus = pygame.Rect(cx - width // 2 - px(3), bottom - px(17), width + px(6), px(5))
        _hgrad_cyl(s, torus, color)


def _pillar_front(s: pygame.Surface, c: Ctx) -> None:
    cx = c.ox + c.tw * 6 // 10
    _column(s, c, cx, px(26), c.oy, c.floor_y + px(2), base=True, capital=True)


def _bigpillar_bottom_front(s: pygame.Surface, c: Ctx) -> None:
    cx = c.ox + c.tw // 2
    _column(s, c, cx, px(40), c.oy, c.floor_y + px(2), base=True, capital=False)


def _bigpillar_top_front(s: pygame.Surface, c: Ctx) -> None:
    cx = c.ox + c.tw // 2
    _column(s, c, cx, px(40), c.oy, c.bottom, base=False, capital=True)


def _gate(s: pygame.Surface, c: Ctx, modifier: int) -> None:
    open_amount = max(0, min(7, modifier))
    tw = c.tw
    gw = px(42)
    gx = c.ox + (tw - gw) // 2
    lintel = pygame.Rect(gx - px(6), c.oy, gw + px(12), px(14))
    _vgrad(s, lintel, c.pal.face, c.pal.face_dark)
    pygame.draw.line(s, c.pal.top_hi, lintel.topleft, lintel.topright, px(1))
    # Ranura en la pared por la que sube el rastrillo
    groove = pygame.Rect(gx + px(2), lintel.bottom, gw - px(4), c.floor_y - lintel.bottom)
    g = pygame.Surface(groove.size, pygame.SRCALPHA)
    g.fill((0, 0, 0, 70))
    s.blit(g, groove)
    top = lintel.bottom
    full = c.floor_y + px(3) - top
    bars_bot = top + full - (open_amount * (full - px(18))) // 7
    # Rejilla: barrotes y travesaños remachados
    nb = 5
    for i in range(nb):
        bx = gx + px(3) + i * (gw - px(6)) // (nb - 1)
        pygame.draw.line(s, IRON, (bx, top), (bx, bars_bot - px(5)), px(3))
        pygame.draw.line(s, IRON_HI, (bx - px(1), top), (bx - px(1), bars_bot - px(5)), 1)
        pygame.draw.polygon(
            s,
            IRON,
            [(bx - px(2), bars_bot - px(6)), (bx, bars_bot), (bx + px(2), bars_bot - px(6))],
        )
    rows = max(2, (bars_bot - top) // px(22))
    for r in range(1, rows + 1):
        hy = bars_bot - px(10) - (r - 1) * px(22)
        if hy <= top + px(2):
            break
        pygame.draw.line(s, IRON, (gx, hy), (gx + gw, hy), px(3))
        pygame.draw.line(s, IRON_HI, (gx, hy - px(1)), (gx + gw, hy - px(1)), 1)
        for i in range(nb):
            bx = gx + px(3) + i * (gw - px(6)) // (nb - 1)
            pygame.draw.circle(s, IRON_HI, (bx, hy), px(1) + 1)


def _plate(s: pygame.Surface, c: Ctx, pressed: bool, rim: RGB) -> None:
    tw = c.tw
    h = px(3) if pressed else px(6)
    rect = pygame.Rect(c.ox + tw // 5, c.floor_y - h, tw * 3 // 5, h + px(2))
    _vgrad(s, rect, _shade(c.pal.top, 0.95), _shade(c.pal.face, 0.9))
    pygame.draw.rect(s, _shade(c.pal.face_dark, 0.9), rect, 1)
    pygame.draw.line(s, rim, rect.topleft, (rect.right - 1, rect.top), px(1))


def _doortop(s: pygame.Surface, c: Ctx) -> None:
    """Dintel de una puerta: arco de piedra que cuelga del techo."""
    tw = c.tw
    h = px(30)
    band = pygame.Rect(c.ox, c.oy, tw, h)
    _vgrad(s, band, c.pal.face, c.pal.face_dark)
    arch = pygame.Rect(c.ox + px(6), c.oy + px(10), tw - px(12), h * 2)
    clip = s.get_clip()
    s.set_clip(band)
    pygame.draw.ellipse(s, (14, 10, 22), arch)
    s.set_clip(clip)
    pygame.draw.line(s, c.pal.top_hi, band.topleft, band.topright, px(1))
    for k in range(3):
        kx = c.ox + tw * (k + 1) // 4
        pygame.draw.line(s, c.pal.joint, (kx, c.oy + px(2)), (kx, c.oy + px(8)), 1)
    if c.palace:
        # Cortinaje recogido
        drape = [
            (c.ox, c.oy + h),
            (c.ox + px(16), c.oy + h),
            (c.ox + px(4), c.oy + h + px(40)),
            (c.ox, c.oy + h + px(44)),
        ]
        pygame.draw.polygon(s, (140, 24, 36), drape)
        pygame.draw.line(s, GOLD, (c.ox, c.oy + h), (c.ox + px(16), c.oy + h), px(2))


def _potion(s: pygame.Surface, c: Ctx, modifier: int) -> None:
    col = POTION_COLORS.get(modifier, (220, 90, 170))
    big = modifier == int(PotionType.MAX_HP)
    r = px(10 if big else 8)
    cx = c.ox + c.tw // 2
    cy = c.floor_y - r
    neck_h = px(10 if big else 8)
    # Sombra en el suelo
    sh = pygame.Surface((r * 3, px(5)), pygame.SRCALPHA)
    pygame.draw.ellipse(sh, (0, 0, 0, 90), sh.get_rect())
    s.blit(sh, (cx - r * 3 // 2, c.floor_y - px(2)))
    glass = (170, 200, 220)
    pygame.draw.rect(s, glass, (cx - px(3), cy - r - neck_h + px(2), px(6), neck_h))
    pygame.draw.rect(
        s, (110, 70, 40), (cx - px(4), cy - r - neck_h - px(2), px(8), px(5)), border_radius=px(1)
    )
    pygame.draw.circle(s, _shade(glass, 0.8), (cx, cy), r)
    # Líquido con menisco y degradado
    liquid = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
    for i in range(r * 2):
        k = i / (r * 2)
        if k < 0.3:
            continue
        pygame.draw.line(liquid, (*_shade(col, 1.15 - 0.5 * k), 255), (0, i), (r * 2, i))
    mask = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
    pygame.draw.circle(mask, (255, 255, 255, 255), (r, r), r - px(2))
    liquid.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    s.blit(liquid, (cx - r, cy - r))
    pygame.draw.circle(s, _shade(glass, 1.15), (cx, cy), r, 1)
    pygame.draw.circle(s, (255, 255, 255), (cx - r // 3, cy - r // 3), max(1, r // 4))
    pygame.draw.circle(s, (255, 255, 255), (cx + r // 3, cy + r // 4), 1)


def _loose(s: pygame.Surface, c: Ctx, modifier: int) -> None:
    jitter = 0
    if modifier:
        phase = modifier & 0x7F
        jitter = (1 if phase % 2 else -1) * (px(2) if phase > 5 else px(1))
    _slab(s, c, c.ox + jitter, c.top_y + (abs(jitter) // 2), cracked=True)
    pygame.draw.line(
        s,
        c.pal.joint,
        (c.ox + jitter + c.tw // 4, c.top_y + px(2)),
        (c.ox + jitter + c.tw * 2 // 3, c.face_y - px(1)),
        px(1),
    )


def _mirror(s: pygame.Surface, c: Ctx) -> None:
    tw = c.tw
    frame = pygame.Rect(c.ox + px(10), c.oy + px(14), tw - px(20), c.floor_y - c.oy - px(16))
    pygame.draw.rect(
        s,
        _shade(GOLD, 0.6),
        frame,
        border_top_left_radius=frame.w // 2,
        border_top_right_radius=frame.w // 2,
    )
    glass = frame.inflate(-px(8), -px(8))
    g = pygame.Surface(glass.size, pygame.SRCALPHA)
    for i in range(glass.h):
        k = i / max(1, glass.h)
        pygame.draw.line(g, (*_mix((150, 170, 210), (60, 70, 110), k), 255), (0, i), (glass.w, i))
    for i in range(0, glass.w + glass.h, px(14)):
        pygame.draw.line(g, (230, 240, 255, 40), (i, 0), (i - glass.h // 2, glass.h), px(3))
    mask = pygame.Surface(glass.size, pygame.SRCALPHA)
    pygame.draw.rect(
        mask,
        (255, 255, 255, 255),
        mask.get_rect(),
        border_top_left_radius=glass.w // 2,
        border_top_right_radius=glass.w // 2,
    )
    g.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    s.blit(g, glass)
    pygame.draw.rect(
        s,
        GOLD,
        frame,
        px(2),
        border_top_left_radius=frame.w // 2,
        border_top_right_radius=frame.w // 2,
    )


def _debris(s: pygame.Surface, c: Ctx) -> None:
    rng = random.Random(c.variant + 99)
    for _ in range(9):
        w = rng.randint(px(5), px(14))
        h = rng.randint(px(3), px(7))
        x = c.ox + rng.randint(px(2), c.tw - w - px(2))
        y = c.floor_y - h + rng.randint(-px(1), px(2))
        col = _shade(c.pal.face, rng.uniform(0.7, 1.15))
        pts = [
            (x, y + h),
            (x + rng.randint(0, px(3)), y),
            (x + w - rng.randint(0, px(3)), y + rng.randint(0, px(2))),
            (x + w, y + h),
        ]
        pygame.draw.polygon(s, col, pts)
        pygame.draw.line(s, _shade(col, 1.25), pts[1], pts[2], 1)


def _door_half(s: pygame.Surface, c: Ctx, *, left: bool, open_: bool) -> None:
    """Media puerta de salida: arco de dos celdas con escalera interior y
    hoja que sube cuando la puerta está abierta."""
    tw = c.tw
    pal = c.pal
    top = c.oy + px(14)
    inner_top = top + px(26)
    floor = c.floor_y
    # Hueco: oscuro, o cálido con escalera si está abierta
    hole = pygame.Rect(c.ox, inner_top, tw, floor - inner_top)
    if left:
        hole.x += px(16)
        hole.w -= px(16)
    else:
        hole.w -= px(16)
    _vgrad(s, hole, (10, 8, 18), (26, 18, 30) if not open_ else (70, 46, 26))
    # Escalones que suben hacia el fondo
    for i in range(4):
        sy = floor - px(6) - i * px(12)
        inset = i * px(9)
        step = pygame.Rect(hole.x + (inset if left else 0), sy, hole.w - inset, px(6))
        col = _shade(pal.top, 0.42 + i * 0.08) if open_ else _shade(pal.top, 0.2 + i * 0.03)
        pygame.draw.rect(s, col, step)
        pygame.draw.line(s, _shade(col, 1.3), step.topleft, step.topright, 1)
    if not open_:
        # Hoja de la puerta bajada (madera con herrajes)
        leaf = hole.copy()
        _vgrad(s, leaf, (84, 54, 34), (52, 32, 20))
        for k in range(1, 4):
            yy = leaf.y + leaf.h * k // 4
            pygame.draw.line(s, IRON, (leaf.x, yy), (leaf.right, yy), px(2))
        for k in range(1, 3):
            xx = leaf.x + leaf.w * k // 3
            pygame.draw.line(s, (40, 24, 14), (xx, leaf.y), (xx, leaf.bottom), 1)
    # Jamba exterior
    jamb = pygame.Rect(
        c.ox if left else c.ox + tw - px(16), top + px(10), px(16), floor - top - px(10)
    )
    _vgrad(s, jamb, pal.face, pal.face_dark)
    pygame.draw.line(s, pal.top_hi, jamb.topleft, jamb.bottomleft, 1)
    # Arco (media bóveda por lado) con dovelas
    arc_rect = pygame.Rect(c.ox if left else c.ox - tw, top, tw * 2, px(60))
    clip = s.get_clip()
    s.set_clip(pygame.Rect(c.ox, c.oy, tw, c.th))
    pygame.draw.ellipse(s, pal.face, arc_rect)
    pygame.draw.ellipse(s, _shade(pal.top, 0.9), arc_rect, px(3))
    inner = arc_rect.inflate(-px(28), -px(24))
    inner.y += px(12)
    pygame.draw.ellipse(s, (10, 8, 18) if not open_ else (60, 40, 24), inner)
    cx, cy = arc_rect.center
    for a in range(0, 180, 20):
        r = math.radians(a)
        p1 = (cx + math.cos(r) * arc_rect.w / 2, cy - math.sin(r) * arc_rect.h / 2)
        p2 = (cx + math.cos(r) * inner.w / 2, cy - math.sin(r) * inner.h / 2 + px(6))
        pygame.draw.line(s, pal.joint, p1, p2, 1)
    s.set_clip(clip)
    if c.palace:
        kx = c.ox + tw - px(2) if left else c.ox + px(2)
        pygame.draw.circle(s, GOLD, (kx, top + px(4)), px(4))


def _chomper(s: pygame.Surface, c: Ctx, modifier: int) -> None:
    frame = modifier & 0x7F
    blood = bool(modifier & 0x80)
    if frame == 2:
        sep = px(1)
    elif frame == 1:
        sep = px(5)
    elif 3 <= frame <= 5:
        sep = px(3 + (frame - 2) * 3)
    else:
        sep = px(13)
    tw = c.tw
    cx = c.ox + tw // 2
    top = c.oy + px(10)
    bottom = c.floor_y
    # Ranura vertical en la pared
    slot = pygame.Rect(cx - px(16), top, px(32), bottom - top)
    pygame.draw.rect(s, (12, 10, 18), slot, border_radius=px(3))
    pygame.draw.rect(s, _shade(c.pal.face, 0.8), slot, px(2), border_radius=px(3))
    mid = (top + bottom) // 2 - px(6)
    blade_h = px(26)
    for side in (-1, 1):
        x_edge = cx + side * sep
        x_back = cx + side * px(15)
        pts = [
            (x_back, mid - blade_h),
            (x_edge, mid - px(4)),
            (x_edge, mid + px(4)),
            (x_back, mid + blade_h),
        ]
        pygame.draw.polygon(s, _shade(STEEL, 0.6), pts)
        lit = [(x_back, mid - blade_h + px(3)), (x_edge, mid - px(3)), (x_edge, mid), (x_back, mid)]
        pygame.draw.polygon(s, STEEL, lit)
        # Dientes
        for k in range(-2, 3):
            ty = mid + k * px(8)
            pygame.draw.polygon(
                s,
                (240, 244, 255),
                [(x_edge, ty - px(3)), (x_edge - side * px(4), ty), (x_edge, ty + px(3))],
            )
        if blood:
            pygame.draw.polygon(
                s,
                (150, 10, 14),
                [
                    (x_edge, mid - px(10)),
                    (x_edge - side * px(5), mid),
                    (x_edge, mid + px(14)),
                    (x_back - side * px(4), mid + px(4)),
                ],
            )
    if blood:
        pygame.draw.ellipse(s, (110, 8, 12), (cx - px(10), bottom - px(3), px(20), px(6)))


def _torch_base(s: pygame.Surface, c: Ctx) -> None:
    """Soporte de hierro y mango; la llama la pinta ``draw_torch_flame``."""
    cx = c.ox + c.tw // 2
    cy = c.oy + c.th // 2 - px(10)
    pygame.draw.rect(s, IRON, (cx - px(9), cy + px(16), px(18), px(5)), border_radius=px(2))
    pygame.draw.line(s, IRON_HI, (cx - px(9), cy + px(16)), (cx + px(9), cy + px(16)), 1)
    pygame.draw.rect(s, IRON, (cx - px(2), cy + px(8), px(4), px(14)))
    pygame.draw.polygon(
        s,
        (110, 66, 32),
        [
            (cx - px(4), cy + px(2)),
            (cx + px(4), cy + px(2)),
            (cx + px(3), cy + px(16)),
            (cx - px(3), cy + px(16)),
        ],
    )
    pygame.draw.line(s, (150, 96, 50), (cx - px(3), cy + px(3)), (cx - px(2), cy + px(15)), 1)
    pygame.draw.ellipse(s, IRON, (cx - px(6), cy - px(1), px(12), px(5)))
    # Hollín en la pared sobre la llama
    soot = pygame.Surface((px(30), px(50)), pygame.SRCALPHA)
    for i in range(soot.get_height()):
        a = int(70 * (i / soot.get_height()) ** 1.5)
        pygame.draw.line(soot, (0, 0, 0, a), (px(6), i), (soot.get_width() - px(6), i))
    soot = pygame.transform.box_blur(soot, px(3))
    s.blit(soot, (cx - px(15), cy - px(54)))


def _wall(s: pygame.Surface, c: Ctx) -> None:
    """Bloque de sillería que ocupa la celda; su cara superior queda a la
    altura del suelo de la fila de arriba."""
    tw = c.tw
    pal = c.pal
    top_y = c.oy - LAYOUT.floor_face - LAYOUT.floor_top
    body = pygame.Rect(c.ox, top_y + LAYOUT.floor_top, tw, c.bottom - top_y - LAYOUT.floor_top)
    _vgrad(s, body, pal.face, _shade(pal.face, 0.78))
    rng = random.Random(c.variant * 13 + 5)
    course = px(21)
    y = body.y
    row = 0
    while y < body.bottom:
        h = min(course, body.bottom - y)
        x = c.ox - (rng.randint(0, tw // 2) if row % 2 else 0)
        while x < c.ox + tw:
            bw = rng.randint(tw // 3, tw * 2 // 3)
            r = pygame.Rect(x, y, bw, h).clip(body)
            if r.w > 0:
                col = _shade(pal.face, rng.uniform(0.85, 1.12))
                pygame.draw.rect(s, col, r.inflate(-px(1), -px(1)))
                pygame.draw.line(s, _shade(col, 1.2), r.topleft, (r.right - 1, r.top), 1)
                pygame.draw.line(
                    s, _shade(col, 0.6), (r.left, r.bottom - 1), (r.right - 1, r.bottom - 1), 1
                )
            x += bw
        y += course
        row += 1
    top = pygame.Rect(c.ox, top_y, tw, LAYOUT.floor_top)
    _vgrad(s, top, _shade(pal.top, 0.7), pal.top)
    pygame.draw.line(s, pal.top_hi, (c.ox, top.bottom - 1), (c.ox + tw - 1, top.bottom - 1), px(1))
    if c.left_open:
        pygame.draw.line(s, _shade(pal.face, 1.25), (c.ox, top_y), (c.ox, c.bottom), px(2))
    if c.right_open:
        pygame.draw.line(
            s, pal.face_dark, (c.ox + tw - px(2), top_y), (c.ox + tw - px(2), c.bottom), px(3)
        )


def _skeleton(s: pygame.Surface, c: Ctx) -> None:
    bone = (226, 222, 204)
    dark = (120, 110, 96)
    y = c.floor_y - px(3)
    x0 = c.ox + c.tw // 5
    pygame.draw.circle(s, dark, (x0, y - px(3)), px(6))
    pygame.draw.circle(s, bone, (x0, y - px(4)), px(5))
    pygame.draw.circle(s, (20, 12, 16), (x0 + px(2), y - px(5)), px(1) + 1)
    pygame.draw.line(s, dark, (x0 + px(5), y), (x0 + c.tw // 2, y), px(3))
    pygame.draw.line(s, bone, (x0 + px(5), y - px(1)), (x0 + c.tw // 2, y - px(1)), px(2))
    for i in range(4):
        rx = x0 + px(10) + i * px(6)
        pygame.draw.arc(s, bone, (rx - px(3), y - px(7), px(6), px(9)), 0, math.pi, px(1))
    hx = x0 + c.tw // 2
    pygame.draw.line(s, bone, (hx, y), (hx + px(14), y - px(2)), px(2))
    pygame.draw.line(s, bone, (hx + px(14), y - px(2)), (hx + px(26), y), px(2))
    pygame.draw.line(s, bone, (hx, y), (hx + px(16), y + px(1)), px(2))


def _sword(s: pygame.Surface, c: Ctx) -> None:
    y = c.floor_y - px(2)
    x0, x1 = c.ox + px(8), c.ox + c.tw - px(16)
    pygame.draw.polygon(s, _shade(STEEL, 0.6), [(x0, y), (x1, y - px(2)), (x1, y + px(1))])
    pygame.draw.line(s, STEEL, (x0 + px(2), y - px(1)), (x1, y - px(2)), px(1))
    pygame.draw.line(s, (255, 255, 255), (x0 + px(20), y - px(1)), (x0 + px(34), y - px(2)), 1)
    pygame.draw.line(s, GOLD, (x1, y - px(6)), (x1, y + px(4)), px(2))
    pygame.draw.line(s, (90, 50, 30), (x1, y - px(1)), (x1 + px(8), y - px(1)), px(3))
    pygame.draw.circle(s, GOLD, (x1 + px(10), y - px(1)), px(2))


def _balcony(s: pygame.Surface, c: Ctx, *, left: bool) -> None:
    """Media ventana al exterior (palacio): arco con cielo nocturno."""
    tw = c.tw
    win = pygame.Rect(
        c.ox + (px(14) if left else 0), c.oy + px(24), tw - px(14), c.floor_y - c.oy - px(30)
    )
    _vgrad(s, win, (18, 22, 70), (50, 56, 120))
    rng = random.Random(c.variant + (3 if left else 9))
    for _ in range(8):
        sx = rng.randint(win.left, win.right - 1)
        sy = rng.randint(win.top, win.top + win.h * 2 // 3)
        s.fill((230, 230, 255), (sx, sy, 2, 2))
    arc = pygame.Rect(c.ox if left else c.ox - tw, c.oy + px(16), tw * 2, px(70))
    clip = s.get_clip()
    s.set_clip(pygame.Rect(c.ox, c.oy, tw, c.th))
    pygame.draw.ellipse(s, c.pal.column, arc, px(8))
    s.set_clip(clip)
    jamb = pygame.Rect(
        c.ox if left else c.ox + tw - px(14), c.oy + px(40), px(14), c.floor_y - c.oy - px(40)
    )
    _hgrad_cyl(s, jamb, c.pal.column)
    # Balaustrada
    rail_y = c.floor_y - px(30)
    pygame.draw.line(s, c.pal.column, (win.left, rail_y), (win.right, rail_y), px(4))
    for bx in range(win.left + px(6), win.right, px(12)):
        pygame.draw.line(
            s, _shade(c.pal.column, 0.85), (bx, rail_y), (bx, c.floor_y - px(2)), px(3)
        )


def _lattice(s: pygame.Surface, c: Ctx, kind: int) -> None:
    wood = (96, 62, 40) if c.palace else (70, 72, 90)
    hi = _shade(wood, 1.4)
    tw, th = c.tw, c.th
    if kind == 25:  # columna de celosía
        r = pygame.Rect(c.ox + tw // 2 - px(5), c.oy, px(10), th)
        _hgrad_cyl(s, r, wood)
        return
    if kind in (28, 29):  # bordes
        x = c.ox if kind == 28 else c.ox + tw - px(8)
        _hgrad_cyl(s, pygame.Rect(x, c.oy, px(8), th), wood)
        return
    area = pygame.Rect(c.ox, c.oy, tw, th if kind == 26 else px(40))
    step = px(16)
    clip = s.get_clip()
    s.set_clip(area)
    for d in range(-area.h, area.w + area.h, step):
        pygame.draw.line(s, wood, (area.x + d, area.y), (area.x + d + area.h, area.bottom), px(3))
        pygame.draw.line(s, wood, (area.x + d + area.h, area.y), (area.x + d, area.bottom), px(3))
        pygame.draw.line(s, hi, (area.x + d, area.y), (area.x + d + area.h, area.bottom), 1)
    s.set_clip(clip)
    pygame.draw.rect(s, wood, area, px(3))


# ---------------------------------------------------------------------------
# Composición, caché y API
# ---------------------------------------------------------------------------

_FLOORED: frozenset[int] = frozenset(
    {1, 2, 3, 4, 5, 6, 7, 8, 10, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23, 24, 25, 30}
)
"""Tiles que llevan losa (canon ``tile_is_floor`` + rejas)."""

FRONT_TILES: frozenset[int] = frozenset({3, 8, 9})
"""Columnas: se pintan por DELANTE de los personajes (pasan por detrás)."""


def has_floor(tile_value: int) -> bool:
    return tile_value in _FLOORED or tile_value == 20


def _paint(tile: int, modifier: int, c: Ctx) -> pygame.Surface:
    s = _new_sprite()
    if tile == 20:
        _wall(s, c)
        return s
    if tile == 11:
        _loose(s, c, modifier)
        return s
    if tile in _FLOORED:
        _slab(s, c, c.ox, c.top_y, cracked=tile == 5)
    if tile == 2:
        _spikes(s, c, modifier)
    elif tile == 4:
        _gate(s, c, modifier)
    elif tile == 6:
        _plate(s, c, bool(modifier), (160, 60, 50))
    elif tile == 15:
        _plate(s, c, bool(modifier), GOLD)
    elif tile in (7, 12):
        _doortop(s, c)
    elif tile == 10:
        _potion(s, c, modifier)
    elif tile == 13:
        _mirror(s, c)
    elif tile in (14, 30):
        _debris(s, c)
        if tile == 30:
            _torch_base(s, c)
    elif tile in (16, 17):
        _door_half(s, c, left=tile == 16, open_=bool(modifier))
    elif tile == 18:
        _chomper(s, c, modifier)
    elif tile == 19:
        _torch_base(s, c)
    elif tile == 21:
        _skeleton(s, c)
    elif tile == 22:
        _sword(s, c)
    elif tile in (23, 24):
        _balcony(s, c, left=tile == 23)
    elif tile in (25, 26, 27, 28, 29):
        _lattice(s, c, tile)
    return s


def _tint(c: RGB, t: RGB) -> RGB:
    return (c[0] * t[0] // 255, c[1] * t[1] // 255, c[2] * t[2] // 255)


@functools.lru_cache(maxsize=32)
def style_ctx(style: str) -> tuple[StonePal, bool]:
    """Paleta de piedra y tipo (palacio o no) de un estilo: ``dungeon``,
    ``palace`` o la clave de un tema de nivel (tinta la paleta base)."""
    if style == "dungeon":
        return DUNGEON, False
    if style == "palace":
        return PALACE, True
    theme: LevelTheme = theme_by_key(style)
    base = PALACE if theme.palace else DUNGEON
    t = theme.tile_tint
    pal = StonePal(
        top=_tint(base.top, t),
        top_hi=_tint(base.top_hi, t),
        face=_tint(base.face, t),
        face_dark=_tint(base.face_dark, t),
        joint=_tint(base.joint, t),
        column=_tint(base.column, t),
        trim=base.trim,
    )
    return pal, theme.palace


def _style(palace: bool, theme: str | None) -> str:
    return theme if theme is not None else ("palace" if palace else "dungeon")


@functools.lru_cache(maxsize=1536)
def _sprite(
    tile: int, modifier: int, style: str, variant: int, edges: tuple[bool, bool]
) -> pygame.Surface:
    pal, palace = style_ctx(style)
    c = Ctx(pal, palace, variant, edges[0], edges[1])
    return _paint(tile, modifier, c)


@functools.lru_cache(maxsize=128)
def _front_sprite(tile: int, style: str) -> pygame.Surface:
    pal, palace = style_ctx(style)
    c = Ctx(pal, palace, 0, False, False)
    s = _new_sprite()
    if tile == 3:
        _pillar_front(s, c)
    elif tile == 8:
        _bigpillar_bottom_front(s, c)
    elif tile == 9:
        _bigpillar_top_front(s, c)
    return s


def mod_key(tile: int, modifier: int) -> int:
    """Sólo el estado que cambia el dibujo entra en la clave de caché."""
    if tile in (2, 4, 10, 11, 18, 16, 17):
        return modifier
    if tile in (6, 15):
        return 1 if modifier else 0
    return 0


def draw_tile(
    surf: pygame.Surface,
    tile_value: int,
    x: int,
    y: int,
    modifier: int = 0,
    *,
    palace: bool = False,
    variant: int = 0,
    edges: tuple[bool, bool] = (False, False),
    theme: str | None = None,
) -> None:
    """Pinta el tile con la esquina superior izquierda de su celda en
    ``(x, y)``. ``edges``: (izquierda, derecha) sin suelo al lado;
    ``theme``: clave del tema del nivel (si no, mazmorra/palacio)."""
    if tile_value == 0:
        return
    img = _sprite(
        tile_value, mod_key(tile_value, modifier), _style(palace, theme), variant % 8, edges
    )
    surf.blit(img, (x - PADX, y - EXT_TOP))


def draw_tile_front(
    surf: pygame.Surface,
    tile_value: int,
    x: int,
    y: int,
    *,
    palace: bool = False,
    theme: str | None = None,
) -> None:
    """Capa delantera (fustes de columnas), tras los personajes."""
    if tile_value in FRONT_TILES:
        surf.blit(_front_sprite(tile_value, _style(palace, theme)), (x - PADX, y - EXT_TOP))


def draw_falling_slab(
    surf: pygame.Surface, x: int, top: int, *, palace: bool = False, theme: str | None = None
) -> None:
    """Losa suelta cayendo: sólo la losa, con su cara superior en ``top``."""
    img = _sprite(1, 0, _style(palace, theme), 3, (True, True))
    c_top = EXT_TOP + LAYOUT.tile_h - LAYOUT.floor_face - LAYOUT.floor_top
    h = LAYOUT.floor_top + LAYOUT.floor_face + EXT_BOT // 2
    surf.blit(img, (x - PADX, top), pygame.Rect(0, c_top, img.get_width(), h))


def torch_flame_px(col: int, row: int) -> tuple[int, int]:
    """Base de la llama de la antorcha de la celda (coordenadas del lienzo)."""
    cx = col * LAYOUT.tile_w + LAYOUT.tile_w // 2
    cy = LAYOUT.hud_top + row * LAYOUT.tile_h + LAYOUT.tile_h // 2 - px(10)
    return cx, cy


def draw_torch_flame(surf: pygame.Surface, cx: int, cy: int, t: float, seed: int = 0) -> None:
    """Llama animada en tres capas (exterior, media, núcleo) con lengüetas
    que se mecen; ``(cx, cy)`` es la boca de la antorcha."""
    ph = seed * 1.37
    sway = math.sin(t * 9.0 + ph) * 0.5 + math.sin(t * 15.3 + ph * 2) * 0.3
    flick = 0.85 + 0.15 * math.sin(t * 21.0 + ph * 3) + 0.08 * math.sin(t * 33.0 + ph)
    layers = (
        ((230, 90, 30), 1.0, 1.0),
        ((255, 170, 50), 0.72, 0.8),
        ((255, 236, 170), 0.42, 0.55),
    )
    for color, wk, hk in layers:
        w = px(9) * wk
        h = px(30) * hk * flick
        tipx = cx + sway * px(5) * hk
        pts = [
            (cx - w, cy + px(2)),
            (cx - w * 0.8, cy - h * 0.35),
            (cx - w * 0.3 + sway * px(2), cy - h * 0.7),
            (tipx, cy - h),
            (cx + w * 0.35 + sway * px(2), cy - h * 0.65),
            (cx + w * 0.85, cy - h * 0.3),
            (cx + w, cy + px(2)),
        ]
        pygame.draw.polygon(surf, color, pts)
    # Lengüeta suelta que se desprende
    k = (t * 2.3 + seed * 0.37) % 1.0
    if k < 0.5:
        fy = cy - px(30) * (0.9 + k)
        fx = cx + sway * px(6)
        r = max(1, int(px(3) * (1 - k * 2)))
        pygame.draw.circle(surf, (255, 190, 80), (int(fx), int(fy)), r)
