"""Renderer canon — pinta una sala completa.

Capas:
  0. Pared del fondo (``backdrop``)
  1. Tiles (losas, rejas, trampas...) y llamas animadas
  2. Personajes (interpolados entre ticks)
  3. Capa delantera: fustes de columnas
  4. HUD
"""

from __future__ import annotations

import pygame

from pop2026canon.domain.chars import Char, CharId
from pop2026canon.domain.constants import TILE_SIZE_X, TILE_SIZE_Y
from pop2026canon.domain.game import Game
from pop2026canon.presentation.char_atlas import CharPalette, draw_kid_frame
from pop2026canon.presentation.layout import LAYOUT
from pop2026canon.presentation.palette import PALETTE
from pop2026canon.presentation.themes import theme_for
from pop2026canon.presentation.tile_atlas import draw_tile


def _room_hash(room_id: int, c: int = 0, r: int = 0) -> int:
    """Hash determinista por (sala, celda) para variación visual estable."""
    return (room_id * 2654435761 + c * 40503 + r * 69621) & 0xFFFFFFFF


def _cell_tile(game: Game, room_id: int, c: int, r: int) -> tuple[int, int]:
    """(tile, modifier) visibles de una celda: estado de trampas y rejas,
    losas caídas y escombros aplicados."""
    from pop2026canon.domain.tiles import Tile
    from pop2026canon.domain.traps import gate_phase

    room = game.level.room(room_id)
    byte = room.fg[r * LAYOUT.room_cols + c]
    tile_val = byte & 0x1F
    modifier = (byte >> 5) & 0x07
    coord = (room_id, c, r)
    piece = Tile(tile_val)
    if piece is Tile.GATE:
        modifier = gate_phase(game.state, coord)
    elif piece in (Tile.CHOMPER, Tile.LOOSE, Tile.SPIKE):
        modifier = game.state.state_at(coord)
    elif piece in (Tile.LEVEL_DOOR_LEFT, Tile.LEVEL_DOOR_RIGHT):
        modifier = int(
            any(
                g[0] == room_id and g[1] in (c - 1, c, c + 1) and g[2] == r
                for g in game.state.open_gates
            )
        )
    # Loose caído: la losa ya no está — agujero real.
    if coord in game.state.fallen_floors:
        tile_val = int(Tile.EMPTY)
    # Escombros de una losa estrellada: tapan pinchos, pociones...
    if coord in game.state.debris_cells:
        if piece in (Tile.TORCH, Tile.TORCH_WITH_DEBRIS):
            tile_val = int(Tile.TORCH_WITH_DEBRIS)
        else:
            tile_val = int(Tile.DEBRIS)
    return tile_val, modifier


def _neighbor_has_floor(game: Game, room_id: int, c: int, r: int) -> bool:
    """¿Hay losa en la celda (c, r), aunque sea de la sala contigua?"""
    from pop2026canon.presentation.tile_atlas import has_floor

    if c < 0 or c >= LAYOUT.room_cols:
        room = game.level.room(room_id)
        nb = room.link_w if c < 0 else room.link_e
        if not (1 <= nb <= len(game.level.rooms)):
            return True  # borde del mundo: muro
        room_id, c = nb, c % LAYOUT.room_cols
    return has_floor(_cell_tile(game, room_id, c, r)[0])


Cell = tuple[int, int, int, int, bool, bool]
"""(col, row, tile, modifier, sin suelo a la izquierda, a la derecha)."""


def room_cells(game: Game) -> tuple[Cell, ...]:
    """Celdas visibles de la sala del kid (sólo las que tienen algo)."""
    from pop2026canon.presentation.tile_atlas import mod_key

    rid = game.kid.room
    out: list[Cell] = []
    for r in range(LAYOUT.room_rows):
        for c in range(LAYOUT.room_cols):
            tile_val, modifier = _cell_tile(game, rid, c, r)
            if tile_val == 0:
                continue
            out.append(
                (
                    c,
                    r,
                    tile_val,
                    mod_key(tile_val, modifier),
                    not _neighbor_has_floor(game, rid, c - 1, r),
                    not _neighbor_has_floor(game, rid, c + 1, r),
                )
            )
    return tuple(out)


def draw_cells(
    surf: pygame.Surface,
    room_id: int,
    cells: tuple[Cell, ...],
    palace: bool,
    theme: str | None = None,
) -> None:
    """Parte estática de la sala: los sprites de los tiles (``theme``:
    clave del tema del nivel)."""
    for c, r, tile_val, modifier, left, right in cells:
        draw_tile(
            surf,
            tile_val,
            c * LAYOUT.tile_w,
            LAYOUT.hud_top + r * LAYOUT.tile_h,
            modifier,
            palace=palace,
            variant=_room_hash(room_id, c, r) % 8,
            edges=(left, right),
            theme=theme,
        )


def draw_animated(surf: pygame.Surface, game: Game, cells: tuple[Cell, ...], t: float) -> None:
    """Parte animada: llamas de antorcha y losas cayendo."""
    from pop2026canon.domain.tiles import Tile
    from pop2026canon.presentation.tile_atlas import draw_torch_flame, torch_flame_px

    for c, r, tile_val, *_ in cells:
        if tile_val in (int(Tile.TORCH), int(Tile.TORCH_WITH_DEBRIS)):
            fx, fy = torch_flame_px(c, r)
            draw_torch_flame(surf, fx, fy, t, seed=c * 3 + r)
    _draw_falling_tiles(surf, game)


def _draw_room_tiles(surf: pygame.Surface, game: Game, t: float = 0.0) -> None:
    """Pinta los 30 tiles de la sala actual (llamas animadas con ``t``)."""
    th = theme_for(game.level.number)
    cells = room_cells(game)
    draw_cells(surf, game.kid.room, cells, th.palace, th.key)
    draw_animated(surf, game, cells, t)


