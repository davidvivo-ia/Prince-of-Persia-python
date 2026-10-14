"""Personajes HD: esqueleto con poses canon (``poses``) vestido por
personaje y pintado con volumen.

Cada sprite se dibuja supermuestreado (x2) con miembros cónicos de tres
tonos (sombra, base, brillo), contorno oscuro y se reduce con filtrado:
bordes suaves a la resolución HD. Los sprites se cachean por
``(frame, paleta, dirección)`` — un frame canon es una pose fija, así
que pintar a 60 fps cuesta sólo un ``blit``.
"""

from __future__ import annotations

import math
from collections import OrderedDict
from dataclasses import dataclass, replace
from enum import IntEnum

import pygame

from pop2026canon.presentation.layout import LAYOUT
from pop2026canon.presentation.poses import (
    HEAD_R,
    ROW_UNITS,
    Joints,
    Pose,
    pose_for,
    solve,
)


class CharPalette(IntEnum):
    """Variantes de vestuario por tipo de char."""

    KID = 0
    SHADOW = 1
    GUARD = 2
    SKELETON = 3
    PRINCESS = 4
    VIZIER = 5
    MOUSE = 6


RGB = tuple[int, int, int]
Vec = tuple[float, float]


@dataclass(frozen=True, slots=True)
class Outfit:
    skin: RGB
    hair: RGB
    shirt: RGB
    pants: RGB
    sash: RGB
    shoes: RGB
    trim: RGB
    head: str = "kid"
    """``kid`` | ``turban`` | ``tall_turban`` | ``long_hair`` | ``skull``."""
    vest: RGB | None = None
    robe: bool = False
    beard: bool = False
    baggy: bool = False
    bones: bool = False
    glow_eyes: bool = False
    alpha: int = 255
    eye: RGB = (24, 14, 10)


OUTFITS: dict[CharPalette, Outfit] = {
    CharPalette.KID: Outfit(
        skin=(222, 164, 118),
        hair=(62, 32, 18),
        shirt=(238, 234, 220),
        pants=(226, 222, 206),
        sash=(198, 40, 30),
        shoes=(176, 140, 100),
        trim=(232, 192, 64),
    ),
    CharPalette.SHADOW: Outfit(
        skin=(40, 34, 62),
        hair=(16, 12, 26),
        shirt=(46, 40, 72),
        pants=(42, 36, 66),
        sash=(90, 40, 120),
        shoes=(20, 16, 30),
        trim=(120, 90, 170),
        glow_eyes=True,
        alpha=232,
        eye=(235, 245, 255),
    ),
    CharPalette.GUARD: Outfit(
        skin=(168, 116, 80),
        hair=(26, 18, 16),
        shirt=(64, 78, 140),
        pants=(58, 62, 104),
        sash=(214, 170, 60),
        shoes=(64, 38, 24),
        trim=(226, 214, 186),
        head="turban",
        vest=(142, 34, 38),
        beard=True,
        baggy=True,
    ),
    CharPalette.SKELETON: Outfit(
        skin=(226, 222, 204),
        hair=(226, 222, 204),
        shirt=(226, 222, 204),
        pants=(226, 222, 204),
        sash=(120, 110, 96),
        shoes=(200, 196, 180),
        trim=(160, 150, 130),
        head="skull",
        bones=True,
    ),
    CharPalette.PRINCESS: Outfit(
        skin=(232, 178, 136),
        hair=(48, 24, 40),
        shirt=(236, 120, 170),
        pants=(236, 120, 170),
        sash=(232, 192, 64),
        shoes=(120, 50, 90),
        trim=(250, 220, 120),
        head="long_hair",
        robe=True,
    ),
    CharPalette.VIZIER: Outfit(
        skin=(176, 122, 88),
        hair=(16, 10, 10),
        shirt=(74, 24, 62),
        pants=(60, 18, 50),
        sash=(224, 180, 64),
        shoes=(30, 14, 22),
        trim=(232, 192, 64),
        head="tall_turban",
        robe=True,
        beard=True,
    ),
    CharPalette.MOUSE: Outfit(
        skin=(150, 140, 150),
        hair=(110, 100, 110),
        shirt=(150, 140, 150),
        pants=(150, 140, 150),
        sash=(150, 140, 150),
        shoes=(220, 150, 160),
        trim=(220, 150, 160),
    ),
}

