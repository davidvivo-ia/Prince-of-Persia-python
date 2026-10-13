"""Mapa de salas exploradas (menú de pausa).

Las salas del original no tienen coordenadas: sólo enlaces N/S/E/O.
``room_layout`` las coloca en una cuadrícula recorriendo los enlaces
desde la sala de inicio (BFS); si dos salas caen en la misma casilla
(los niveles no siempre son planos), la segunda se desplaza a la
casilla libre más cercana.
"""

from __future__ import annotations

from collections import deque

import pygame

from pop2026canon.domain.level import Level
from pop2026canon.domain.tiles import Tile
from pop2026canon.presentation.palette import PALETTE


def room_layout(level: Level) -> dict[int, tuple[int, int]]:
    """``{room_id: (x, y)}`` en celdas de mapa (pueden ser negativas)."""
    pos: dict[int, tuple[int, int]] = {level.start_room: (0, 0)}
    taken: dict[tuple[int, int], int] = {(0, 0): level.start_room}
    queue = deque([level.start_room])
    while queue:
        rid = queue.popleft()
        rm = level.room(rid)
        x, y = pos[rid]
        for nb, (dx, dy) in (
            (rm.link_n, (0, -1)),
            (rm.link_s, (0, 1)),
            (rm.link_e, (1, 0)),
            (rm.link_w, (-1, 0)),
        ):
            if not (1 <= nb <= len(level.rooms)) or nb in pos:
                continue
            cell = (x + dx, y + dy)
            radius = 1
            while cell in taken:
                cell = (x + dx * (radius + 1), y + dy * (radius + 1))
                radius += 1
            pos[nb] = cell
            taken[cell] = nb
            queue.append(nb)
    return pos


def _has_exit(level: Level, rid: int) -> bool:
    room = level.room(rid)
    return rid != level.start_room and any((b & 0x1F) == int(Tile.LEVEL_DOOR_LEFT) for b in room.fg)


def draw_minimap(
    surf: pygame.Surface,
    level: Level,
    visited: set[int],
    current: int,
    font: pygame.font.Font,
    t: float = 0.0,
) -> None:
    """Pinta el mapa centrado en ``surf`` (sólo salas visitadas y sus
    vecinas inmediatas como "por explorar")."""
    layout = room_layout(level)
    known = set(visited)
    frontier: set[int] = set()
    for rid in visited:
        rm = level.room(rid)
        for nb in (rm.link_n, rm.link_s, rm.link_e, rm.link_w):
            if 1 <= nb <= len(level.rooms) and nb not in known:
                frontier.add(nb)
    shown = known | frontier
    if not shown:
        return
    xs = [layout[r][0] for r in shown if r in layout]
    ys = [layout[r][1] for r in shown if r in layout]
    if not xs:
        return
    w, h = surf.get_size()
    cell_w, cell_h = 70, 44
    span_w = (max(xs) - min(xs) + 1) * cell_w
    span_h = (max(ys) - min(ys) + 1) * cell_h
    scale = min(1.0, (w - 60) / max(1, span_w), (h - 120) / max(1, span_h))
    cw, ch = max(10, int(cell_w * scale)), max(8, int(cell_h * scale))
    ox = (w - (max(xs) - min(xs) + 1) * cw) // 2 - min(xs) * cw
    oy = (h - (max(ys) - min(ys) + 1) * ch) // 2 - min(ys) * ch + 10

    def rect_of(rid: int) -> pygame.Rect:
        x, y = layout[rid]
        return pygame.Rect(ox + x * cw + 3, oy + y * ch + 3, cw - 6, ch - 6)

    # Pasillos entre salas conocidas
    for rid in known:
        if rid not in layout:
            continue
        rm = level.room(rid)
        for nb in (rm.link_e, rm.link_s, rm.link_w, rm.link_n):
            if nb in shown and nb in layout:
                a, b = rect_of(rid).center, rect_of(nb).center
                pygame.draw.line(surf, PALETTE.primary_dark, a, b, 3)
    for rid in shown:
        if rid not in layout:
            continue
        r = rect_of(rid)
        if rid in known:
            fill: tuple[int, ...] = PALETTE.brick_dark
            if rid == current:
                pulse = 0.5 + 0.5 * abs(((t * 2.0) % 2.0) - 1.0)
                fill = tuple(
                    int(PALETTE.brick[i] * pulse + PALETTE.brick_dark[i] * (1 - pulse))
                    for i in range(3)
                )
            pygame.draw.rect(surf, fill, r, border_radius=4)
            pygame.draw.rect(surf, PALETTE.brick_top, r, 1, border_radius=4)
            if _has_exit(level, rid):
                pygame.draw.rect(surf, PALETTE.poster_gold, r.inflate(-r.w // 2, -r.h // 3), 0, 2)
        else:
            pygame.draw.rect(surf, PALETTE.muted, r, 1, border_radius=4)
            q = font.render("?", True, PALETTE.muted)
            surf.blit(q, q.get_rect(center=r.center))
