"""Cinemáticas de historia: la introducción (el palacio de noche, Jaffar,
la princesa y el reloj de arena, el joven arrojado a la mazmorra) y el
reencuentro final.

Todo es procedural y dirigido por el tiempo ``t`` (segundos desde que
empezó la cinemática): ``draw_intro(surf, t)`` y ``draw_ending(surf,
t)`` son funciones puras de dibujo, sin estado. Los subtítulos pasan
por :mod:`pop2026canon.presentation.i18n`.

Planos de la intro::

    0 ─ 7 s   el palacio bajo la luna (fondo del póster)
    7 ─ 16 s  los aposentos: Jaffar entra, planta el reloj de arena
    16 ─ 24 s la mazmorra: el joven cae, se levanta y mira a la luz

Final::

    0 ─ 12 s  los aposentos: el príncipe entra corriendo, ella va a su
              encuentro, la arena se detiene, "FIN".
"""

from __future__ import annotations

import functools
import math
import random

import pygame

from pop2026canon.presentation import fonts, poses
from pop2026canon.presentation.char_atlas import CharPalette, sprite
from pop2026canon.presentation.i18n import tr
from pop2026canon.presentation.layout import px
from pop2026canon.presentation.palette import PALETTE
from pop2026canon.presentation.poster import draw_backdrop

INTRO_DURATION: float = 24.0
ENDING_DURATION: float = 12.0

_SCENE_PALACE_END = 7.0
_SCENE_CHAMBER_END = 16.0

RGB = tuple[int, int, int]

INTRO_LINES: tuple[tuple[float, float, str], ...] = (
    (0.8, 3.8, "Persia, hace mucho tiempo."),
    (3.6, 5.6, "Mientras el sultán guerrea en tierras lejanas,"),
    (5.4, 7.4, "su visir Jaffar se adueña del palacio."),
    (10.5, 13.5, "A la princesa le concede una hora para elegir:"),
    (13.2, 16.2, "casarse con él... o morir."),
    (17.0, 19.6, "El joven que ella ama no tiene título ni nombre."),
    (19.4, 21.8, "Jaffar lo ha arrojado a las mazmorras."),
    (21.6, 24.0, "Tiene sesenta minutos."),
)
"""``(desde, hasta, texto)`` de cada subtítulo de la intro."""

ENDING_LINES: tuple[tuple[float, float, str], ...] = (
    (1.0, 4.5, "La arena se ha detenido."),
    (4.6, 8.0, "Jaffar ha caído y el palacio despierta."),
    (8.1, 12.0, "Ella nunca dudó."),
)


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _ease(x: float) -> float:
    x = _clamp01(x)
    return x * x * (3 - 2 * x)


def _fade(surf: pygame.Surface, alpha: float) -> None:
    """Velo negro con ``alpha`` 0..1."""
    if alpha <= 0:
        return
    veil = pygame.Surface(surf.get_size())
    veil.fill(PALETTE.bg)
    veil.set_alpha(int(255 * _clamp01(alpha)))
    surf.blit(veil, (0, 0))


def _letterbox(surf: pygame.Surface) -> None:
    w, h = surf.get_size()
    bar = px(34)
    pygame.draw.rect(surf, (0, 0, 0), (0, 0, w, bar))
    pygame.draw.rect(surf, (0, 0, 0), (0, h - bar, w, bar))


