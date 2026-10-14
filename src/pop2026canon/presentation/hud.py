"""HUD moderno: vida en triángulos (canon) con brillo y animación de
pérdida, reloj de arena del rebobinado, vida y nombre del enemigo,
reloj, pistas emergentes y rótulo de nivel.

Medidas en escala de diseño (640x426) pasadas por ``px``: se pinta
nítido sobre el lienzo HD.
"""

from __future__ import annotations

import functools
import math
from dataclasses import dataclass

import pygame

from pop2026canon.domain.chars import CharId
from pop2026canon.domain.combat import is_hostile
from pop2026canon.domain.game import Game
from pop2026canon.presentation import fonts
from pop2026canon.presentation.i18n import tr
from pop2026canon.presentation.layout import LAYOUT, px
from pop2026canon.presentation.palette import PALETTE

ENEMY_NAMES: dict[CharId, str] = {
    CharId.GUARD: "GUARDIA",
    CharId.GUARD_VARIANT: "GUARDIA",
    CharId.SKELETON: "ESQUELETO",
    CharId.VIZIER: "JAFFAR",
    CharId.SHADOW: "SOMBRA",
}

RGB = tuple[int, int, int]


@functools.lru_cache(maxsize=2)
def _bar_background(w: int, h: int) -> pygame.Surface:
    """Banda superior: degradado de terciopelo con filo dorado biselado."""
    s = pygame.Surface((w, h))
    for y in range(h):
        k = y / max(1, h - 1)
        col = (int(10 + 14 * k), int(7 + 8 * k), int(20 + 16 * k))
        pygame.draw.line(s, col, (0, y), (w, y))
    # Celosía tenue (motivo geométrico persa)
    step = px(16)
    for x in range(-h, w, step):
        pygame.draw.line(s, (26, 20, 40), (x, h - px(5)), (x + h, 0))
        pygame.draw.line(s, (26, 20, 40), (x + h, h - px(5)), (x, 0))
    shade = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(h):
        a = int(150 * (1 - y / h) ** 2)
        pygame.draw.line(shade, (6, 4, 12, a), (0, y), (w, y))
    s.blit(shade, (0, 0))
    gold, gold_dark = PALETTE.poster_gold, PALETTE.poster_gold_dark
    pygame.draw.line(s, gold_dark, (0, h - px(3)), (w, h - px(3)), px(1))
    pygame.draw.line(s, gold, (0, h - px(2)), (w, h - px(2)), px(1))
    pygame.draw.line(s, (255, 236, 170), (0, h - px(2)), (w, h - px(2)), 1)
    pygame.draw.line(s, (0, 0, 0), (0, h - 1), (w, h - 1), 1)
    cx = w // 2
    for r, col in ((10, gold_dark), (8, gold), (4, (255, 236, 170))):
        pygame.draw.polygon(
            s,
            col,
            [(cx - px(r), h - px(2)), (cx, h - px(2) - px(r)), (cx + px(r), h - px(2))],
        )
    return s