GUARD_WARDROBE: dict[int, tuple[RGB, RGB, RGB, RGB]] = {
    1: ((64, 78, 140), (58, 62, 104), (142, 34, 38), (226, 214, 186)),
    2: ((150, 40, 44), (96, 32, 40), (60, 66, 120), (236, 224, 200)),
    3: ((54, 110, 70), (44, 76, 56), (120, 90, 40), (214, 206, 170)),
    4: ((190, 110, 40), (120, 70, 36), (40, 120, 130), (240, 232, 214)),
    5: ((110, 54, 130), (72, 40, 90), (200, 160, 60), (230, 220, 240)),
    6: ((120, 80, 50), (84, 56, 36), (170, 60, 50), (206, 190, 160)),
    7: ((40, 60, 110), (34, 44, 80), (150, 120, 50), (200, 206, 220)),
    8: ((96, 100, 112), (66, 70, 80), (40, 110, 120), (216, 220, 230)),
    9: ((190, 150, 70), (130, 100, 50), (110, 50, 40), (240, 230, 190)),
    10: ((226, 222, 210), (160, 160, 170), (200, 160, 60), (240, 236, 220)),
    11: ((36, 32, 40), (28, 26, 34), (160, 30, 40), (210, 200, 190)),
    12: ((30, 26, 36), (24, 22, 30), (190, 150, 50), (120, 40, 60)),
    13: ((64, 78, 140), (58, 62, 104), (142, 34, 38), (226, 214, 186)),
    14: ((64, 78, 140), (58, 62, 104), (142, 34, 38), (226, 214, 186)),
}
"""Vestuario de los guardias por nivel: (camisa, pantalón, chaleco,
turbante). Como en el original, cada nivel tiene sus colores."""


def outfit_for(palette: CharPalette, variant: int = 0) -> Outfit:
    """Vestuario de un personaje; ``variant`` es el nivel para los guardias."""
    base = OUTFITS.get(palette, OUTFITS[CharPalette.KID])
    if palette is CharPalette.GUARD and variant in GUARD_WARDROBE:
        shirt, pants, vest, turban = GUARD_WARDROBE[variant]
        return replace(base, shirt=shirt, pants=pants, vest=vest, trim=turban)
    return base


OUTLINE: RGB = (16, 10, 22)
STEEL: RGB = (214, 220, 234)
STEEL_DARK: RGB = (120, 128, 150)
GOLD: RGB = (232, 192, 64)
LIGHT: Vec = (0.42, -0.62)
"""Dirección de la luz principal en el sprite (arriba y por delante)."""

SS = 2
"""Supermuestreo del dibujo."""


def _shade(c: RGB, k: float) -> RGB:
    return (min(255, int(c[0] * k)), min(255, int(c[1] * k)), min(255, int(c[2] * k)))


def _tint(c: RGB, add: int) -> RGB:
    return (min(255, c[0] + add), min(255, c[1] + add), min(255, c[2] + add))


def _norm(v: Vec) -> Vec:
    d = math.hypot(*v) or 1.0
    return v[0] / d, v[1] / d


_LIGHT = _norm(LIGHT)