def _subtitles(surf: pygame.Surface, lines: tuple[tuple[float, float, str], ...], t: float) -> None:
    w, h = surf.get_size()
    y = h - px(34) - px(30)
    for start, end, text in lines:
        if not (start <= t < end + 0.4):
            continue
        a = min(_clamp01((t - start) / 0.5), _clamp01((end + 0.4 - t) / 0.4))
        txt = fonts.render(tr(text), 24, PALETTE.primary)
        shadow = fonts.render(tr(text), 24, (0, 0, 0))
        txt.set_alpha(int(255 * a))
        shadow.set_alpha(int(200 * a))
        r = txt.get_rect(center=(w // 2, y))
        surf.blit(shadow, r.move(px(1), px(1)))
        surf.blit(txt, r)


def _skip_hint(surf: pygame.Surface, t: float) -> None:
    w, h = surf.get_size()
    blink = abs(math.sin(t * 2.5)) > 0.3
    hint = fonts.render(tr("Enter para saltar"), 15, PALETTE.muted if blink else (60, 50, 70))
    surf.blit(hint, hint.get_rect(bottomright=(w - px(10), h - px(8))))


def _actor(
    surf: pygame.Surface,
    frame: int,
    palette: CharPalette,
    facing: int,
    x: int,
    y: int,
    scale: float = 1.6,
    tint: RGB = (255, 255, 255),
) -> None:
    img, (ax, ay) = sprite(frame, palette, facing)
    img = pygame.transform.smoothscale(
        img, (int(img.get_width() * scale), int(img.get_height() * scale))
    )
    if tint != (255, 255, 255):
        img.fill(tint, special_flags=pygame.BLEND_RGB_MULT)
    surf.blit(img, (x - int(ax * scale), y - int(ay * scale)))


def _run_frame(t: float, speed: float = 14.0) -> int:
    return 121 + int(t * speed) % 12


def _vizier_frame(s: float) -> int:
    """Jaffar en los aposentos: entra con paso solemne (0..3 s), señala a
    la princesa, alza los brazos para conjurar el reloj de arena y se
    queda con las manos juntas."""
    if s < 3.0:
        return poses.VIZIER_STRIDE_FIRST + int(s * 8) % 12
    if s < 3.4:
        return poses.VIZIER_POINT
    if s < 4.4:
        k = (s - 3.4) / 1.0
        span = poses.VIZIER_SUMMON_LAST - poses.VIZIER_SUMMON_FIRST
        return poses.VIZIER_SUMMON_FIRST + min(span, int(k * (span + 1)))
    if s < 6.0:
        return poses.VIZIER_SUMMON_LAST
    return poses.VIZIER_GLOAT


# ---------------------------------------------------------------------------
# Los aposentos de la princesa
# ---------------------------------------------------------------------------


@functools.lru_cache(maxsize=2)
def _chamber(w: int, h: int) -> pygame.Surface:
    """Sala de palacio: muro de arenisca, ventanal en arco con la luna,
    columnas, suelo de mármol y alfombra (estático, cacheado)."""
    surf = pygame.Surface((w, h))
    floor_y = int(h * 0.76)
    # Muro con degradado cálido
    for y in range(floor_y):
        k = y / floor_y
        c = (int(96 + 30 * k), int(66 + 18 * k), int(60 + 10 * k))
        pygame.draw.line(surf, c, (0, y), (w, y))
    # Sillares
    rng = random.Random(7)
    bh = px(34)
    for row, y in enumerate(range(0, floor_y, bh)):
        off = (row % 2) * px(40)
        for x in range(-px(80) + off, w, px(80)):
            shade = rng.randint(-8, 8)
            pygame.draw.line(surf, (70 + shade, 48 + shade, 46 + shade), (x, y), (x, y + bh), 1)
        pygame.draw.line(surf, (72, 50, 48), (0, y), (w, y), 1)
    # Ventanal en arco con cielo nocturno y luna
    ww, wh = int(w * 0.26), int(h * 0.5)
    wx, wy = w // 2 - ww // 2, int(h * 0.12)
    win = pygame.Surface((ww, wh), pygame.SRCALPHA)
    for y in range(wh):
        k = y / wh
        c = (int(10 + 30 * k), int(14 + 32 * k), int(44 + 60 * k))
        pygame.draw.line(win, c, (0, y), (ww, y))
    srng = random.Random(1989)
    for _ in range(40):
        sx, sy = srng.randrange(ww), srng.randrange(wh // 2)
        win.fill((230, 230, 255), (sx, sy, 1, 1))
    pygame.draw.circle(win, (250, 244, 210), (ww * 2 // 3, wh // 4), px(22))
    pygame.draw.circle(win, (236, 228, 190), (ww * 2 // 3 - px(6), wh // 4 - px(4)), px(6))
    # Dunas al fondo
    pts = [(0, wh)] + [
        (x, int(wh * 0.72 + math.sin(x * 0.03) * px(6))) for x in range(0, ww + px(10), px(10))
    ]
    pts.append((ww, wh))
    pygame.draw.polygon(win, (36, 30, 70), pts)
    mask = pygame.Surface((ww, wh), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), (0, ww // 2, ww, wh - ww // 2))
    pygame.draw.circle(mask, (255, 255, 255, 255), (ww // 2, ww // 2), ww // 2)
    win.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    surf.blit(win, (wx, wy))
    # Marco del arco
    for x in (wx, wx + ww - px(4)):
        pygame.draw.rect(surf, (170, 130, 80), (x, wy + ww // 2, px(4), wh - ww // 2))
    pygame.draw.circle(surf, (170, 130, 80), (wx + ww // 2, wy + ww // 2), ww // 2, px(4))
    pygame.draw.rect(surf, (96, 66, 60), (wx - px(6), wy + wh, ww + px(12), px(8)))
    # Columnas
    for cx in (int(w * 0.14), int(w * 0.86)):
        col_w = px(26)
        pygame.draw.rect(surf, (150, 112, 78), (cx - col_w // 2, int(h * 0.1), col_w, floor_y))
        pygame.draw.rect(
            surf, (196, 156, 104), (cx - col_w // 2 + px(4), int(h * 0.1), px(6), floor_y)
        )
        pygame.draw.rect(
            surf, (104, 76, 52), (cx + col_w // 2 - px(6), int(h * 0.1), px(4), floor_y)
        )
        pygame.draw.rect(
            surf,
            (176, 136, 88),
            (cx - col_w // 2 - px(6), int(h * 0.1) - px(8), col_w + px(12), px(10)),
        )
        pygame.draw.rect(
            surf,
            (176, 136, 88),
            (cx - col_w // 2 - px(6), floor_y - px(10), col_w + px(12), px(10)),
        )
    # Suelo de mármol con perspectiva
    for y in range(floor_y, h):
        k = (y - floor_y) / max(1, h - floor_y)
        c = (int(52 + 40 * k), int(40 + 30 * k), int(44 + 30 * k))
        pygame.draw.line(surf, c, (0, y), (w, y))
    for i in range(-6, 8):
        x0 = w // 2 + i * px(60)
        x1 = w // 2 + i * px(150)
        pygame.draw.line(surf, (70, 56, 60), (x0, floor_y), (x1, h), 1)
    for k in (0.12, 0.3, 0.55, 0.85):
        y = floor_y + int((h - floor_y) * k)
        pygame.draw.line(surf, (70, 56, 60), (0, y), (w, y), 1)
    # Alfombra
    carpet = [
        (w // 2 - px(120), floor_y + px(6)),
        (w // 2 + px(120), floor_y + px(6)),
        (w // 2 + px(220), h - px(10)),
        (w // 2 - px(220), h - px(10)),
    ]
    pygame.draw.polygon(surf, (120, 30, 40), carpet)
    pygame.draw.polygon(surf, (190, 150, 60), carpet, px(2))
    # Pedestal del reloj de arena
    pw = px(60)
    pygame.draw.rect(surf, (130, 100, 70), (w // 2 - pw // 2, floor_y - px(40), pw, px(44)))
    pygame.draw.rect(
        surf, (170, 136, 96), (w // 2 - pw // 2 - px(6), floor_y - px(44), pw + px(12), px(6))
    )
    return surf


def _candles(surf: pygame.Surface, t: float) -> None:
    """Luz de velas que titila en las columnas."""
    w, h = surf.get_size()
    for i, cx in enumerate((int(w * 0.14), int(w * 0.86))):
        cy = int(h * 0.36)
        flick = 0.8 + 0.2 * math.sin(t * 9 + i * 2) * math.sin(t * 5.3 + i)
        r = int(px(30) * flick)
        glow = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 170, 70, 34), (r, r), r)
        glow = pygame.transform.box_blur(glow, px(12))
        surf.blit(glow, (cx - r, cy - r), special_flags=pygame.BLEND_RGBA_ADD)
        pygame.draw.rect(surf, (230, 220, 190), (cx + px(16), cy, px(5), px(14)))
        fh = px(6) * flick
        pygame.draw.polygon(
            surf,
            (255, 220, 120),
            [(cx + px(16), cy), (cx + px(18), cy - fh - px(4)), (cx + px(21), cy)],
        )


def draw_hourglass(
    surf: pygame.Surface,
    cx: int,
    cy: int,
    size: int,
    sand: float,
    t: float,
    *,
    glow: float = 1.0,
    scale: float = 1.0,
) -> None:
    """Reloj de arena de Jaffar: ``sand`` es la fracción que queda arriba
    (1 = recién vuelto, 0 = agotado); ``glow`` la intensidad del aura
    roja; ``(cx, cy)`` la base. ``size`` es la altura en píxeles."""
    size = int(size * scale)
    hw = size * 2 // 5
    top = cy - size
    mid = cy - size // 2
    if glow > 0:
        r = int(size * 0.9)
        aura = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        pulse = 0.7 + 0.3 * math.sin(t * 3)
        pygame.draw.circle(aura, (255, 60, 40, int(70 * glow * pulse)), (r, r), r)
        aura = pygame.transform.box_blur(aura, max(1, px(14)))
        surf.blit(aura, (cx - r, mid - r), special_flags=pygame.BLEND_RGBA_ADD)
    # Vidrio
    glass = pygame.Surface((hw * 2 + 2, size + 2), pygame.SRCALPHA)
    ox, oy = hw + 1, 1
    upper = [
        (ox - hw, oy),
        (ox + hw, oy),
        (ox + px(2), oy + size // 2),
        (ox - px(2), oy + size // 2),
    ]
    lower = [
        (ox - px(2), oy + size // 2),
        (ox + px(2), oy + size // 2),
        (ox + hw, oy + size),
        (ox - hw, oy + size),
    ]
    pygame.draw.polygon(glass, (200, 220, 255, 40), upper)
    pygame.draw.polygon(glass, (200, 220, 255, 40), lower)
    # Arena arriba (llena desde el cuello hacia arriba)
    sand = _clamp01(sand)
    sand_col = (232, 190, 90, 230)
    if sand > 0:
        level = oy + size // 2 - int(size // 2 * sand)
        k = (oy + size // 2 - level) / (size // 2)
        half = px(2) + int((hw - px(2)) * k)
        pygame.draw.polygon(
            glass,
            sand_col,
            [
                (ox - half, level),
                (ox + half, level),
                (ox + px(2), oy + size // 2),
                (ox - px(2), oy + size // 2),
            ],
        )
    # Arena abajo (montículo)
    fill = 1 - sand
    if fill > 0:
        hh = int(size // 2 * fill)
        base = oy + size
        pygame.draw.polygon(
            glass,
            sand_col,
            [
                (ox - hw, base),
                (ox + hw, base),
                (ox + hw * max(0.0, 1 - fill), base - hh),
                (ox, base - hh - px(4)),
                (ox - hw * max(0.0, 1 - fill), base - hh),
            ],
        )
    if 0 < sand < 1:
        pygame.draw.line(
            glass, sand_col, (ox, oy + size // 2), (ox, oy + size - px(2)), max(1, px(1))
        )
    pygame.draw.polygon(glass, (220, 235, 255, 150), upper, 1)
    pygame.draw.polygon(glass, (220, 235, 255, 150), lower, 1)
    surf.blit(glass, (cx - hw - 1, top - 1))
    # Armazón dorado
    gold, dark = PALETTE.poster_gold, PALETTE.poster_gold_dark
    for yy in (top - px(4), cy):
        pygame.draw.rect(surf, dark, (cx - hw - px(6), yy, hw * 2 + px(12), px(5)))
        pygame.draw.rect(surf, gold, (cx - hw - px(6), yy, hw * 2 + px(12), px(2)))
    for xx in (cx - hw - px(4), cx + hw + px(2)):
        pygame.draw.rect(surf, dark, (xx, top, px(3), size))
        pygame.draw.line(surf, gold, (xx, top), (xx, cy), 1)


def _chamber_scene(surf: pygame.Surface, t: float) -> None:
    w, h = surf.get_size()
    surf.blit(_chamber(w, h), (0, 0))
    _candles(surf, t)


# ---------------------------------------------------------------------------
# La mazmorra
# ---------------------------------------------------------------------------


@functools.lru_cache(maxsize=2)
def _dungeon(w: int, h: int) -> pygame.Surface:
    surf = pygame.Surface((w, h))
    floor_y = int(h * 0.78)
    for y in range(h):
        k = y / h
        c = (int(22 + 14 * k), int(18 + 10 * k), int(30 + 10 * k))
        pygame.draw.line(surf, c, (0, y), (w, y))
    rng = random.Random(3)
    bh = px(30)
    for row, y in enumerate(range(0, floor_y, bh)):
        off = (row % 2) * px(36)
        for x in range(-px(72) + off, w, px(72)):
            s = rng.randint(-6, 6)
            pygame.draw.rect(surf, (34 + s, 28 + s, 44 + s), (x, y, px(72), bh))
            pygame.draw.rect(surf, (18, 14, 26), (x, y, px(72), bh), 1)
    # Suelo
    for y in range(floor_y, h):
        k = (y - floor_y) / max(1, h - floor_y)
        c = (int(30 + 10 * k), int(24 + 8 * k), int(34 + 8 * k))
        pygame.draw.line(surf, c, (0, y), (w, y))
    pygame.draw.line(surf, (60, 50, 70), (0, floor_y), (w, floor_y), px(2))
    # Tragaluz con barrotes arriba a la derecha
    gx, gy, gw, gh = int(w * 0.68), int(h * 0.08), px(90), px(50)
    pygame.draw.rect(surf, (8, 8, 20), (gx, gy, gw, gh))
    for i in range(4):
        pygame.draw.rect(surf, (50, 46, 60), (gx + px(10) + i * px(22), gy, px(5), gh))
    # Cadenas y argolla
    for x in (int(w * 0.22), int(w * 0.3)):
        for y in range(int(h * 0.2), int(h * 0.5), px(8)):
            pygame.draw.ellipse(surf, (70, 66, 80), (x, y, px(6), px(10)), 1)
    return surf


def _moon_shaft(surf: pygame.Surface, t: float, strength: float) -> None:
    w, h = surf.get_size()
    if strength <= 0:
        return
    gx, gy, gw = int(w * 0.68), int(h * 0.08), px(90)
    shaft = pygame.Surface((w, h), pygame.SRCALPHA)
    k = 0.9 + 0.1 * math.sin(t * 0.7)
    pts = [(gx, gy), (gx + gw, gy), (gx - px(120), int(h * 0.8)), (gx - px(330), int(h * 0.8))]
    pygame.draw.polygon(shaft, (150, 170, 230, int(42 * strength * k)), pts)
    surf.blit(shaft, (0, 0))


def _torch(surf: pygame.Surface, x: int, y: int, t: float) -> None:
    flick = 0.8 + 0.2 * math.sin(t * 11) * math.sin(t * 6.1)
    r = int(px(56) * flick)
    glow = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
    pygame.draw.circle(glow, (255, 150, 60, 46), (r, r), r)
    glow = pygame.transform.box_blur(glow, px(16))
    surf.blit(glow, (x - r, y - r), special_flags=pygame.BLEND_RGBA_ADD)
    pygame.draw.rect(surf, (80, 60, 40), (x - px(3), y, px(6), px(30)))
    fh = px(16) * flick
    pygame.draw.polygon(
        surf, (255, 170, 60), [(x - px(7), y + px(2)), (x, y - fh), (x + px(7), y + px(2))]
    )
    pygame.draw.polygon(
        surf, (255, 240, 170), [(x - px(3), y + px(2)), (x, y - fh / 2), (x + px(3), y + px(2))]
    )


def _dungeon_scene(surf: pygame.Surface, t: float) -> None:
    """El joven cae desde arriba, aterriza, se incorpora y mira la luz."""
    w, h = surf.get_size()
    surf.blit(_dungeon(w, h), (0, 0))
    _torch(surf, int(w * 0.12), int(h * 0.3), t)
    floor_y = int(h * 0.78)
    kx = int(w * 0.46)
    if t < 1.2:
        k = _ease(t / 1.2)
        ky = int(-px(80) + (floor_y + px(80)) * k * k)
        _actor(surf, 102 + int(t * 8) % 4, CharPalette.KID, 0, kx, ky)
    elif t < 1.5:
        _actor(surf, 106, CharPalette.KID, 0, kx, floor_y)
    elif t < 3.2:
        _actor(surf, 179 + min(6, int((t - 1.5) * 6)), CharPalette.KID, 0, kx, floor_y)
    elif t < 4.4:
        f = 115 + min(5, int((t - 3.2) * 5))
        _actor(surf, f, CharPalette.KID, 0, kx, floor_y)
    else:
        _actor(surf, 15, CharPalette.KID, 0, kx, floor_y)
    _moon_shaft(surf, t, _clamp01((t - 3.0) / 2.0))


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------


def draw_intro(surf: pygame.Surface, t: float) -> None:
    """Cinemática de introducción (``t`` en segundos, 0..INTRO_DURATION)."""
    w, h = surf.get_size()
    floor_y = int(h * 0.76)
    if t < _SCENE_PALACE_END:
        draw_backdrop(surf, t)
        # Un velo rojo que crece: la sombra del visir sobre el palacio
        k = _clamp01((t - 4.0) / 3.0)
        if k > 0:
            veil = pygame.Surface((w, h), pygame.SRCALPHA)
            veil.fill((120, 10, 20, int(70 * k)))
            surf.blit(veil, (0, 0))
        _fade(surf, 1 - t / 1.2)
        _fade(surf, (t - (_SCENE_PALACE_END - 0.6)) / 0.6)
    elif t < _SCENE_CHAMBER_END:
        s = t - _SCENE_PALACE_END
        _chamber_scene(surf, t)
        # La princesa, a la izquierda: espera cabizbaja y se sobresalta al
        # ver aparecer el reloj de arena
        pf = poses.PRINCESS_STARTLE if 3.8 <= s < 7.0 else poses.PRINCESS_WAIT
        _actor(surf, pf, CharPalette.PRINCESS, 0, int(w * 0.3), floor_y)
        # Jaffar entra desde la derecha (0..3 s), se para junto al pedestal
        vx_end, vx_start = int(w * 0.66), int(w + px(60))
        if s < 3.0:
            vx = int(vx_start + (vx_end - vx_start) * _ease(s / 3.0))
            _actor(surf, _vizier_frame(s), CharPalette.VIZIER, -1, vx, floor_y)
        else:
            _actor(surf, _vizier_frame(s), CharPalette.VIZIER, -1, vx_end, floor_y)
        # El reloj de arena aparece al conjurarlo (3.8 s) y la arena corre
        if s >= 3.8:
            appear = _ease((s - 3.8) / 0.8)
            sand = 1.0 - _clamp01((s - 4.6) / 60.0)
            draw_hourglass(
                surf,
                w // 2,
                floor_y - px(44),
                px(70),
                sand,
                t,
                glow=appear,
                scale=0.6 + 0.4 * appear,
            )
        _fade(surf, 1 - s / 0.8)
        _fade(surf, (s - (_SCENE_CHAMBER_END - _SCENE_PALACE_END - 0.6)) / 0.6)
    else:
        s = t - _SCENE_CHAMBER_END
        _dungeon_scene(surf, s)
        _fade(surf, 1 - s / 0.8)
        _fade(surf, (s - (INTRO_DURATION - _SCENE_CHAMBER_END - 1.0)) / 1.0)
    _letterbox(surf)
    _subtitles(surf, INTRO_LINES, t)
    _skip_hint(surf, t)


def draw_ending(surf: pygame.Surface, t: float) -> None:
    """Reencuentro en los aposentos (``t`` en segundos, 0..ENDING_DURATION)."""
    w, h = surf.get_size()
    floor_y = int(h * 0.76)
    _chamber_scene(surf, t)
    # La arena casi agotada; el aura se apaga al detenerse (1 s)
    glow = 1.0 - _clamp01((t - 0.6) / 1.2)
    draw_hourglass(surf, w // 2, floor_y - px(44), px(70), 0.04, t, glow=glow)
    # El príncipe entra corriendo por la izquierda y frena a media sala
    px_end, px_start = int(w * 0.4), int(-px(60))
    if t < 2.6:
        kx = int(px_start + (px_end - px_start) * _ease(t / 2.6))
        _actor(surf, _run_frame(t), CharPalette.KID, 0, kx, floor_y)
    else:
        _actor(surf, 15, CharPalette.KID, 0, px_end, floor_y)
    # La princesa va a su encuentro (3..5.5 s)
    pr_start, pr_end = int(w * 0.74), int(w * 0.6)
    if t < 2.2:
        _actor(surf, poses.PRINCESS_WAIT, CharPalette.PRINCESS, -1, pr_start, floor_y)
    elif t < 3.0:
        _actor(surf, poses.PRINCESS_STARTLE, CharPalette.PRINCESS, -1, pr_start, floor_y)
    elif t < 5.5:
        k = _ease((t - 3.0) / 2.5)
        glide = poses.PRINCESS_GLIDE_FIRST + int(t * 10) % 10
        _actor(
            surf,
            glide,
            CharPalette.PRINCESS,
            -1,
            int(pr_start + (pr_end - pr_start) * k),
            floor_y,
        )
    else:
        _actor(surf, poses.PRINCESS_JOY, CharPalette.PRINCESS, -1, pr_end, floor_y)
    # Destellos dorados cuando se encuentran
    if t > 5.5:
        rng = random.Random(int(t * 6))
        for _ in range(14):
            sx = w // 2 + rng.randint(-px(90), px(90))
            sy = floor_y - rng.randint(px(10), px(120)) - int((t * 20) % px(40))
            a = 0.5 + 0.5 * math.sin(t * 7 + sx)
            pygame.draw.circle(surf, (255, int(220 * a), int(120 * a)), (sx, sy), max(1, px(1)))
    # Amanece: el muro se calienta
    dawn = _clamp01((t - 6.0) / 5.0)
    if dawn > 0:
        veil = pygame.Surface((w, h), pygame.SRCALPHA)
        veil.fill((255, 200, 120, int(50 * dawn)))
        surf.blit(veil, (0, 0))
    if t > 9.5:
        fin = fonts.gold_title(tr("FIN"), 64, glow=8).copy()
        fin.set_alpha(int(255 * _clamp01((t - 9.5) / 1.0)))
        surf.blit(fin, fin.get_rect(center=(w // 2, int(h * 0.3))))
    _fade(surf, 1 - t / 1.0)
    _letterbox(surf)
    _subtitles(surf, ENDING_LINES, t)
    _skip_hint(surf, t)
