"""Atlas procedural de tiles — 31 funciones `draw_<tile>`.

Cada tile se pinta con primitivas pygame (rect, line, polygon, circle).
No assets externos. Paleta tributo en `palette.py`.
"""

from __future__ import annotations

import pygame

from pop2026canon.presentation.layout import LAYOUT
from pop2026canon.presentation.palette import PALETTE

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return (
        int(a[0] * (1 - t) + b[0] * t),
        int(a[1] * (1 - t) + b[1] * t),
        int(a[2] * (1 - t) + b[2] * t),
    )


# ---------------------------------------------------------------------------
# Tile draws (signatura uniforme)
# ---------------------------------------------------------------------------


def draw_empty(surf: pygame.Surface, x: int, y: int, modifier: int = 0) -> None:
    """Aire — no pinta nada (fondo del back wall hará el trabajo)."""
    pass


def draw_floor(surf: pygame.Surface, x: int, y: int, modifier: int = 0) -> None:
    """Losa de suelo estilo POP1 en el borde INFERIOR de la celda (geometría
    canon: la superficie del suelo es el borde inferior de la fila y el
    char está de pie dentro de la celda). Encima queda el aire de la fila,
    donde se ve la pared trasera."""
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    slab_h = max(18, th // 3)
    top = y + th - slab_h
    pygame.draw.rect(surf, PALETTE.brick, (x, top, tw, slab_h))
    # Superficie superior iluminada (donde pisa el kid)
    pygame.draw.rect(surf, PALETTE.brick_top, (x, top, tw, 6))
    pygame.draw.line(
        surf, _mix(PALETTE.brick_top, PALETTE.primary, 0.5), (x, top), (x + tw - 1, top), 1
    )
    pygame.draw.line(surf, PALETTE.brick_dark, (x, top + 6), (x + tw - 1, top + 6), 1)
    # Cara de ladrillo: 2 cursos con junta alternada
    course_h = (slab_h - 6) // 2
    col_idx = x // tw
    for i in range(2):
        cy0 = top + 6 + i * course_h
        pygame.draw.line(surf, PALETTE.mortar, (x, cy0 + course_h), (x + tw, cy0 + course_h), 1)
        jx = x + tw // 2 if (i + col_idx) % 2 == 0 else x + tw // 4
        pygame.draw.line(surf, PALETTE.mortar, (jx, cy0), (jx, cy0 + course_h), 1)
    pygame.draw.line(surf, PALETTE.brick_dark, (x, y + th - 1), (x + tw - 1, y + th - 1), 2)


def draw_spike(surf: pygame.Surface, x: int, y: int, modifier: int = 0) -> None:
    """Pinchos de hierro que salen del suelo según su modifier canon
    (``animate_spike``): 0 recogidos (ranura), 1..4 saliendo, 0x8F..0x80
    fuera, 6..8 recogiéndose, 0xFF fuera con un cuerpo clavado."""
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    base_y = y + th - 2
    if modifier == 0:
        extent = 0.0
    elif modifier == 0xFF or modifier & 0x80:
        extent = 1.0
    elif modifier < 5:
        extent = modifier / 4.0
    else:
        extent = max(0.0, (9 - modifier) / 4.0)
    # Ranura en el suelo (siempre visible)
    pygame.draw.rect(surf, PALETTE.bg, (x + 3, base_y - 3, tw - 6, 3))
    if extent <= 0.0:
        return
    n = 4
    sw = (tw - 4) // n
    height = int(30 * extent)
    for i in range(n):
        sx = x + 2 + i * sw
        tip = (sx + sw // 2, base_y - height)
        pygame.draw.polygon(
            surf,
            PALETTE.blade,
            [(sx, base_y), tip, (sx + sw, base_y)],
        )
        pygame.draw.line(surf, _mix(PALETTE.blade, PALETTE.primary, 0.5), (sx, base_y), tip, 1)
        pygame.draw.line(surf, PALETTE.guard_armor, tip, (sx + sw, base_y), 1)
    if modifier == 0xFF:
        pygame.draw.ellipse(surf, PALETTE.error, (x + 4, base_y - 10, tw - 8, 8))


def draw_pillar(surf: pygame.Surface, x: int, y: int, modifier: int = 0) -> None:
    """Columna decorativa estrecha."""
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    cx = x + tw // 2
    pygame.draw.rect(surf, PALETTE.pillar, (cx - 4, y, 8, th))
    pygame.draw.line(
        surf, _mix(PALETTE.pillar, PALETTE.primary, 0.3), (cx - 4, y), (cx - 4, y + th), 1
    )


def draw_gate(surf: pygame.Surface, x: int, y: int, modifier: int = 0) -> None:
    """Portcullis. Modifier 0..7 = altura abierta."""
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    open_amount = max(0, min(7, modifier))
    # Marco
    pygame.draw.rect(surf, PALETTE.brick_dark, (x, y, 4, th))
    pygame.draw.rect(surf, PALETTE.brick_dark, (x + tw - 4, y, 4, th))
    pygame.draw.rect(surf, PALETTE.brick_dark, (x, y, tw, 6))
    # Rastrillo: cuelga del dintel y SUBE al abrirse (0 = bajado del todo
    # hasta el suelo, 7 = recogido arriba, sólo asoman las puntas).
    bars_top = y + 6
    bars_bot = y + th - 4 - (open_amount * (th - 40)) // 7
    n = 5
    for i in range(n):
        bx = x + 5 + (tw - 10) * (i + 1) // (n + 1)
        pygame.draw.line(surf, PALETTE.warning, (bx, bars_top), (bx, bars_bot - 3), 2)
        # Punta
        pygame.draw.polygon(
            surf, PALETTE.warning, [(bx - 2, bars_bot - 3), (bx, bars_bot), (bx + 2, bars_bot - 3)]
        )
    # Travesaños horizontales (siguen a los barrotes)
    for frac in (0.3, 0.65):
        hy = bars_top + int((bars_bot - bars_top) * frac)
        pygame.draw.line(surf, PALETTE.brick_dark, (x + 5, hy), (x + tw - 5, hy), 2)


def draw_stuck(surf: pygame.Surface, x: int, y: int, modifier: int = 0) -> None:
    """Bloque atascado — visualmente como floor con cracks."""
    draw_floor(surf, x, y, modifier)
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    pygame.draw.line(
        surf, PALETTE.brick_dark, (x + tw // 3, y + th // 3), (x + tw * 2 // 3, y + th * 2 // 3), 2
    )


def draw_closer(surf: pygame.Surface, x: int, y: int, modifier: int = 0) -> None:
    """Botón rojo que cierra gates."""
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    cx = x + tw // 2
    cy = y + th - 12
    pygame.draw.rect(surf, PALETTE.muted, (cx - 6, cy, 12, 5))
    pygame.draw.circle(surf, PALETTE.error, (cx, cy - 2), 4)


def draw_doortop_with_floor(surf: pygame.Surface, x: int, y: int, modifier: int = 0) -> None:
    """Tapiz superior con suelo encima."""
    draw_floor(surf, x, y, modifier)
    tw = LAYOUT.tile_w
    pygame.draw.rect(surf, PALETTE.accent, (x + 2, y - 12, tw - 4, 12))


def draw_bigpillar_bottom(surf: pygame.Surface, x: int, y: int, modifier: int = 0) -> None:
    """Mitad inferior de columna grande."""
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    pygame.draw.rect(surf, PALETTE.pillar, (x + 4, y, tw - 8, th))
    pygame.draw.rect(
        surf, _mix(PALETTE.pillar, PALETTE.brick_dark, 0.4), (x + 4, y + th - 10, tw - 8, 10)
    )


def draw_bigpillar_top(surf: pygame.Surface, x: int, y: int, modifier: int = 0) -> None:
    """Mitad superior — capitel."""
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    pygame.draw.rect(surf, PALETTE.pillar, (x + 2, y, tw - 4, th))
    pygame.draw.rect(surf, _mix(PALETTE.pillar, PALETTE.brick_top, 0.3), (x, y, tw, 12))


def draw_potion(surf: pygame.Surface, x: int, y: int, modifier: int = 0) -> None:
    """Poción. Modifier = tipo (1=heal, 2=maxhp, 4=poison, 5=float, 6=time)."""
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    cx = x + tw // 2
    cy = y + th - 24
    type_colors = {
        1: PALETTE.success,  # heal
        2: PALETTE.accent,  # max hp
        3: PALETTE.warning,  # boost
        4: PALETTE.error,  # poison
        5: PALETTE.primary,  # float
        6: PALETTE.warning,  # time
    }
    col = type_colors.get(modifier, PALETTE.success)
    # Corcho
    pygame.draw.rect(surf, PALETTE.brick_dark, (cx - 3, cy - 12, 6, 3))
    # Cuello
    pygame.draw.rect(surf, _mix(col, PALETTE.bg, 0.4), (cx - 2, cy - 9, 4, 4))
    # Cuerpo
    pygame.draw.circle(surf, col, (cx, cy), 7)
    pygame.draw.circle(surf, PALETTE.primary, (cx - 3, cy - 3), 1)


def draw_loose(surf: pygame.Surface, x: int, y: int, modifier: int = 0) -> None:
    """Losa suelta. ``modifier`` es su estado canon: 0 quieta; 1..10 a punto
    de caer (vibra cada vez más); 0x80.. temblando sin caer."""
    jitter = 0
    if modifier:
        phase = modifier & 0x7F
        jitter = (1 if phase % 2 else -1) * (2 if phase > 5 else 1)
    draw_floor(surf, x + jitter, y, 0)
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    slab_h = max(18, th // 3)
    top = y + th - slab_h
    pygame.draw.line(
        surf, PALETTE.bg, (x + jitter + tw // 4, top + 4), (x + jitter + tw * 3 // 4, y + th - 3), 2
    )
    pygame.draw.line(
        surf,
        PALETTE.brick_dark,
        (x + jitter + tw // 5, top + 3),
        (x + jitter + tw // 3, top + 10),
        1,
    )


def draw_doortop(surf: pygame.Surface, x: int, y: int, modifier: int = 0) -> None:
    """Tapiz superior decorativo (sin suelo)."""
    tw = LAYOUT.tile_w
    pygame.draw.rect(surf, PALETTE.accent, (x + 2, y, tw - 4, 14))
    pygame.draw.rect(surf, _mix(PALETTE.accent, PALETTE.bg, 0.5), (x + 4, y + 4, tw - 8, 6))


def draw_mirror(surf: pygame.Surface, x: int, y: int, modifier: int = 0) -> None:
    """Espejo del nivel 4."""
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    pygame.draw.rect(surf, PALETTE.muted, (x + 2, y + 4, tw - 4, th - 16))
    pygame.draw.rect(
        surf, _mix(PALETTE.muted, PALETTE.primary, 0.4), (x + 4, y + 6, tw - 8, th - 20)
    )
    pygame.draw.rect(surf, PALETTE.warning, (x + 2, y + 4, tw - 4, th - 16), 2)


def draw_falling_slab(surf: pygame.Surface, x: int, top: int) -> None:
    """Losa suelta cayendo: la losa sola, a la altura ``top`` (píxeles)."""
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    slab_h = max(18, th // 3)
    pygame.draw.rect(surf, PALETTE.brick, (x, top, tw, slab_h))
    pygame.draw.rect(surf, PALETTE.brick_dark, (x, top, tw, slab_h), 2)
    pygame.draw.line(
        surf, PALETTE.bg, (x + tw // 4, top + 4), (x + tw * 3 // 4, top + slab_h - 3), 2
    )


def draw_debris(surf: pygame.Surface, x: int, y: int, modifier: int = 0) -> None:
    """Restos del loose floor caído."""
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    pygame.draw.rect(surf, _mix(PALETTE.brick, PALETTE.brick_dark, 0.4), (x, y, tw, th))
    for i in range(6):
        px = x + (i * tw) // 6
        py = y + th - 8 - (i % 3) * 3
        pygame.draw.rect(surf, PALETTE.brick_dark, (px, py, 3, 3))


def draw_opener(surf: pygame.Surface, x: int, y: int, modifier: int = 0) -> None:
    """Placa de presión. Modifier 1 = pisada."""
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    depth = 6 if modifier else 8
    top = y + th - 14
    pygame.draw.rect(surf, PALETTE.muted, (x + 4, top + (8 - depth), tw - 8, depth))
    pygame.draw.line(surf, PALETTE.accent, (x + tw // 3, top - 2), (x + tw * 2 // 3, top - 2), 1)


def _draw_level_door_half(surf: pygame.Surface, x: int, y: int, *, left: bool) -> None:
    """Media puerta de salida: arco de piedra de dos celdas de ancho con
    hueco oscuro y escalones que suben hacia el interior."""
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    stone = _mix(PALETTE.brick_dark, PALETTE.primary, 0.25)
    dark = (10, 8, 16)
    # Jamba exterior
    jamb_x = x if left else x + tw - 10
    pygame.draw.rect(surf, stone, (jamb_x, y + 16, 10, th - 16))
    # Hueco de la puerta (interior oscuro)
    inner_x = x + 10 if left else x
    pygame.draw.rect(surf, dark, (inner_x, y + 26, tw - 10, th - 26))
    # Dintel / arco (media bóveda por lado)
    arc_rect = pygame.Rect(x if left else x - tw, y + 8, tw * 2, 44)
    clip = surf.get_clip()
    surf.set_clip(pygame.Rect(x, y, tw, th))
    pygame.draw.ellipse(surf, stone, arc_rect)
    pygame.draw.ellipse(surf, dark, arc_rect.inflate(-20, -16))
    surf.set_clip(clip)
    # Escalones que suben hacia dentro (3 peldaños)
    for i in range(3):
        step_y = y + th - 8 - i * 10
        step_w = (tw - 12) - i * 8
        sx = x + 10 + (i * 4 if left else 2)
        pygame.draw.rect(surf, _mix(stone, PALETTE.primary, 0.3), (sx, step_y, step_w, 4))


def draw_level_door_left(surf: pygame.Surface, x: int, y: int, modifier: int = 0) -> None:
    """Mitad izquierda del exit door."""
    _draw_level_door_half(surf, x, y, left=True)


def draw_level_door_right(surf: pygame.Surface, x: int, y: int, modifier: int = 0) -> None:
    """Mitad derecha."""
    _draw_level_door_half(surf, x, y, left=False)


def draw_chomper(surf: pygame.Surface, x: int, y: int, modifier: int = 0) -> None:
    """Cuchillas verticales. ``modifier`` es el frame canon 1..15 (0 =
    paradas, abiertas); muerden en el 2; 0x80 = sangre."""
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    frame = modifier & 0x7F
    blood = bool(modifier & 0x80)
    # Separación de las hojas: cerradas en el 2, cerrándose en el 1,
    # abriéndose en 3-5, abiertas el resto.
    if frame == 2:
        sep = 1
    elif frame == 1:
        sep = 5
    elif 3 <= frame <= 5:
        sep = 3 + (frame - 2) * 3
    else:
        sep = 12
    # Marco metálico
    pygame.draw.rect(surf, PALETTE.guard_armor, (x + tw // 2 - 3, y, 6, th))
    cx = x + tw // 2
    pygame.draw.polygon(
        surf, PALETTE.blade, [(cx - sep, y + th // 3), (cx, y + th // 2), (cx + sep, y + th // 3)]
    )
    pygame.draw.polygon(
        surf,
        PALETTE.blade,
        [(cx - sep, y + 2 * th // 3), (cx, y + th // 2), (cx + sep, y + 2 * th // 3)],
    )
    if blood:
        pygame.draw.ellipse(surf, PALETTE.error, (cx - 8, y + th - 10, 16, 8))


def draw_torch(surf: pygame.Surface, x: int, y: int, modifier: int = 0) -> None:
    """Antorcha de pared: soporte de hierro, mango y llama a media altura
    de la celda (altura de los ojos del kid), como en el original."""
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    cx = x + tw // 2
    cy = y + th // 2 - 10  # base de la llama
    # Soporte en la pared (anillo + brazo)
    pygame.draw.rect(surf, PALETTE.brick_dark, (cx - 7, cy + 14, 14, 4))
    pygame.draw.rect(surf, PALETTE.brick_dark, (cx - 2, cy + 6, 4, 12))
    # Mango de madera
    pygame.draw.rect(surf, (96, 58, 28), (cx - 3, cy + 2, 6, 14))
    # Llama: exterior naranja, interior rojo, núcleo claro
    pygame.draw.polygon(
        surf,
        PALETTE.warning,
        [(cx - 8, cy + 4), (cx - 3, cy - 14), (cx, cy - 22), (cx + 3, cy - 14), (cx + 8, cy + 4)],
    )
    pygame.draw.polygon(surf, PALETTE.error, [(cx - 4, cy + 3), (cx, cy - 12), (cx + 4, cy + 3)])
    pygame.draw.polygon(surf, (255, 240, 180), [(cx - 2, cy + 2), (cx, cy - 5), (cx + 2, cy + 2)])
    # Halo cálido suave. BLEND_ADD ignora el alpha: la intensidad va en
    # el propio color (RGB bajo), si no sale un disco sólido.
    halo = pygame.Surface((56, 56))
    halo.fill((0, 0, 0))
    pygame.draw.circle(halo, (26, 16, 4), (28, 28), 28)
    pygame.draw.circle(halo, (40, 24, 6), (28, 28), 14)
    surf.blit(halo, (cx - 28, cy - 32), special_flags=pygame.BLEND_ADD)


def draw_wall(surf: pygame.Surface, x: int, y: int, modifier: int = 0) -> None:
    """Muro vertical sin pisable."""
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    pygame.draw.rect(surf, _mix(PALETTE.brick_dark, PALETTE.brick, 0.3), (x, y, tw, th))
    for r in range(0, th, 12):
        pygame.draw.line(surf, PALETTE.mortar, (x, y + r), (x + tw, y + r), 1)


def draw_skeleton_tile(surf: pygame.Surface, x: int, y: int, modifier: int = 0) -> None:
    """Esqueleto tumbado. Modifier 1 = ya despierto."""
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    cy = y + th - 12
    # Calavera
    pygame.draw.circle(surf, PALETTE.primary, (x + tw // 4, cy), 5)
    # Cuerpo
    pygame.draw.line(surf, PALETTE.primary, (x + tw // 4, cy), (x + tw * 3 // 4, cy), 3)
    # Costillas
    for i in range(3):
        rx = x + tw // 4 + (i + 1) * 6
        pygame.draw.line(surf, PALETTE.primary, (rx, cy - 3), (rx, cy + 3), 1)


def draw_sword_pickup(surf: pygame.Surface, x: int, y: int, modifier: int = 0) -> None:
    """Espada recogible."""
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    base_y = y + th - 18
    pygame.draw.line(surf, PALETTE.blade, (x + 4, base_y), (x + tw - 8, base_y), 2)
    pygame.draw.line(surf, PALETTE.warning, (x + tw - 8, base_y - 3), (x + tw - 8, base_y + 3), 2)
    pygame.draw.circle(surf, PALETTE.warning, (x + tw - 4, base_y), 3)
    # Halo
    halo = pygame.Surface((24, 12), pygame.SRCALPHA)
    pygame.draw.ellipse(halo, (*PALETTE.accent, 60), (0, 0, 24, 12))
    surf.blit(halo, (x + 2, base_y - 8), special_flags=pygame.BLEND_ADD)


def draw_balcony_left(surf: pygame.Surface, x: int, y: int, modifier: int = 0) -> None:
    """Balcón izquierdo."""
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    pygame.draw.rect(surf, PALETTE.pillar, (x, y, tw // 2, th))
    pygame.draw.rect(surf, _mix(PALETTE.pillar, PALETTE.brick_top, 0.3), (x, y, tw // 2, 8))


def draw_balcony_right(surf: pygame.Surface, x: int, y: int, modifier: int = 0) -> None:
    """Balcón derecho."""
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    pygame.draw.rect(surf, PALETTE.pillar, (x + tw // 2, y, tw // 2, th))
    pygame.draw.rect(
        surf, _mix(PALETTE.pillar, PALETTE.brick_top, 0.3), (x + tw // 2, y, tw // 2, 8)
    )


def draw_lattice_pillar(surf: pygame.Surface, x: int, y: int, modifier: int = 0) -> None:
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    pygame.draw.rect(surf, PALETTE.pillar, (x + tw // 2 - 1, y, 2, th))


def draw_lattice_down(surf: pygame.Surface, x: int, y: int, modifier: int = 0) -> None:
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    for r in range(0, th, 8):
        pygame.draw.line(surf, PALETTE.pillar, (x + 2, y + r), (x + tw - 2, y + r), 1)


def draw_lattice_small(surf: pygame.Surface, x: int, y: int, modifier: int = 0) -> None:
    tw = LAYOUT.tile_w
    pygame.draw.rect(surf, PALETTE.pillar, (x + tw // 4, y + 4, tw // 2, 12), 1)


def draw_lattice_left(surf: pygame.Surface, x: int, y: int, modifier: int = 0) -> None:
    _tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    pygame.draw.rect(surf, PALETTE.pillar, (x, y, 4, th))


def draw_lattice_right(surf: pygame.Surface, x: int, y: int, modifier: int = 0) -> None:
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    pygame.draw.rect(surf, PALETTE.pillar, (x + tw - 4, y, 4, th))


def draw_torch_with_debris(surf: pygame.Surface, x: int, y: int, modifier: int = 0) -> None:
    draw_debris(surf, x, y, modifier)
    draw_torch(surf, x, y, modifier)


# ---------------------------------------------------------------------------
# Dispatcher por Tile.value
# ---------------------------------------------------------------------------

_DRAW_TABLE = {
    0: draw_empty,
    1: draw_floor,
    2: draw_spike,
    3: draw_pillar,
    4: draw_gate,
    5: draw_stuck,
    6: draw_closer,
    7: draw_doortop_with_floor,
    8: draw_bigpillar_bottom,
    9: draw_bigpillar_top,
    10: draw_potion,
    11: draw_loose,
    12: draw_doortop,
    13: draw_mirror,
    14: draw_debris,
    15: draw_opener,
    16: draw_level_door_left,
    17: draw_level_door_right,
    18: draw_chomper,
    19: draw_torch,
    20: draw_wall,
    21: draw_skeleton_tile,
    22: draw_sword_pickup,
    23: draw_balcony_left,
    24: draw_balcony_right,
    25: draw_lattice_pillar,
    26: draw_lattice_down,
    27: draw_lattice_small,
    28: draw_lattice_left,
    29: draw_lattice_right,
    30: draw_torch_with_debris,
}


# Tiles-suelo con item encima (canon tile_is_floor): se pinta la losa y
# luego el item.
_FLOORED_ITEMS: frozenset[int] = frozenset({2, 6, 10, 13, 15, 16, 17, 18, 19, 21, 22, 23, 24, 30})


def draw_tile(surf: pygame.Surface, tile_value: int, x: int, y: int, modifier: int = 0) -> None:
    """Pinta el tile correspondiente."""
    if tile_value in _FLOORED_ITEMS:
        draw_floor(surf, x, y, 0)
    draw_fn = _DRAW_TABLE.get(tile_value, draw_empty)
    draw_fn(surf, x, y, modifier)
