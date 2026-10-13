"""HUD moderno: vida en triángulos (canon) con brillo y animación de
pérdida, reloj de arena del rebobinado, vida y nombre del enemigo,
reloj, pistas emergentes y rótulo de nivel."""

from __future__ import annotations

import functools
import math
from dataclasses import dataclass

import pygame

from pop2026canon.domain.chars import CharId
from pop2026canon.domain.combat import is_hostile
from pop2026canon.domain.game import Game
from pop2026canon.presentation import fonts
from pop2026canon.presentation.layout import LAYOUT
from pop2026canon.presentation.palette import PALETTE

ENEMY_NAMES: dict[CharId, str] = {
    CharId.GUARD: "GUARDIA",
    CharId.GUARD_VARIANT: "GUARDIA",
    CharId.SKELETON: "ESQUELETO",
    CharId.VIZIER: "JAFFAR",
    CharId.SHADOW: "SOMBRA",
}


@functools.lru_cache(maxsize=2)
def _bar_background(w: int, h: int) -> pygame.Surface:
    s = pygame.Surface((w, h))
    for y in range(h):
        k = y / max(1, h - 1)
        col = (int(14 + 10 * k), int(9 + 6 * k), int(26 + 10 * k))
        pygame.draw.line(s, col, (0, y), (w, y))
    pygame.draw.line(s, PALETTE.poster_gold_dark, (0, h - 3), (w, h - 3))
    pygame.draw.line(s, PALETTE.poster_gold, (0, h - 2), (w, h - 2))
    pygame.draw.line(s, (0, 0, 0), (0, h - 1), (w, h - 1))
    # Ornamento central
    cx = w // 2
    pygame.draw.polygon(s, PALETTE.poster_gold, [(cx - 8, h - 2), (cx, h - 9), (cx + 8, h - 2)])
    return s


