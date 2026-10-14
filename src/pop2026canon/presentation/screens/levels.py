"""Selección de nivel: una tarjeta por nivel con su ambiente, el mejor
tiempo, las muertes y las medallas; los niveles aún no alcanzados van
con candado.

La navegación (``LevelSelect.handle``) es pura y está testeada; el
dibujo va aparte.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pygame

from pop2026canon.infrastructure.progress import MEDALS, Progress
from pop2026canon.presentation import fonts
from pop2026canon.presentation.input_device import UiAction
from pop2026canon.presentation.layout import px
from pop2026canon.presentation.palette import PALETTE
from pop2026canon.presentation.themes import theme_for

COLS = 7
ROWS = 2

MEDAL_COLORS: dict[str, tuple[int, int, int]] = {
    "completed": (200, 200, 210),
    "flawless": (240, 200, 70),
    "swift": (90, 170, 255),
    "explorer": (90, 220, 120),
}
MEDAL_NAMES: dict[str, str] = {
    "completed": "Completado",
    "flawless": "Sin un rasguño",
    "swift": "Veloz",
    "explorer": "Explorador",
}


@dataclass
class LevelSelect:
    progress: Progress
    index: int = 0
    total: int = 14

    def handle(self, action: UiAction) -> str | None:
        """``"_move"`` al moverse, ``"start"`` al confirmar un nivel
        desbloqueado, ``"locked"`` si no lo está, ``"back"`` al salir."""
        if action is UiAction.LEFT:
            self.index = (self.index - 1) % self.total
            return "_move"
        if action is UiAction.RIGHT:
            self.index = (self.index + 1) % self.total
            return "_move"
        if action is UiAction.UP:
            self.index = (self.index - COLS) % self.total
            return "_move"
        if action is UiAction.DOWN:
            self.index = (self.index + COLS) % self.total
            return "_move"
        if action is UiAction.CONFIRM:
            return "start" if self.unlocked(self.level) else "locked"
        if action in (UiAction.BACK, UiAction.PAUSE):
            return "back"
        return None

    @property
    def level(self) -> int:
        return self.index + 1

    def unlocked(self, level: int) -> bool:
        return level <= self.progress.unlocked


def _medal(surf: pygame.Surface, cx: int, cy: int, kind: str, r: int, *, got: bool) -> None:
    col = MEDAL_COLORS[kind] if got else (60, 56, 70)
    pts = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
    pygame.draw.polygon(surf, col, pts)
    if got:
        hi = tuple(min(255, c + 70) for c in col)
        pygame.draw.line(surf, hi, (cx - r // 2, cy - r // 2), (cx, cy - r + 1), 1)
    pygame.draw.polygon(surf, (16, 10, 22), pts, 1)


def draw_level_select(
    surf: pygame.Surface,
    sel: LevelSelect,
    level_names: dict[int, str],
    t: float,
) -> None:
    w, h = surf.get_size()
    title = fonts.gold_title("NIVELES", 38, glow=5)
    surf.blit(title, title.get_rect(midtop=(w // 2, px(14))))
    margin = px(18)
    gap = px(8)
    cw = (w - margin * 2 - gap * (COLS - 1)) // COLS
    ch = px(118)
    top = px(70)
    for i in range(sel.total):
        n = i + 1
        col, row = i % COLS, i // COLS
        x = margin + col * (cw + gap)
        y = top + row * (ch + gap)
        rect = pygame.Rect(x, y, cw, ch)
        th = theme_for(n)
        unlocked = sel.unlocked(n)
        rec = sel.progress.record(n)
        card = pygame.Surface(rect.size, pygame.SRCALPHA)
        stone = th.stone if unlocked else tuple(c // 3 for c in th.stone)
        for yy in range(ch):
            k = yy / ch
            c = tuple(int(stone[j] * (0.55 + 0.35 * (1 - k))) for j in range(3))
            pygame.draw.line(card, (*c, 235), (0, yy), (cw, yy))
        # Franja del ambiente
        pygame.draw.rect(
            card, (*th.accent, 255) if unlocked else (40, 40, 48, 255), (0, 0, cw, px(5))
        )
        surf.blit(card, rect)
        selected = i == sel.index
        if selected:
            glow = 150 + int(80 * (0.5 + 0.5 * math.sin(t * 5)))
            pygame.draw.rect(surf, (*PALETTE.poster_gold, glow), rect, px(2), border_radius=px(4))
        else:
            pygame.draw.rect(surf, (*PALETTE.poster_gold_dark, 140), rect, 1, border_radius=px(4))
        num = fonts.render(
            str(n), 30, PALETTE.poster_gold if unlocked else PALETTE.muted, bold=True
        )
        surf.blit(num, (rect.x + px(6), rect.y + px(8)))
        name = level_names.get(n, "")
        name_s = fonts.render(name, 15, PALETTE.primary if unlocked else PALETTE.muted)
        if name_s.get_width() > cw - px(10):
            name_s = pygame.transform.smoothscale(
                name_s, (cw - px(10), int(name_s.get_height() * (cw - px(10)) / name_s.get_width()))
            )
        surf.blit(name_s, (rect.x + px(6), rect.y + px(40)))
        if not unlocked:
            # Candado
            lx, ly = rect.centerx, rect.y + px(80)
            pygame.draw.rect(
                surf, (120, 110, 130), (lx - px(7), ly - px(2), px(14), px(11)), border_radius=px(2)
            )
            pygame.draw.arc(
                surf, (120, 110, 130), (lx - px(5), ly - px(12), px(10), px(14)), 0, math.pi, px(2)
            )
            continue
        clock = fonts.render(rec.best_clock, 16, PALETTE.primary_dark)
        surf.blit(clock, (rect.x + px(6), rect.y + px(60)))
        if rec.best_deaths is not None:
            d = fonts.render(
                f"☠ {rec.best_deaths}" if fonts.has_symbols() else f"x{rec.best_deaths}",
                14,
                PALETTE.muted,
            )
            surf.blit(d, (rect.x + px(6), rect.y + px(78)))
        for k, kind in enumerate(MEDALS):
            _medal(
                surf,
                rect.x + px(12) + k * px(17),
                rect.bottom - px(14),
                kind,
                px(6),
                got=kind in rec.medals,
            )
    # Pie: nivel elegido, medallas y ayuda
    n = sel.level
    th = theme_for(n)
    rec = sel.progress.record(n)
    foot_y = top + ROWS * (ch + gap) + px(10)
    if sel.unlocked(n):
        line = f"{n} · {level_names.get(n, '')} — {th.title}"
        got = [MEDAL_NAMES[m] for m in MEDALS if m in rec.medals]
        sub = ("Medallas: " + ", ".join(got)) if got else "Sin medallas todavía"
    else:
        line = f"{n} · {level_names.get(n, '')}"
        sub = "Completa el nivel anterior para desbloquearlo"
    l1 = fonts.render(line, 22, PALETTE.primary)
    l2 = fonts.render(sub, 18, PALETTE.primary_dark)
    surf.blit(l1, l1.get_rect(midtop=(w // 2, foot_y)))
    surf.blit(l2, l2.get_rect(midtop=(w // 2, foot_y + px(26))))
    total = sel.progress.medal_count
    tm = fonts.render(f"{total} / {4 * 13} medallas", 16, PALETTE.poster_gold)
    surf.blit(tm, tm.get_rect(midtop=(w // 2, foot_y + px(50))))
    hint = fonts.render("Enter / A: jugar · Esc / B: volver", 16, PALETTE.muted)
    surf.blit(hint, hint.get_rect(midbottom=(w // 2, h - px(8))))