def _draw_front_tiles(surf: pygame.Surface, game: Game) -> None:
    """Capa delantera: fustes de columnas por delante de los personajes."""
    from pop2026canon.presentation.tile_atlas import FRONT_TILES, draw_tile_front

    th = theme_for(game.level.number)
    rid = game.kid.room
    for r in range(LAYOUT.room_rows):
        for c in range(LAYOUT.room_cols):
            tile_val = _cell_tile(game, rid, c, r)[0]
            if tile_val in FRONT_TILES:
                x = c * LAYOUT.tile_w
                y = LAYOUT.hud_top + r * LAYOUT.tile_h
                draw_tile_front(surf, tile_val, x, y, palace=th.palace, theme=th.key)


def _draw_falling_tiles(surf: pygame.Surface, game: Game) -> None:
    """Losas sueltas en caída (canon mobs): una losa que baja por su columna."""
    from pop2026canon.domain.constants import TILE_SIZE_Y
    from pop2026canon.presentation.tile_atlas import draw_falling_slab

    th = theme_for(game.level.number)
    slab_off = LAYOUT.tile_h - LAYOUT.floor_face - LAYOUT.floor_top
    for mob in game.state.falling_tiles:
        if mob.room != game.kid.room:
            continue
        x = mob.col * LAYOUT.tile_w
        top = (
            LAYOUT.hud_top
            + mob.row * LAYOUT.tile_h
            + (LAYOUT.tile_h * mob.y) // TILE_SIZE_Y
            + slab_off
        )
        draw_falling_slab(surf, x, top, palace=th.palace, theme=th.key)


def _char_px(char: Char) -> tuple[int, int]:
    """Convierte la posición tile-based del char a píxeles (pies)."""
    # x sub-tile en [0, TILE_SIZE_X) recorre el ANCHO ÚTIL de la celda
    # (del 15 % al 85 %): el sprite nunca se sale de su celda ni de la
    # ventana en los bordes de la sala.
    inner = LAYOUT.tile_w * 7 // 10
    px_x = (
        char.curr_col * LAYOUT.tile_w
        + LAYOUT.tile_w * 3 // 20
        + (char.x * inner) // (TILE_SIZE_X - 1)
    )
    # Geometría canon: el char ocupa la celda del suelo; ``y`` es la
    # altura de los pies dentro de la fila (0 arriba, 62 en el suelo).
    # Los pies pisan el centro de la cara superior de la losa.
    px_y = (
        LAYOUT.hud_top
        + char.curr_row * LAYOUT.tile_h
        + (LAYOUT.tile_h * char.y) // TILE_SIZE_Y
        - LAYOUT.foot_lift
    )
    return px_x, px_y


def _lerp_char_px(prev: Char | None, char: Char, alpha: float) -> tuple[int, int]:
    """Posición interpolada entre el tick anterior y el actual.

    La lógica corre a 12 FPS pero la pantalla a 60: interpolar la
    posición del char entre ticks elimina el movimiento a saltos de
    celda. Si el char cambió de sala (o se teleportó lejos), se pinta
    directamente en la posición nueva.
    """
    cx, cy = _char_px(char)
    if prev is None or alpha >= 1.0 or prev.room != char.room:
        return cx, cy
    px, py = _char_px(prev)
    if abs(cx - px) > LAYOUT.tile_w * 3 or abs(cy - py) > LAYOUT.tile_h * 2:
        return cx, cy  # teleport (respawn, snap de hang...)
    return (int(px + (cx - px) * alpha), int(py + (cy - py) * alpha))


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


def _draw_chars(
    surf: pygame.Surface, game: Game, prev: Game | None = None, alpha: float = 1.0
) -> None:
    """Pinta el kid + otros chars en la sala visible (interpolados)."""
    visible_room = game.kid.room
    prev_others = prev.others if prev is not None else ()
    # Otros chars primero (detrás)
    for i, char in enumerate(game.others):
        if char.room != visible_room:
            continue
        prev_char = None
        if i < len(prev_others) and prev_others[i].charid is char.charid:
            prev_char = prev_others[i]
        px_x, px_y = _lerp_char_px(prev_char, char, alpha)
        draw_kid_frame(
            surf, char.frame or 15, px_x, px_y, char.direction, _palette_for(char.charid)
        )
    # Kid en primer plano
    prev_kid = prev.kid if prev is not None else None
    px_x, px_y = _lerp_char_px(prev_kid, game.kid, alpha)
    draw_kid_frame(surf, game.kid.frame or 15, px_x, px_y, game.kid.direction, CharPalette.KID)


def render(
    surf: pygame.Surface,
    game: Game,
    font: pygame.font.Font | None = None,
    *,
    show_time: bool = False,
    prev: Game | None = None,
    alpha: float = 1.0,
) -> None:
    """Frame completo sin efectos (modo *headless* y pruebas): pared,
    tiles, personajes, columnas delanteras y HUD.

    ``prev``/``alpha`` interpolan las posiciones de los chars entre el
    tick lógico anterior y el actual (12 FPS lógicos → 60 visuales).
    """
    from pop2026canon.presentation.backdrop import backdrop
    from pop2026canon.presentation.hud import HudState, draw_hud

    _ = font
    surf.fill(PALETTE.bg)
    surf.blit(backdrop(game.kid.room, theme_for(game.level.number).key), (0, LAYOUT.hud_top))
    _draw_room_tiles(surf, game, pygame.time.get_ticks() / 1000.0)
    _draw_chars(surf, game, prev, alpha)
    _draw_front_tiles(surf, game)
    draw_hud(surf, game, HudState(), t=0.0, sand=None, rewinding=False, show_time=show_time)