def _triangle(
    surf: pygame.Surface,
    x: int,
    y: int,
    color: tuple[int, int, int],
    *,
    filled: bool,
    scale: float = 1.0,
) -> None:
    w = int(11 * scale)
    h = int(13 * scale)
    pts = [(x, y + h // 2), (x + w // 2, y - h // 2), (x + w, y + h // 2)]
    if filled:
        pygame.draw.polygon(surf, color, pts)
        hi = tuple(min(255, c + 70) for c in color)
        pygame.draw.line(surf, hi, (x + w // 2, y - h // 2 + 2), (x + 3, y + h // 2 - 2), 1)
    pygame.draw.polygon(surf, (0, 0, 0) if filled else color, pts, 1)


def _hourglass(surf: pygame.Surface, x: int, y: int, frac: float, active: bool, t: float) -> None:
    gold = PALETTE.poster_gold if not active else (255, 240, 170)
    pygame.draw.line(surf, gold, (x, y - 10), (x + 12, y - 10), 2)
    pygame.draw.line(surf, gold, (x, y + 10), (x + 12, y + 10), 2)
    pygame.draw.polygon(
        surf,
        gold,
        [(x + 1, y - 9), (x + 11, y - 9), (x + 6, y), (x + 11, y + 9), (x + 1, y + 9), (x + 6, y)],
        1,
    )
    sand = (240, 200, 110)
    top_h = int(8 * (1 - frac))
    bot_h = int(8 * frac)
    if top_h:
        pygame.draw.polygon(
            surf,
            sand,
            [
                (x + 6 - top_h // 2 - 1, y - 1 - top_h),
                (x + 6 + top_h // 2 + 1, y - 1 - top_h),
                (x + 6, y - 1),
            ],
        )
    if bot_h:
        pygame.draw.polygon(surf, sand, [(x + 2, y + 8), (x + 10, y + 8), (x + 6, y + 8 - bot_h)])
    if active and int(t * 20) % 2 == 0:
        pygame.draw.line(surf, sand, (x + 6, y), (x + 6, y + 7), 1)


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
    x0, y0 = 14, 20
    for i in range(kid.hp_max):
        filled = i < kid.hp_curr
        color = PALETTE.error
        scale = 1.0
        if filled and kid.hp_curr == 1:
            scale = 1.0 + 0.12 * (0.5 + 0.5 * math.sin(t * 8))
        if not filled and state.lost_flash > 0 and i == kid.hp_curr:
            color = (255, 255, 255)
            filled = True
        _triangle(
            surf, x0 + i * 15, y0, color if filled else PALETTE.muted, filled=filled, scale=scale
        )
    x_after = x0 + kid.hp_max * 15 + 10
    if sand is not None:
        _hourglass(surf, x_after, y0, sand, rewinding, t)
        bar = pygame.Rect(x_after + 18, y0 - 3, 46, 6)
        pygame.draw.rect(surf, (40, 30, 20), bar, border_radius=3)
        fill = bar.copy()
        fill.w = int(bar.w * sand)
        if fill.w > 0:
            pygame.draw.rect(surf, (240, 200, 110), fill, border_radius=3)
        pygame.draw.rect(surf, PALETTE.poster_gold_dark, bar, 1, border_radius=3)

    # Nombre del nivel
    title = f"{game.level.number} · {game.level.name.upper()}"
    label = fonts.render(title, 22, PALETTE.primary)
    surf.blit(label, label.get_rect(center=(w // 2, 18)))

    # Reloj
    if show_time or game.time.minutes < 5:
        warn = game.time.minutes < 5
        txt = f"{game.time.minutes:02d}:{game.time.ticks // 12:02d}"
        col = PALETTE.warning if warn else PALETTE.primary_dark
        if warn and int(t * 2) % 2 == 0:
            col = PALETTE.error
        tt = fonts.render(txt, 20, col)
        surf.blit(tt, tt.get_rect(center=(w // 2, 36)))

    # Enemigo
    enemy = next(
        (c for c in game.others if is_hostile(c) and c.room == kid.room and c.alive < 0), None
    )
    if enemy is not None:
        name = ENEMY_NAMES.get(enemy.charid, "ENEMIGO")
        n = fonts.render(name, 18, (150, 170, 230))
        right = w - 14
        for i in range(enemy.hp_max):
            _triangle(
                surf,
                right - (i + 1) * 15,
                y0,
                (70, 120, 230) if i < enemy.hp_curr else PALETTE.muted,
                filled=i < enemy.hp_curr,
            )
        surf.blit(n, n.get_rect(midright=(right - enemy.hp_max * 15 - 8, y0)))


def draw_banner(surf: pygame.Surface, game: Game, state: HudState) -> None:
    if state.banner_t <= 0:
        return
    k = state.banner_t / state.BANNER_TIME
    a = min(1.0, (1 - k) * 4, k * 3)
    w = surf.get_width()
    big = fonts.render(f"NIVEL {game.level.number}", 48, PALETTE.poster_gold, bold=True)
    small = fonts.render(game.level.name, 26, PALETTE.primary)
    panel = pygame.Surface((w, 92), pygame.SRCALPHA)
    panel.fill((0, 0, 0, int(140 * a)))
    big.set_alpha(int(255 * a))
    small.set_alpha(int(255 * a))
    y = LAYOUT.hud_top + 150
    surf.blit(panel, (0, y))
    surf.blit(big, big.get_rect(center=(w // 2, y + 32)))
    surf.blit(small, small.get_rect(center=(w // 2, y + 66)))


def draw_toast(surf: pygame.Surface, state: HudState) -> None:
    if state.toast_t <= 0 or not state.toast_text:
        return
    k = state.toast_t / state.TOAST_TIME
    a = min(1.0, (1 - k) * 6, k * 4)
    text = fonts.render(state.toast_text, 20, PALETTE.primary)
    w, h = surf.get_size()
    if text.get_width() > w - 40:
        text = pygame.transform.smoothscale(
            text, (w - 40, int(text.get_height() * (w - 40) / text.get_width()))
        )
    pad = 10
    rect = text.get_rect(center=(w // 2, h - 26 + int(10 * (1 - a))))
    box = rect.inflate(pad * 2, pad)
    panel = pygame.Surface(box.size, pygame.SRCALPHA)
    pygame.draw.rect(panel, (8, 6, 16, int(200 * a)), panel.get_rect(), border_radius=8)
    pygame.draw.rect(
        panel, (*PALETTE.poster_gold, int(220 * a)), panel.get_rect(), 1, border_radius=8
    )
    surf.blit(panel, box)
    text.set_alpha(int(255 * a))
    surf.blit(text, rect)


def draw_rewind_icon(surf: pygame.Surface, t: float) -> None:
    w = surf.get_width()
    a = 160 + int(90 * (0.5 + 0.5 * math.sin(t * 10)))
    icon = pygame.Surface((60, 30), pygame.SRCALPHA)
    col = (255, 230, 170, a)
    for i in range(2):
        x = 28 - i * 22
        pygame.draw.polygon(icon, col, [(x + 22, 3), (x + 22, 27), (x + 4, 15)])
    surf.blit(icon, (w - 80, LAYOUT.hud_top + 14))