class _Pen:
    """Dibujo en unidades del esqueleto sobre la superficie supermuestreada."""

    def __init__(self, surf: pygame.Surface, origin: Vec, k: float) -> None:
        self.s = surf
        self.ox, self.oy = origin
        self.k = k

    def p(self, v: Vec) -> tuple[int, int]:
        return round(self.ox + v[0] * self.k), round(self.oy + v[1] * self.k)

    def r(self, units: float) -> int:
        return max(1, round(units * self.k))

    def circle(self, c: RGB, at: Vec, radius: float) -> None:
        pygame.draw.circle(self.s, c, self.p(at), self.r(radius))

    def poly(self, c: RGB, pts: list[Vec]) -> None:
        pygame.draw.polygon(self.s, c, [self.p(q) for q in pts])

    def line(self, c: RGB, a: Vec, b: Vec, width: float) -> None:
        pygame.draw.line(self.s, c, self.p(a), self.p(b), self.r(width))

    def ellipse(self, c: RGB, center: Vec, rx: float, ry: float) -> None:
        cx, cy = self.p(center)
        w, h = self.r(rx * 2), self.r(ry * 2)
        pygame.draw.ellipse(self.s, c, (cx - w // 2, cy - h // 2, w, h))

    def capsule(self, c: RGB, a: Vec, b: Vec, ra: float, rb: float) -> None:
        d = _norm((b[0] - a[0], b[1] - a[1]))
        n = (-d[1], d[0])
        pts = [
            (a[0] + n[0] * ra, a[1] + n[1] * ra),
            (b[0] + n[0] * rb, b[1] + n[1] * rb),
            (b[0] - n[0] * rb, b[1] - n[1] * rb),
            (a[0] - n[0] * ra, a[1] - n[1] * ra),
        ]
        self.poly(c, pts)
        self.circle(c, a, ra)
        self.circle(c, b, rb)

    def limb(self, base: RGB, a: Vec, b: Vec, ra: float, rb: float) -> None:
        """Miembro con volumen: sombra, base desplazada a la luz, brillo."""
        self.capsule(_shade(base, 0.62), a, b, ra, rb)
        o = 0.2
        la = (a[0] + _LIGHT[0] * ra * o, a[1] + _LIGHT[1] * ra * o)
        lb = (b[0] + _LIGHT[0] * rb * o, b[1] + _LIGHT[1] * rb * o)
        self.capsule(base, la, lb, ra * 0.78, rb * 0.78)
        h = 0.5
        ha = (a[0] + _LIGHT[0] * ra * h, a[1] + _LIGHT[1] * ra * h)
        hb = (b[0] + _LIGHT[0] * rb * h, b[1] + _LIGHT[1] * rb * h)
        self.capsule(_tint(base, 28), ha, hb, ra * 0.26, rb * 0.26)


# ---------------------------------------------------------------------------
# Partes del cuerpo
# ---------------------------------------------------------------------------


def _frame(angle: float) -> tuple[Vec, Vec]:
    """(arriba, delante) de un segmento inclinado ``angle`` grados."""
    a = math.radians(angle)
    return (math.sin(a), -math.cos(a)), (math.cos(a), math.sin(a))


def _at(o: Vec, up: Vec, fw: Vec, f: float, u: float) -> Vec:
    return o[0] + fw[0] * f + up[0] * u, o[1] + fw[1] * f + up[1] * u


def _leg(pen: _Pen, o: Outfit, j: Joints, near: bool, far_k: float) -> None:
    k = 1.0 if near else far_k
    hip = j.hip
    knee = j.knee_n if near else j.knee_f
    ankle = j.ankle_n if near else j.ankle_f
    toe = j.toe_n if near else j.toe_f
    if o.bones:
        bone = _shade(o.skin, k)
        pen.line(_shade(bone, 0.6), hip, knee, 1.6)
        pen.line(bone, hip, knee, 1.1)
        pen.line(_shade(bone, 0.6), knee, ankle, 1.4)
        pen.line(bone, knee, ankle, 0.9)
        pen.circle(bone, knee, 1.5)
        pen.line(bone, ankle, toe, 1.0)
        return
    pants = _shade(o.pants, k)
    if o.baggy:
        mid = ((knee[0] + ankle[0]) / 2, (knee[1] + ankle[1]) / 2)
        pen.limb(pants, hip, knee, 3.8, 3.4)
        pen.limb(pants, knee, mid, 3.4, 3.2)
        pen.limb(pants, mid, ankle, 3.2, 1.9)
    else:
        pen.limb(pants, hip, knee, 3.5, 2.6)
        pen.limb(pants, knee, ankle, 2.5, 1.8)
    # Pie / zapato con suela
    shoe = _shade(o.shoes, k)
    pen.limb(shoe, ankle, toe, 1.9, 1.2)
    if o.head in {"turban", "tall_turban"}:
        # Babucha con punta curva
        d = _norm((toe[0] - ankle[0], toe[1] - ankle[1]))
        tip = (toe[0] + d[0] * 1.6, toe[1] + d[1] * 1.6 - 1.2)
        pen.line(shoe, toe, tip, 0.9)


def _torso(pen: _Pen, o: Outfit, j: Joints) -> None:
    up, fw = _frame(j.lean)
    hip = j.hip

    def at(f: float, u: float) -> Vec:
        return _at(hip, up, fw, f, u)

    if o.bones:
        bone = o.skin
        dark = _shade(bone, 0.55)
        # Columna, costillas y pelvis
        pen.line(dark, at(-1.2, 0), at(-1.0, 15), 1.6)
        pen.line(bone, at(-1.2, 0), at(-1.0, 15), 1.0)
        for i in range(5):
            u = 6.0 + i * 1.9
            w = 3.6 - abs(i - 2) * 0.35
            pen.line(dark, at(-1.0, u), at(w, u - 1.2), 1.2)
            pen.line(bone, at(-1.0, u), at(w, u - 1.2), 0.7)
        pen.poly(bone, [at(-3.2, 0.5), at(3.0, 0.5), at(2.0, -1.8), at(-2.2, -1.8)])
        pen.poly(dark, [at(-1.0, -0.2), at(1.0, -0.2), at(0.0, -1.4)])
        return
    shirt = o.shirt
    body = [
        at(-3.6, -0.4),
        at(3.9, -0.4),
        at(4.4, 4.0),
        at(5.0, 9.4),
        at(3.4, 14.0),
        at(0.4, 15.2),
        at(-3.8, 13.6),
        at(-3.5, 7.0),
    ]
    pen.poly(_shade(shirt, 0.66), body)
    lit = [
        at(-1.8, 0.2),
        at(3.4, 0.2),
        at(3.9, 4.0),
        at(4.4, 9.2),
        at(2.9, 13.2),
        at(0.5, 14.2),
        at(-2.2, 12.6),
        at(-2.0, 6.5),
    ]
    pen.poly(shirt, lit)
    pen.poly(_tint(shirt, 26), [at(1.8, 8.0), at(4.0, 9.2), at(2.9, 12.6), at(1.6, 12.0)])
    # Pliegues de la camisa
    pen.line(_shade(shirt, 0.8), at(0.8, 2.5), at(1.6, 8.5), 0.45)
    pen.line(_shade(shirt, 0.8), at(-1.4, 3.0), at(-0.8, 9.5), 0.4)
    if o.vest is not None:
        vest = o.vest
        pen.poly(
            _shade(vest, 0.7),
            [at(-3.7, 2.0), at(0.4, 2.0), at(1.4, 13.6), at(-3.7, 13.4)],
        )
        pen.poly(vest, [at(-2.4, 2.4), at(0.1, 2.4), at(1.0, 13.0), at(-2.6, 12.8)])
        pen.line(o.trim, at(0.4, 2.0), at(1.4, 13.6), 0.5)
        pen.poly(
            vest,
            [at(3.6, 2.0), at(4.4, 4.0), at(4.8, 9.2), at(3.2, 13.6), at(2.4, 13.0), at(2.8, 2.4)],
        )
    # Faja / cinturón con nudo y caída por detrás
    sash = o.sash
    band = [at(-3.7, 1.4), at(4.0, 1.4), at(4.3, 4.4), at(-3.6, 4.4)]
    pen.poly(_shade(sash, 0.7), band)
    pen.poly(sash, [at(-2.6, 1.8), at(3.6, 1.8), at(3.9, 3.6), at(-2.6, 3.6)])
    pen.line(_tint(sash, 40), at(-1.5, 3.4), at(3.6, 3.4), 0.35)
    if not o.robe:
        tail = [at(-3.4, 2.6), at(-6.4, -3.2), at(-5.0, -3.8), at(-2.6, 1.2)]
        pen.poly(_shade(sash, 0.75), tail)
    # Faldón de la camisa por debajo de la faja (kid)
    if not o.robe and o.vest is None:
        pen.poly(_shade(shirt, 0.8), [at(-3.6, 1.5), at(4.0, 1.5), at(4.4, -1.2), at(-4.0, -1.0)])


def _robe(pen: _Pen, o: Outfit, j: Joints) -> None:
    up, fw = _frame(j.lean)
    hip = j.hip
    pts = (j.knee_n, j.knee_f, j.ankle_n, j.ankle_f)
    front = max(p[0] for p in pts) + 3.0
    back = min(p[0] for p in pts) - 3.0
    hem = max(j.ankle_n[1], j.ankle_f[1]) + 0.3
    w_back = _at(hip, up, fw, -4.2, 3.0)
    w_front = _at(hip, up, fw, 4.6, 3.0)
    skirt = [w_back, w_front, (front, hem), (back, hem)]
    pen.poly(_shade(o.shirt, 0.62), skirt)
    inner = [
        (w_back[0] + 1.6, w_back[1]),
        (w_front[0] - 0.6, w_front[1]),
        (front - 1.2, hem - 0.6),
        ((front + back) / 2, hem - 0.6),
    ]
    pen.poly(o.shirt, inner)
    # Pliegues y ribete del bajo
    for t in (0.3, 0.55, 0.8):
        top = (w_back[0] + (w_front[0] - w_back[0]) * t, w_back[1] + (w_front[1] - w_back[1]) * t)
        bot = (back + (front - back) * t, hem)
        pen.line(_shade(o.shirt, 0.72), top, bot, 0.5)
    pen.line(o.trim, (back, hem - 0.4), (front, hem - 0.4), 0.9)


def _arm(pen: _Pen, o: Outfit, j: Joints, near: bool, far_k: float) -> None:
    k = 1.0 if near else far_k
    sh = j.shoulder
    el = j.elbow_n if near else j.elbow_f
    ha = j.hand_n if near else j.hand_f
    if o.bones:
        bone = _shade(o.skin, k)
        pen.line(_shade(bone, 0.6), sh, el, 1.4)
        pen.line(bone, sh, el, 0.9)
        pen.line(_shade(bone, 0.6), el, ha, 1.2)
        pen.line(bone, el, ha, 0.8)
        pen.circle(bone, el, 1.2)
        pen.circle(bone, ha, 1.1)
        return
    sleeve = _shade(o.shirt, k)
    pen.limb(sleeve, sh, el, 2.4, 2.0)
    if o.robe:
        pen.limb(sleeve, el, ha, 2.0, 2.2)  # manga ancha
        pen.circle(_shade(o.trim, k), ha, 1.0)
    else:
        mid = (el[0] + (ha[0] - el[0]) * 0.7, el[1] + (ha[1] - el[1]) * 0.7)
        pen.limb(sleeve, el, mid, 2.0, 1.7)
        pen.limb(_shade(o.skin, k), mid, ha, 1.4, 1.3)
    pen.limb(_shade(o.skin, k), ha, ha, 1.7, 1.7)


def _head(pen: _Pen, o: Outfit, j: Joints) -> None:
    up, fw = _frame(j.head_angle)
    c = j.head
    neck_base = j.neck

    def at(f: float, u: float) -> Vec:
        return _at(c, up, fw, f, u)

    if o.head == "skull":
        bone = o.skin
        pen.line(_shade(bone, 0.6), neck_base, at(-0.5, -3.5), 1.3)
        pen.circle(_shade(bone, 0.6), at(-0.2, 0.4), HEAD_R * 0.98)
        pen.circle(bone, at(0.1, 0.8), HEAD_R * 0.86)
        pen.poly(bone, [at(0.0, -2.0), at(4.2, -2.4), at(4.4, -4.6), at(0.4, -5.0)])
        pen.line(_shade(bone, 0.5), at(1.0, -3.6), at(4.2, -3.6), 0.35)
        pen.circle((20, 10, 16), at(2.6, 0.2), 1.35)
        pen.circle((255, 120, 60), at(2.8, 0.3), 0.35)
        pen.poly((40, 26, 30), [at(4.3, -1.2), at(5.0, -2.2), at(3.8, -2.0)])
        return
    skin = o.skin
    # Cuello
    pen.limb(skin, neck_base, at(-0.6, -3.6), 1.7, 1.7)
    # Pelo de la nuca (detrás de la cara)
    if o.head in ("kid", "long_hair"):
        pen.circle(_shade(o.hair, 0.8), at(-1.4, 0.8), HEAD_R * 1.02)
        lock = [at(-4.6, 1.0), at(-1.0, 1.4), at(-1.2, -4.8), at(-4.0, -5.6), at(-5.6, -2.0)]
        pen.poly(_shade(o.hair, 0.85), lock)
        if o.head == "long_hair":
            tress = [at(-5.4, 1.0), at(-1.2, 0.0), at(-2.0, -15.0), at(-5.6, -16.0), at(-7.2, -9.0)]
            pen.poly(_shade(o.hair, 0.75), tress)
            pen.line(_tint(o.hair, 20), at(-4.0, -1.0), at(-4.6, -13.0), 0.5)
    # Cara
    pen.circle(_shade(skin, 0.72), c, HEAD_R)
    pen.circle(skin, at(0.6, 0.4), HEAD_R * 0.86)
    pen.circle(_tint(skin, 22), at(2.2, 1.6), HEAD_R * 0.32)
    # Nariz, barbilla, oreja
    pen.poly(skin, [at(4.2, 1.2), at(6.0, -0.9), at(4.4, -1.2)])
    pen.poly(_shade(skin, 0.75), [at(4.4, -1.2), at(6.0, -0.9), at(5.0, -1.6)])
    pen.circle(_shade(skin, 0.7), at(-0.8, -0.4), 1.2)
    # Ojo y ceja
    eye = at(2.9, 0.5)
    if o.glow_eyes:
        pen.circle((150, 170, 255), eye, 1.3)
        pen.circle(o.eye, eye, 0.75)
    else:
        pen.ellipse((250, 246, 236), eye, 0.95, 0.65)
        pen.circle(o.eye, at(3.3, 0.5), 0.5)
    pen.line(_shade(o.hair, 0.9), at(1.8, 1.9), at(4.0, 1.7), 0.5)
    # Boca
    pen.line(_shade(skin, 0.55), at(3.4, -2.6), at(4.6, -2.4), 0.35)
    if o.beard:
        beard = [at(1.0, -1.6), at(4.8, -2.0), at(4.4, -5.6), at(2.6, -7.0), at(0.6, -4.0)]
        pen.poly(o.hair, beard)
        pen.line(o.hair, at(3.0, -1.6), at(5.6, -1.4), 0.6)  # bigote
    # Tocado
    if o.head == "kid":
        cap = [
            at(-4.8, 1.0),
            at(-3.4, 4.6),
            at(0.2, 5.8),
            at(3.6, 4.6),
            at(4.6, 2.4),
            at(1.4, 3.0),
            at(-1.8, 2.0),
        ]
        pen.poly(o.hair, cap)
        pen.poly(_tint(o.hair, 30), [at(-2.4, 4.2), at(0.4, 5.2), at(2.6, 4.4), at(0.2, 4.4)])
        pen.poly(o.hair, [at(3.0, 4.4), at(4.8, 1.6), at(5.2, 3.4)])  # flequillo
    elif o.head == "long_hair":
        cap = [at(-5.0, 0.0), at(-3.6, 4.6), at(0.6, 5.8), at(3.8, 4.4), at(4.4, 2.0), at(1.0, 3.0)]
        pen.poly(o.hair, cap)
        pen.circle(o.trim, at(1.4, 5.0), 0.8)  # diadema
    elif o.head == "turban":
        t = o.trim
        pen.ellipse(_shade(t, 0.72), at(-0.4, 3.4), 6.0, 3.6)
        pen.ellipse(t, at(0.0, 3.8), 5.4, 3.0)
        for u in (2.4, 4.0):
            pen.line(_shade(t, 0.8), at(-4.6, u), at(4.4, u + 0.6), 0.4)
        pen.circle((200, 30, 40), at(3.4, 5.4), 0.9)
        pen.circle((255, 160, 160), at(3.6, 5.6), 0.3)
    elif o.head == "tall_turban":
        t = (236, 228, 210)
        pen.ellipse(_shade(t, 0.72), at(-0.2, 5.6), 6.0, 6.0)
        pen.ellipse(t, at(0.2, 6.2), 5.2, 5.4)
        pen.line(_shade(t, 0.8), at(-4.8, 3.6), at(4.8, 4.6), 0.5)
        pen.line(_shade(t, 0.8), at(-4.0, 7.0), at(4.0, 8.6), 0.4)
        pen.circle((40, 160, 90), at(4.6, 4.6), 1.1)
        pen.circle(o.trim, at(4.6, 4.6), 0.5)
        pen.line(o.trim, at(0.6, 11.0), at(-1.6, 14.6), 0.6)  # pluma


def _blade(pen: _Pen, j: Joints) -> None:
    if j.blade is None:
        return
    a = math.radians(j.blade)
    d = (math.sin(a), math.cos(a))
    n = (-d[1], d[0])
    h = j.hand_n
    base = (h[0] + d[0] * 2.4, h[1] + d[1] * 2.4)
    tip = (h[0] + d[0] * 25.0, h[1] + d[1] * 25.0)
    mid = (h[0] + d[0] * 15.0 - n[0] * 0.9, h[1] + d[1] * 15.0 - n[1] * 0.9)
    w = 1.05
    pts = [
        (base[0] + n[0] * w, base[1] + n[1] * w),
        (mid[0] + n[0] * w * 0.85, mid[1] + n[1] * w * 0.85),
        tip,
        (mid[0] - n[0] * w * 0.9, mid[1] - n[1] * w * 0.9),
        (base[0] - n[0] * w, base[1] - n[1] * w),
    ]
    pen.poly(STEEL_DARK, pts)
    inner = [
        (base[0] + n[0] * w * 0.4, base[1] + n[1] * w * 0.4),
        (mid[0] + n[0] * w * 0.35, mid[1] + n[1] * w * 0.35),
        tip,
        (mid[0] - n[0] * w * 0.5, mid[1] - n[1] * w * 0.5),
        (base[0] - n[0] * w * 0.5, base[1] - n[1] * w * 0.5),
    ]
    pen.poly(STEEL, inner)
    pen.line((255, 255, 255), base, mid, 0.25)
    # Guarda, puño y pomo
    g = (h[0] + d[0] * 1.8, h[1] + d[1] * 1.8)
    pen.line(
        _shade(GOLD, 0.6),
        (g[0] + n[0] * 2.8, g[1] + n[1] * 2.8),
        (g[0] - n[0] * 2.8, g[1] - n[1] * 2.8),
        1.0,
    )
    pen.line(
        GOLD, (g[0] + n[0] * 2.6, g[1] + n[1] * 2.6), (g[0] - n[0] * 2.6, g[1] - n[1] * 2.6), 0.55
    )
    pen.circle(GOLD, (h[0] - d[0] * 1.6, h[1] - d[1] * 1.6), 0.9)


def _item(pen: _Pen, j: Joints, item: str) -> None:
    if item == "flask":
        h = j.hand_n
        body = (h[0] + 0.4, h[1] - 1.6)
        pen.circle((150, 180, 210), body, 2.2)
        pen.circle((210, 40, 50), (body[0], body[1] + 0.5), 1.7)
        pen.line((170, 200, 230), body, (body[0] + 0.3, body[1] - 3.2), 0.9)
        pen.circle((255, 255, 255), (body[0] - 0.8, body[1] - 0.6), 0.45)
    elif item == "slash":
        hip = j.hip
        pen.line((150, 0, 0), (hip[0] - 5, hip[1] + 2), (hip[0] + 6, hip[1] - 6), 1.6)
        pen.line((220, 30, 30), (hip[0] - 4, hip[1] + 1), (hip[0] + 5, hip[1] - 5), 0.8)


# ---------------------------------------------------------------------------
# Composición y caché
# ---------------------------------------------------------------------------


def _bounds(j: Joints) -> tuple[float, float, float, float]:
    xs = [p[0] for p in j.points()]
    ys = [p[1] for p in j.points()]
    if j.blade is not None:
        a = math.radians(j.blade)
        h = j.hand_n
        xs.append(h[0] + math.sin(a) * 26)
        ys.append(h[1] + math.cos(a) * 26)
    m = 11.0
    return min(xs) - m, min(ys) - m - 6.0, max(xs) + m, max(ys) + m


def _units_px() -> float:
    """Píxeles del lienzo por unidad del esqueleto."""
    return LAYOUT.tile_h / ROW_UNITS


def _outline(src: pygame.Surface, width: int) -> pygame.Surface:
    mask = pygame.mask.from_surface(src, 20)
    sil = mask.to_surface(setcolor=(*OUTLINE, 255), unsetcolor=(0, 0, 0, 0))
    out = pygame.Surface(src.get_size(), pygame.SRCALPHA)
    for dx in (-width, 0, width):
        for dy in (-width, 0, width):
            if dx or dy:
                out.blit(sil, (dx, dy))
    out.blit(src, (0, 0))
    return out


def _render(pose: Pose, outfit: Outfit) -> tuple[pygame.Surface, tuple[int, int]]:
    """Sprite mirando a la derecha y la posición de los pies en él."""
    j = solve(pose)
    x0, y0, x1, y1 = _bounds(j)
    k = _units_px() * SS
    w = max(4, math.ceil((x1 - x0) * k))
    h = max(4, math.ceil((y1 - y0) * k))
    big = pygame.Surface((w, h), pygame.SRCALPHA)
    pen = _Pen(big, (-x0 * k, -y0 * k), k)
    far_k = 0.7
    if outfit.robe:
        _arm(pen, outfit, j, False, far_k)
        _leg(pen, outfit, j, False, far_k)
        _leg(pen, outfit, j, True, far_k)
        _robe(pen, outfit, j)
        _torso(pen, outfit, j)
    else:
        _arm(pen, outfit, j, False, far_k)
        _leg(pen, outfit, j, False, far_k)
        _leg(pen, outfit, j, True, far_k)
        _torso(pen, outfit, j)
    _head(pen, outfit, j)
    _blade(pen, j)
    _arm(pen, outfit, j, True, far_k)
    _item(pen, j, pose.item)
    big = _outline(big, max(1, round(k * 0.42)))
    small = pygame.transform.smoothscale(big, (max(1, w // SS), max(1, h // SS)))
    anchor = (round(-x0 * k / SS), round(-y0 * k / SS))
    return small, anchor


def _render_mouse(frame: int, outfit: Outfit) -> tuple[pygame.Surface, tuple[int, int]]:
    k = _units_px() * SS
    w, h = math.ceil(26 * k), math.ceil(14 * k)
    big = pygame.Surface((w, h), pygame.SRCALPHA)
    pen = _Pen(big, (8 * k, 12 * k), k)
    fur = outfit.skin
    step = 1.0 if frame % 2 else -1.0
    pen.line(_shade(fur, 0.6), (-6.0, -2.0), (-7.5, -6.0), 0.5)
    pen.line(_shade(fur, 0.6), (-7.5, -6.0), (-5.0, -8.5), 0.4)
    pen.ellipse(_shade(fur, 0.65), (0.0, -2.6), 6.4, 3.0)
    pen.ellipse(fur, (0.4, -3.0), 5.6, 2.4)
    pen.circle(fur, (5.6, -3.4), 2.2)
    pen.circle(_shade(fur, 0.8), (4.6, -5.6), 1.4)
    pen.circle(outfit.shoes, (4.6, -5.6), 0.8)
    pen.circle((10, 6, 10), (6.4, -3.8), 0.45)
    pen.circle(outfit.shoes, (7.7, -3.0), 0.5)
    for lx in (-3.0, 2.5):
        pen.line(_shade(fur, 0.55), (lx, -1.0), (lx + step * 0.8, 0.0), 0.5)
    big = _outline(big, max(1, round(k * 0.35)))
    small = pygame.transform.smoothscale(big, (w // SS, h // SS))
    return small, (round(8 * k / SS), round(12 * k / SS))


_CACHE: OrderedDict[tuple[int, int, int, int], tuple[pygame.Surface, tuple[int, int]]] = (
    OrderedDict()
)
_CACHE_MAX = 900


def sprite(
    frame: int, palette: CharPalette, facing: int, variant: int = 0
) -> tuple[pygame.Surface, tuple[int, int]]:
    """Sprite del frame (cacheado) y el punto de los pies dentro de él.
    ``variant``: el nivel, para el vestuario de los guardias."""
    right = facing == 0
    if palette is not CharPalette.GUARD:
        variant = 0
    key = (frame, int(palette), 0 if right else 1, variant)
    hit = _CACHE.get(key)
    if hit is not None:
        _CACHE.move_to_end(key)
        return hit
    outfit = outfit_for(palette, variant)
    if palette is CharPalette.MOUSE:
        img, (ax, ay) = _render_mouse(frame, outfit)
        pose_sx, alpha = 1.0, 1.0
    else:
        pose = pose_for(frame)
        img, (ax, ay) = _render(pose, outfit)
        pose_sx, alpha = pose.sx, pose.alpha
    if pose_sx != 1.0:
        w = max(1, round(img.get_width() * abs(pose_sx)))
        ax = round(ax * abs(pose_sx))
        img = pygame.transform.smoothscale(img, (w, img.get_height()))
        if pose_sx < 0:
            img = pygame.transform.flip(img, True, False)
            ax = w - ax
    if not right:
        img = pygame.transform.flip(img, True, False)
        ax = img.get_width() - ax
    a = int(outfit.alpha * alpha)
    if a < 255:
        img.set_alpha(a)
    out = (img, (ax, ay))
    _CACHE[key] = out
    if len(_CACHE) > _CACHE_MAX:
        _CACHE.popitem(last=False)
    return out


def draw_kid_frame(
    surf: pygame.Surface,
    frame_id: int,
    px_x: int,
    px_y: int,
    facing: int,
    palette: CharPalette = CharPalette.KID,
    variant: int = 0,
) -> None:
    """Dibuja el frame del char con los pies en ``(px_x, px_y)``."""
    img, (ax, ay) = sprite(frame_id, palette, facing, variant)
    surf.blit(img, (px_x - ax, px_y - ay))


WARM_FRAMES: tuple[int, ...] = (
    15,
    *range(7, 12),
    *range(121, 133),
    *range(16, 28),
    *range(34, 45),
    *range(45, 53),
    *range(102, 120),
    67,
    68,
    69,
    70,
    77,
    78,
    91,
    *range(135, 150),
    *range(150, 176),
    *range(179, 186),
)
"""Frames más frecuentes: se pre-pintan poco a poco al empezar un nivel."""


def is_cached(frame: int, palette: CharPalette, facing: int, variant: int = 0) -> bool:
    if palette is not CharPalette.GUARD:
        variant = 0
    return (frame, int(palette), 0 if facing == 0 else 1, variant) in _CACHE
