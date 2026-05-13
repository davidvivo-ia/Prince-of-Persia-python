"""Renderer pygame: dibujo procedural (sin sprites bitmap).

Vector-retro: rectángulos, polígonos y círculos en colores semánticos.
Encima, un overlay opcional de scanlines ("CRT layer").
"""

from __future__ import annotations

import pygame

from pop2026.domain.actions import Action
from pop2026.domain.game import Game, GameStatus
from pop2026.domain.geometry import Position
from pop2026.domain.guard import Guard, GuardMode
from pop2026.domain.level import effective_tile
from pop2026.domain.prince import Prince
from pop2026.domain.tiles import Tile
from pop2026.presentation.theme import LAYOUT, PALETTE, RGB


def _hud_text(game: Game) -> str:
    secs = game.time_left // 60
    mm, ss = divmod(secs, 60)
    hp_full = "*" * game.prince.hp
    hp_empty = "." * (game.prince.max_hp - game.prince.hp)
    sword = " [sword]" if game.prince.has_sword else ""
    return f"NIVEL {game.level_index}   {mm:02d}:{ss:02d}   HP [{hp_full}{hp_empty}]{sword}"


def _tile_color(tile: Tile) -> RGB | None:
    if tile is Tile.FLOOR:
        return PALETTE.bg_elev
    if tile is Tile.LOOSE_FLOOR:
        return PALETTE.muted
    if tile is Tile.GATE:
        return PALETTE.warning
    return None


def _draw_tile(surface: pygame.Surface, tile: Tile, x: int, y: int, ts: int) -> None:
    if tile is Tile.EMPTY:
        return
    color = _tile_color(tile)
    if color is not None:
        rect = pygame.Rect(x, y, ts, ts)
        pygame.draw.rect(surface, color, rect)
        bevel = tuple(min(255, c + 30) for c in color)
        pygame.draw.line(surface, bevel, (x, y), (x + ts - 1, y), 1)
        return
    if tile is Tile.SPIKES:
        for i in range(4):
            base_x = x + i * (ts // 4)
            pygame.draw.polygon(
                surface,
                PALETTE.error,
                [
                    (base_x, y + ts),
                    (base_x + ts // 8, y + ts // 2),
                    (base_x + ts // 4, y + ts),
                ],
            )
        return
    if tile is Tile.PRESSURE:
        pygame.draw.rect(surface, PALETTE.muted, (x, y + ts - 4, ts, 4))
        pygame.draw.rect(surface, PALETTE.accent, (x + ts // 3, y + ts - 6, ts // 3, 2))
        return
    if tile is Tile.POTION_HEAL:
        pygame.draw.circle(surface, PALETTE.success, (x + ts // 2, y + ts // 2), ts // 4)
        pygame.draw.rect(surface, PALETTE.success, (x + ts // 2 - 2, y + ts // 3, 4, 4))
        return
    if tile is Tile.POTION_POISON:
        pygame.draw.circle(surface, PALETTE.error, (x + ts // 2, y + ts // 2), ts // 4)
        pygame.draw.rect(surface, PALETTE.error, (x + ts // 2 - 2, y + ts // 3, 4, 4))
        return
    if tile is Tile.EXIT:
        pygame.draw.rect(surface, PALETTE.accent, (x + 2, y, ts - 4, ts), 2)
        pygame.draw.circle(surface, PALETTE.accent, (x + ts // 2, y + ts // 2), ts // 4, 1)
        return


def _draw_prince(surface: pygame.Surface, p: Prince, ts: int) -> None:
    cx = p.pos.col * ts + ts // 2
    cy = p.pos.row * ts + ts // 2
    color = PALETTE.primary if p.alive else PALETTE.error
    pygame.draw.rect(surface, color, (cx - 6, cy - 4, 12, 10))
    pygame.draw.circle(surface, color, (cx, cy - 8), 4)
    pygame.draw.rect(surface, color, (cx - 5, cy + 6, 4, 6))
    pygame.draw.rect(surface, color, (cx + 1, cy + 6, 4, 6))
    if p.has_sword:
        sx = cx + (6 if p.facing.value > 0 else -6)
        pygame.draw.line(
            surface,
            PALETTE.accent,
            (sx, cy - 2),
            (sx + (6 if p.facing.value > 0 else -6), cy - 2),
            2,
        )
    if p.action is Action.HURT:
        pygame.draw.circle(surface, PALETTE.error, (cx, cy - 12), 2)


def _draw_guard(surface: pygame.Surface, g: Guard, ts: int) -> None:
    cx = g.pos.col * ts + ts // 2
    cy = g.pos.row * ts + ts // 2
    color = PALETTE.error if g.mode is not GuardMode.DEAD else PALETTE.muted
    pygame.draw.rect(surface, color, (cx - 6, cy - 4, 12, 10))
    pygame.draw.circle(surface, color, (cx, cy - 8), 4)
    pygame.draw.rect(surface, color, (cx - 5, cy + 6, 4, 6))
    pygame.draw.rect(surface, color, (cx + 1, cy + 6, 4, 6))
    sx = cx + (6 if g.facing.value > 0 else -6)
    pygame.draw.line(
        surface,
        PALETTE.warning,
        (sx, cy - 2),
        (sx + (6 if g.facing.value > 0 else -6), cy - 2),
        2,
    )


def _draw_crt(surface: pygame.Surface) -> None:
    """Overlay de scanlines (firma visual)."""
    w, h = surface.get_size()
    line_surf = pygame.Surface((w, 2), pygame.SRCALPHA)
    line_surf.fill((0, 0, 0, 18))
    for y in range(0, h, 3):
        surface.blit(line_surf, (0, y))


def _draw_hud(surface: pygame.Surface, game: Game, font: pygame.font.Font) -> None:
    txt = _hud_text(game)
    img = font.render(txt, True, PALETTE.primary, PALETTE.bg)
    surface.blit(img, (8, 4))

    msg: str | None
    color: RGB = PALETTE.primary
    if game.status is GameStatus.WON:
        msg, color = "VICTORIA  ·  pulsa Esc para salir", PALETTE.accent
    elif game.status is GameStatus.LOST_DIED:
        msg, color = "HAS MUERTO  ·  Esc para salir", PALETTE.error
    elif game.status is GameStatus.LOST_TIMEOUT:
        msg, color = "TIEMPO AGOTADO  ·  Esc para salir", PALETTE.warning
    else:
        msg = None
    if msg is not None:
        big = font.render(msg, True, color, PALETTE.bg)
        rect = big.get_rect(center=(surface.get_width() // 2, surface.get_height() // 2))
        surface.blit(big, rect)


def render(
    surface: pygame.Surface,
    game: Game,
    font: pygame.font.Font,
    *,
    crt: bool = True,
) -> None:
    """Renderiza un frame completo del juego."""
    surface.fill(PALETTE.bg)
    ts = LAYOUT.tile_size

    for r in range(game.level.rows):
        for c in range(game.level.cols):
            tile = effective_tile(game.level, game.state, Position(r, c))
            _draw_tile(surface, tile, c * ts, r * ts, ts)

    for g in game.guards:
        _draw_guard(surface, g, ts)

    _draw_prince(surface, game.prince, ts)
    _draw_hud(surface, game, font)

    if crt:
        _draw_crt(surface)