@functools.lru_cache(maxsize=64)
def _gem(color: RGB, scale_q: int, filled: bool) -> pygame.Surface:
    """Triángulo de vida como gema facetada con brillo (cacheado)."""
    scale = scale_q / 100
    w = px(12 * scale)
    h = px(14 * scale)
    pad = px(4)
    s = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
    ox, oy = pad, pad
    top = (ox + w // 2, oy)
    left = (ox, oy + h)
    right = (ox + w, oy + h)
    if filled:
        glow = pygame.Surface(s.get_size(), pygame.SRCALPHA)
        pygame.draw.polygon(glow, (*color, 90), [top, left, right])
        glow = pygame.transform.box_blur(glow, max(1, pad // 2))
        s.blit(glow, (0, 0))
        dark = tuple(int(c * 0.55) for c in color)
        light = tuple(min(255, c + 80) for c in color)
        mid = (ox + w // 2, oy + h * 2 // 3)
        pygame.draw.polygon(s, color, [top, left, right])
        pygame.draw.polygon(s, dark, [mid, left, right])
        pygame.draw.polygon(s, light, [top, mid, left])
        pygame.draw.line(s, (255, 255, 255), top, (ox + w // 2 - px(2), oy + h // 2), 1)
        pygame.draw.polygon(s, (20, 6, 6), [top, left, right], 1)
    else:
        pygame.draw.polygon(s, (*color, 70), [top, left, right])
        pygame.draw.polygon(s, color, [top, left, right], max(1, px(1)))
    return s


def _triangle(
    surf: pygame.Surface,
    x: int,
    y: int,
    color: RGB,
    *,
    filled: bool,
    scale: float = 1.0,
) -> None:
    """Gema de vida con el vértice inferior izquierdo en ``x`` y centrada
    verticalmente en ``y`` (coordenadas del lienzo)."""
    g = _gem(color, int(scale * 100), filled)
    surf.blit(g, g.get_rect(center=(x + px(6 * scale), y)))


def _hourglass(surf: pygame.Surface, x: int, y: int, frac: float, active: bool, t: float) -> None:
    gold = PALETTE.poster_gold if not active else (255, 240, 170)
    s = LAYOUT.scale

    def p(dx: float, dy: float) -> tuple[int, int]:
        return x + round(dx * s), y + round(dy * s)

    pygame.draw.line(surf, gold, p(-1, -10), p(13, -10), px(2))
    pygame.draw.line(surf, gold, p(-1, 10), p(13, 10), px(2))
    glass = [p(1, -9), p(11, -9), p(6, 0), p(11, 9), p(1, 9), p(6, 0)]
    pygame.draw.polygon(surf, (40, 30, 50), glass)
    pygame.draw.polygon(surf, gold, glass, max(1, px(1)))
    sand = (240, 200, 110)
    top_h = 8 * (1 - frac)
    bot_h = 8 * frac
    if top_h > 0.3:
        pygame.draw.polygon(
            surf,
            sand,
            [p(6 - top_h / 2 - 1, -1 - top_h), p(6 + top_h / 2 + 1, -1 - top_h), p(6, -1)],
        )
    if bot_h > 0.3:
        pygame.draw.polygon(surf, sand, [p(2, 8), p(10, 8), p(6, 8 - bot_h)])
    if active and int(t * 20) % 2 == 0:
        pygame.draw.line(surf, sand, p(6, 0), p(6, 7), max(1, px(1)))


@dataclass
class HudState:
    shown_hp: float = 3.0
    lost_flash: float = 0.0
    banner_t: float = 0.0
    toast_text: str = ""
    toast_t: float = 0.0

    TOAST_TIME = 5.0
    BANNER_TIME = 2.8

    def show_toast(self, text: str) -> None:
        self.toast_text = text
        self.toast_t = self.TOAST_TIME

    def show_banner(self) -> None:
        self.banner_t = self.BANNER_TIME

    def update(self, dt: float, hp: int) -> None:
        if hp < self.shown_hp - 0.01:
            self.lost_flash = 0.5
        self.shown_hp = float(hp)
        self.lost_flash = max(0.0, self.lost_flash - dt)
        self.banner_t = max(0.0, self.banner_t - dt)
        self.toast_t = max(0.0, self.toast_t - dt)


def _shadowed(text: str, size: int, color: RGB, *, bold: bool = False) -> pygame.Surface:
    """Texto con sombra suave (legible sobre cualquier fondo)."""
    fg = fonts.render(text, size, color, bold=bold)
    sh = fonts.render(text, size, (0, 0, 0), bold=bold)
    o = max(1, px(1))
    out = pygame.Surface((fg.get_width() + o * 2, fg.get_height() + o * 2), pygame.SRCALPHA)
    sh.set_alpha(170)
    out.blit(sh, (o * 2, o * 2))
    out.blit(fg, (0, 0))
    return out


def draw_hud(
    surf: pygame.Surface,
    game: Game,
    state: HudState,
    *,
    t: float,
    sand: float | None,
    rewinding: bool,
    show_time: bool,
) -> None:
    w = surf.get_width()
    surf.blit(_bar_background(w, LAYOUT.hud_top), (0, 0))
    kid = game.kid
    # Vida del kid
    x0, y0 = px(14), px(20)
    gap = px(16)
    for i in range(kid.hp_max):
        filled = i < kid.hp_curr
        color = PALETTE.error
        scale = 1.0
        if filled and kid.hp_curr == 1:
            scale = 1.0 + 0.12 * (0.5 + 0.5 * math.sin(t * 8))
            scale = round(scale * 20) / 20
        if not filled and state.lost_flash > 0 and i == kid.hp_curr:
            color = (255, 255, 255)
            filled = True
        _triangle(
            surf, x0 + i * gap, y0, color if filled else PALETTE.muted, filled=filled, scale=scale
        )
    x_after = x0 + kid.hp_max * gap + px(10)
    if sand is not None:
        _hourglass(surf, x_after, y0, sand, rewinding, t)
        bar = pygame.Rect(x_after + px(18), y0 - px(3), px(46), px(6))
        pygame.draw.rect(surf, (40, 30, 20), bar, border_radius=bar.h // 2)
        fill = bar.copy()
        fill.w = int(bar.w * sand)
        if fill.w > 0:
            pygame.draw.rect(surf, (240, 200, 110), fill, border_radius=bar.h // 2)
            hi = fill.copy()
            hi.h = max(1, fill.h // 3)
            hi.y += 1
            pygame.draw.rect(surf, (255, 240, 190), hi, border_radius=hi.h)
        pygame.draw.rect(surf, PALETTE.poster_gold_dark, bar, 1, border_radius=bar.h // 2)

    # Nombre del nivel
    title = f"{game.level.number} · {game.level.name.upper()}"
    label = _shadowed(title, 22, PALETTE.primary)
    surf.blit(label, label.get_rect(center=(w // 2, px(17))))

    # Reloj
    if show_time or game.time.minutes < 5:
        warn = game.time.minutes < 5
        txt = f"{game.time.minutes:02d}:{game.time.ticks // 12:02d}"
        col = PALETTE.warning if warn else PALETTE.primary_dark
        if warn and int(t * 2) % 2 == 0:
            col = PALETTE.error
        tt = _shadowed(txt, 20, col)
        surf.blit(tt, tt.get_rect(center=(w // 2, px(35))))

    # Enemigo
    enemy = next(
        (c for c in game.others if is_hostile(c) and c.room == kid.room and c.alive < 0), None
    )
    if enemy is not None:
        name = tr(ENEMY_NAMES.get(enemy.charid, "ENEMIGO"))
        n = _shadowed(name, 18, (150, 170, 230))
        right = w - px(14)
        for i in range(enemy.hp_max):
            _triangle(
                surf,
                right - (i + 1) * gap,
                y0,
                (70, 120, 230) if i < enemy.hp_curr else PALETTE.muted,
                filled=i < enemy.hp_curr,
            )
        surf.blit(n, n.get_rect(midright=(right - enemy.hp_max * gap - px(8), y0)))


@functools.lru_cache(maxsize=4)
def _banner_panel(w: int, h: int) -> pygame.Surface:
    """Franja del rótulo: negro translúcido que se funde a los lados."""
    panel = pygame.Surface((w, h), pygame.SRCALPHA)
    for x in range(w):
        d = abs(x - w / 2) / (w / 2)
        a = int(170 * max(0.0, 1 - d**2.2))
        pygame.draw.line(panel, (4, 2, 10, a), (x, 0), (x, h))
    gold = PALETTE.poster_gold
    for x in range(w):
        d = abs(x - w / 2) / (w / 2)
        a = int(200 * max(0.0, 1 - d**1.5))
        panel.set_at((x, 0), (*gold, a))
        panel.set_at((x, h - 1), (*gold, a))
    return panel


def draw_banner(surf: pygame.Surface, game: Game, state: HudState) -> None:
    if state.banner_t <= 0:
        return
    k = state.banner_t / state.BANNER_TIME
    a = min(1.0, (1 - k) * 4, k * 3)
    w = surf.get_width()
    big = _shadowed(f"{tr('NIVEL')} {game.level.number}", 48, PALETTE.poster_gold, bold=True)
    small = _shadowed(game.level.name, 26, PALETTE.primary)
    panel = _banner_panel(w, px(92)).copy()
    panel.set_alpha(int(255 * a))
    big.set_alpha(int(255 * a))
    small.set_alpha(int(255 * a))
    y = LAYOUT.hud_top + px(150)
    rise = px(8) * (1 - min(1.0, (1 - k) * 4))
    surf.blit(panel, (0, y))
    surf.blit(big, big.get_rect(center=(w // 2, y + px(32) + rise)))
    surf.blit(small, small.get_rect(center=(w // 2, y + px(66) + rise)))


def draw_toast(surf: pygame.Surface, state: HudState) -> None:
    if state.toast_t <= 0 or not state.toast_text:
        return
    k = state.toast_t / state.TOAST_TIME
    a = min(1.0, (1 - k) * 6, k * 4)
    text = fonts.render(state.toast_text, 20, PALETTE.primary)
    w, h = surf.get_size()
    margin = px(40)
    if text.get_width() > w - margin:
        text = pygame.transform.smoothscale(
            text, (w - margin, int(text.get_height() * (w - margin) / text.get_width()))
        )
    pad = px(10)
    rect = text.get_rect(center=(w // 2, h - px(26) + int(px(10) * (1 - a))))
    box = rect.inflate(pad * 2, pad)
    panel = pygame.Surface(box.size, pygame.SRCALPHA)
    radius = px(8)
    pygame.draw.rect(panel, (8, 6, 16, int(210 * a)), panel.get_rect(), border_radius=radius)
    pygame.draw.rect(
        panel, (*PALETTE.poster_gold, int(220 * a)), panel.get_rect(), 1, border_radius=radius
    )
    surf.blit(panel, box)
    text.set_alpha(int(255 * a))
    surf.blit(text, rect)


def draw_rewind_icon(surf: pygame.Surface, t: float) -> None:
    w = surf.get_width()
    a = 160 + int(90 * (0.5 + 0.5 * math.sin(t * 10)))
    icon = pygame.Surface((px(60), px(30)), pygame.SRCALPHA)
    col = (255, 230, 170, a)
    for i in range(2):
        x = 28 - i * 22
        pygame.draw.polygon(
            icon, col, [(px(x + 22), px(3)), (px(x + 22), px(27)), (px(x + 4), px(15))]
        )
    surf.blit(icon, (w - px(80), LAYOUT.hud_top + px(14)))
