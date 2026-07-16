"""Renderer canon — pinta una sala completa.

Capas:
  0. Back wall (degradado + sillería tenue + arcos)
  1. BG tiles (overlays detrás del char)
  2. FG tiles (suelo, gates, chompers...)
  3. Char en primer plano (kid + others)
  4. HUD (tiempo + HP + sword status)
"""

from __future__ import annotations

import pygame

from pop2026canon.domain.chars import Char, CharId
from pop2026canon.domain.constants import TILE_SIZE_X, TILE_SIZE_Y
from pop2026canon.domain.game import Game
from pop2026canon.presentation.char_atlas import CharPalette, draw_kid_frame
from pop2026canon.presentation.layout import LAYOUT
from pop2026canon.presentation.palette import PALETTE
from pop2026canon.presentation.tile_atlas import draw_tile


def _room_hash(room_id: int, c: int = 0, r: int = 0) -> int:
    """Hash determinista por (sala, celda) para variación visual estable."""
    return (room_id * 2654435761 + c * 40503 + r * 69621) & 0xFFFFFFFF


def _draw_back_wall(surf: pygame.Surface, room_id: int = 0) -> None:
    """Pared trasera con degradado + arcos rebajados + decoración por sala."""
    w = surf.get_width()
    top = LAYOUT.hud_top
    h = LAYOUT.room_h
    # Degradado vertical
    steps = 12
    band = max(1, h // steps)
    for i in range(steps):
        t = i / max(1, steps - 1)
        col = tuple(int(PALETTE.bg_far[k] * (1 - t) + PALETTE.bg[k] * t * 0.6) for k in range(3))
        pygame.draw.rect(surf, col, (0, top + i * band, w, band + 1))
    # Arcos rebajados cada 2 tiles
    arch_w = LAYOUT.tile_w * 2 - 10
    arch_h = LAYOUT.tile_h - 24
    arch_top = top + 18
    n_arches = max(1, w // (LAYOUT.tile_w * 2))
    for i in range(n_arches):
        ax = i * LAYOUT.tile_w * 2 + 5
        rect = pygame.Rect(ax, arch_top, arch_w, arch_h)
        pygame.draw.rect(
            surf,
            PALETTE.bg,
            rect,
            border_top_left_radius=arch_w // 2,
            border_top_right_radius=arch_w // 2,
        )
        pygame.draw.rect(
            surf,
            PALETTE.bg_far,
            rect,
            1,
            border_top_left_radius=arch_w // 2,
            border_top_right_radius=arch_w // 2,
        )
    # Decoración determinista por sala: sillares hundidos y alguna
    # ventana estrecha — rompe la monotonía (cada sala se reconoce).
    hsh = _room_hash(room_id)
    for i in range(4):
        bx = ((hsh >> (i * 5)) % max(1, w - 40)) + 8
        by = top + 24 + ((hsh >> (i * 7 + 3)) % max(1, h - 80))
        bw = 14 + ((hsh >> (i * 3)) % 18)
        shade = pygame.Surface((bw, 8), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 26))
        surf.blit(shade, (bx, by))
    if hsh % 5 == 2:
        wx = (hsh >> 9) % max(1, w - 60) + 20
        wy = top + 26
        pygame.draw.rect(
            surf, (8, 6, 12), (wx, wy, 12, 26), border_top_left_radius=6, border_top_right_radius=6
        )
        pygame.draw.rect(
            surf,
            PALETTE.bg_far,
            (wx, wy, 12, 26),
            1,
            border_top_left_radius=6,
            border_top_right_radius=6,
        )


def _draw_room_tiles(surf: pygame.Surface, game: Game) -> None:
    """Pinta los 30 tiles de la sala actual."""
    from pop2026canon.domain.tiles import Tile

    room = game.level.room(game.kid.room)
    for r in range(LAYOUT.room_rows):
        for c in range(LAYOUT.room_cols):
            byte = room.fg[r * LAYOUT.room_cols + c]
            tile_val = byte & 0x1F
            modifier = (byte >> 5) & 0x07
            # Override modifier para gates / chompers / loose con su state actual
            if Tile(tile_val) in (Tile.GATE, Tile.CHOMPER, Tile.LOOSE):
                modifier = game.state.state_at((game.kid.room, c, r))
            # Loose caído: la losa ya no está — agujero real (la física
            # tampoco soporta peso ahí).
            if (game.kid.room, c, r) in game.state.fallen_floors:
                tile_val = int(Tile.EMPTY)
            x = c * LAYOUT.tile_w
            y = LAYOUT.hud_top + r * LAYOUT.tile_h
            draw_tile(surf, tile_val, x, y, modifier)
            # Variación de sillería en suelos: 1 de cada 3 celdas lleva
            # un tinte tenue determinista (texturas "BLOCK1-5" del canon).
            if Tile(tile_val) is Tile.FLOOR and _room_hash(game.kid.room, c, r) % 3 == 0:
                slab_h = max(18, LAYOUT.tile_h // 3)
                tint = pygame.Surface((LAYOUT.tile_w, slab_h - 8), pygame.SRCALPHA)
                tint.fill((0, 0, 0, 22))
                surf.blit(tint, (x, y + 7))


def _char_px(char: Char) -> tuple[int, int]:
    """Convierte la posición tile-based del char a píxeles (pies)."""
    # x sub-tile en [0, TILE_SIZE_X), col en [0, room_cols)
    px_x = char.curr_col * LAYOUT.tile_w + (char.x * LAYOUT.tile_w) // TILE_SIZE_X
    px_x += LAYOUT.tile_w // 2  # centra en la celda
    px_y = (
        LAYOUT.hud_top
        + (char.curr_row + 1) * LAYOUT.tile_h
        - (LAYOUT.tile_h * char.y) // TILE_SIZE_Y
        - 2
    )
    return px_x, px_y


def _palette_for(charid: CharId) -> CharPalette:
    return {
        CharId.KID: CharPalette.KID,
        CharId.SHADOW: CharPalette.SHADOW,
        CharId.GUARD: CharPalette.GUARD,
        CharId.SKELETON: CharPalette.SKELETON,
        CharId.PRINCESS: CharPalette.PRINCESS,
        CharId.VIZIER: CharPalette.VIZIER,
        CharId.MOUSE: CharPalette.MOUSE,
    }.get(charid, CharPalette.KID)


def _draw_chars(surf: pygame.Surface, game: Game) -> None:
    """Pinta el kid + otros chars en la sala visible."""
    visible_room = game.kid.room
    # Otros chars primero (detrás)
    for char in game.others:
        if char.room != visible_room:
            continue
        px_x, px_y = _char_px(char)
        draw_kid_frame(
            surf, char.frame or 15, px_x, px_y, char.direction, _palette_for(char.charid)
        )
    # Kid en primer plano
    px_x, px_y = _char_px(game.kid)
    draw_kid_frame(surf, game.kid.frame or 15, px_x, px_y, game.kid.direction, CharPalette.KID)


def _draw_hud(
    surf: pygame.Surface, game: Game, font: pygame.font.Font, *, show_time: bool = False
) -> None:
    """Banda HUD superior con HP, tiempo, sala y HP del guard visible."""
    w = surf.get_width()
    pygame.draw.rect(surf, PALETTE.bg, (0, 0, w, LAYOUT.hud_top))
    pygame.draw.line(surf, PALETTE.warning, (0, LAYOUT.hud_top - 1), (w, LAYOUT.hud_top - 1), 1)

    # HP del kid — corazones (izquierda, como el original)
    for i in range(game.kid.hp_max):
        cx = 16 + i * 16 + 6
        cy = 18
        col = PALETTE.error if i < game.kid.hp_curr else PALETTE.muted
        pygame.draw.circle(surf, col, (cx - 3, cy - 1), 3)
        pygame.draw.circle(surf, col, (cx + 3, cy - 1), 3)
        pygame.draw.polygon(surf, col, [(cx - 5, cy), (cx + 5, cy), (cx, cy + 6)])

    # HP del guard en la sala visible — derecha (canon: barra azul)
    guard = next(
        (
            c
            for c in game.others
            if c.charid is CharId.GUARD and c.room == game.kid.room and c.alive < 0
        ),
        None,
    )
    if guard is not None:
        for i in range(guard.hp_curr):
            cx = w - 16 - i * 14
            cy = 18
            pygame.draw.rect(surf, PALETTE.accent, (cx - 4, cy - 5, 9, 11), border_radius=2)

    # Texto: nivel y sala
    label = f"{game.level.name} L{game.level.number}/14 S{game.kid.room}/{len(game.level.rooms)}"
    surf.blit(font.render(label, True, PALETTE.primary), (w // 3, 14))

    # Tiempo: bajo demanda (TAB) o siempre en los últimos 5 minutos
    if show_time or game.time.minutes <= 5:
        time_txt = f"{game.time.minutes:02d}:{game.time.ticks // 12:02d}"
        color = PALETTE.warning if game.time.minutes <= 5 else PALETTE.primary
        x = w - 80 if guard is None else w - 170
        surf.blit(font.render(time_txt, True, color), (x, 14))


def render(
    surf: pygame.Surface, game: Game, font: pygame.font.Font, *, show_time: bool = False
) -> None:
    """Renderiza un frame completo."""
    surf.fill(PALETTE.bg)
    _draw_back_wall(surf, game.kid.room)
    _draw_room_tiles(surf, game)
    _draw_chars(surf, game)
    _draw_hud(surf, game, font, show_time=show_time)
