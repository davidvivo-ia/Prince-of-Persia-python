"""Renderer pygame con estética **vector-POP**.

Dibuja a primitivas (sin sprites bitmap) pero con la silueta del Prince
of Persia original: suelos de ladrillo gruesos, pilares de columna,
príncipe humanoide proporcionado con cinturón rojo, guardia con
armadura plomiza y sable. Overlay opcional de scanlines (CRT).
"""

from __future__ import annotations

import math

import pygame

from pop2026.domain.actions import Action
from pop2026.domain.anim import offset_for
from pop2026.domain.game import Game, GameStatus
from pop2026.domain.geometry import Facing, Position
from pop2026.domain.guard import Guard, GuardMode
from pop2026.domain.level import effective_tile
from pop2026.domain.physics_prince import PhysicsPrince as Prince
from pop2026.domain.tiles import Tile
from pop2026.presentation.theme import LAYOUT, PALETTE, RGB

# ---------------------------------------------------------------------------
# Geometría: convertir celda -> píxeles dentro del área de juego (offset HUD)
# ---------------------------------------------------------------------------


def _cell_to_px(col: int, row: int) -> tuple[int, int]:
    """Coordenada en píxeles de la esquina superior-izquierda de una celda."""
    return col * LAYOUT.tile_w, LAYOUT.hud_top + row * LAYOUT.tile_h


FLOOR_THICKNESS: int = 22
"""Píxeles de grosor del suelo de ladrillo dentro de la celda."""


def _floor_top_y(row: int) -> int:
    """Coordenada Y donde está la superficie pisable de un tile FLOOR en ``row``."""
    _, y = _cell_to_px(0, row)
    return y + LAYOUT.tile_h - FLOOR_THICKNESS


def viewport_col(prince_col: int, level_cols: int) -> int:
    """Columna lógica donde empieza la pantalla visible.

    Cada "habitación" mide ``LAYOUT.cols`` celdas. La cámara salta en
    bloque (room-flick) cuando el príncipe cruza un borde, igual que en
    el motor original.

    Args:
        prince_col: columna lógica del príncipe.
        level_cols: anchura total del nivel.

    Returns:
        Columna donde empieza la habitación visible actual, recortada al
        rango válido del nivel.
    """
    if level_cols <= LAYOUT.cols:
        return 0
    room = max(0, prince_col // LAYOUT.cols)
    max_room = max(0, (level_cols - 1) // LAYOUT.cols)
    return min(room, max_room) * LAYOUT.cols


def total_rooms(level_cols: int) -> int:
    """Cuántas habitaciones lógicas tiene el nivel."""
    if level_cols <= 0:
        return 0
    return max(1, (level_cols + LAYOUT.cols - 1) // LAYOUT.cols)


# ---------------------------------------------------------------------------
# Fondo: pared trasera con sombreado
# ---------------------------------------------------------------------------


def _draw_back_wall(surface: pygame.Surface) -> None:
    """Pinta la pared trasera del calabozo: sillería de piedra + arcos.

    Capas (de atrás hacia delante):

    1. Degradado vertical sutil — cielo profundo / fondo violeta.
    2. Sillería de piedra: bloques rectangulares con mortero claro
       formando un fondo "construido" (no plano).
    3. Antorchas en columnas alternas con halos de luz.
    4. Arcos rebajados en la banda media para dar profundidad de
       galería.
    """
    w = surface.get_width()
    top_y = LAYOUT.hud_top
    h = LAYOUT.height_px - LAYOUT.hud_top

    # 1. Degradado vertical: arriba bg_far, abajo bg.
    steps = 16
    band = max(1, h // steps)
    for i in range(steps):
        t = i / max(1, steps - 1)
        col = tuple(int(PALETTE.bg_far[k] * (1 - t) + PALETTE.bg[k] * t * 0.6) for k in range(3))
        pygame.draw.rect(surface, col, (0, top_y + i * band, w, band + 1))

    # 2. Sillería de piedra al fondo — bloques rectangulares finos.
    stone_h = LAYOUT.tile_h // 3
    stone_w = LAYOUT.tile_w * 2 // 3
    stone_col = _mix(PALETTE.bg_far, PALETTE.pillar, 0.35)
    mortar_col = _mix(PALETTE.bg, PALETTE.bg_far, 0.6)
    rows_back = (h // stone_h) + 1
    for r in range(rows_back):
        sy = top_y + r * stone_h
        offset = (r % 2) * (stone_w // 2)
        x = -offset
        while x < w:
            # Bloque (silueta tenue)
            pygame.draw.rect(surface, stone_col, (x + 1, sy + 1, stone_w - 2, stone_h - 2), 1)
            # Junta horizontal y vertical en mortero claro
            pygame.draw.line(surface, mortar_col, (x, sy), (x + stone_w, sy), 1)
            pygame.draw.line(surface, mortar_col, (x, sy), (x, sy + stone_h), 1)
            x += stone_w

    # 3. Antorchas: una cada 5 tiles, ardiendo en la fila superior.
    for tile_c in range(2, w // LAYOUT.tile_w, 5):
        tx = tile_c * LAYOUT.tile_w + LAYOUT.tile_w // 2
        ty = top_y + LAYOUT.tile_h // 2
        _draw_wall_torch(surface, tx, ty)

    # 4. Arcos rebajados en la banda media — galería profunda.
    arch_h = LAYOUT.tile_h - 14
    arch_w = LAYOUT.tile_w * 2 - 10
    arch_top = top_y + LAYOUT.tile_h + 6
    n_arches = max(1, w // (LAYOUT.tile_w * 2))
    for i in range(n_arches):
        ax = i * LAYOUT.tile_w * 2 + 5
        rect = pygame.Rect(ax, arch_top, arch_w, arch_h)
        pygame.draw.rect(
            surface,
            PALETTE.bg,
            rect,
            border_top_left_radius=arch_w // 2,
            border_top_right_radius=arch_w // 2,
        )
        # Marco de la dovela
        pygame.draw.rect(
            surface,
            PALETTE.bg_far,
            rect,
            1,
            border_top_left_radius=arch_w // 2,
            border_top_right_radius=arch_w // 2,
        )
        # Piedra clave central
        key_w = 4
        key_rect = pygame.Rect(
            rect.centerx - key_w // 2,
            arch_top - 1,
            key_w,
            4,
        )
        pygame.draw.rect(surface, PALETTE.bg_far, key_rect)


def _draw_wall_torch(surface: pygame.Surface, cx: int, cy: int) -> None:
    """Antorcha mural: brazo de hierro + cuenco + llama + halo."""
    # Halo de luz cálido (alpha compuesto).
    halo = pygame.Surface((36, 36), pygame.SRCALPHA)
    for r, a in ((16, 18), (12, 30), (8, 50)):
        pygame.draw.circle(halo, (*PALETTE.warning, a), (18, 18), r)
    surface.blit(halo, (cx - 18, cy - 18), special_flags=pygame.BLEND_ADD)

    # Brazo de hierro saliendo del muro.
    pygame.draw.line(surface, PALETTE.brick_dark, (cx, cy + 2), (cx, cy + 6), 2)
    # Cuenco metálico.
    pygame.draw.rect(surface, PALETTE.guard_armor, (cx - 3, cy + 1, 6, 2))
    # Llama: lóbulo amarillo + núcleo rojo.
    pygame.draw.polygon(
        surface,
        PALETTE.warning,
        [(cx - 3, cy + 1), (cx, cy - 6), (cx + 3, cy + 1)],
    )
    pygame.draw.polygon(
        surface,
        PALETTE.error,
        [(cx - 2, cy), (cx, cy - 4), (cx + 2, cy)],
    )
    # Chispa central.
    pygame.draw.circle(surface, PALETTE.primary, (cx, cy - 3), 1)


# ---------------------------------------------------------------------------
# Tiles
# ---------------------------------------------------------------------------


def _draw_floor(surface: pygame.Surface, x: int, y: int) -> None:
    """Dibuja un tile de suelo: el ladrillo llena toda la celda.

    Estilo Apple II HGR: cuatro cursos horizontales de ladrillo en
    aparejo soga (juntas verticales desplazadas tile a tile), borde
    superior iluminado, sombra inferior y juntas de mortero oscuro.
    Cada tile aporta una variación determinista para evitar el efecto
    "tablero" cuando el suelo se repite.
    """
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    top = y

    # Cuerpo del ladrillo (toda la celda).
    pygame.draw.rect(surface, PALETTE.brick, (x, top, tw, th))

    # Veta clara horizontal a media altura (variación de tono).
    streak_y = top + th // 4
    pygame.draw.line(
        surface,
        _mix(PALETTE.brick, PALETTE.brick_top, 0.35),
        (x + 2, streak_y),
        (x + tw - 3, streak_y),
        1,
    )

    # Sombra inferior — efecto de profundidad pegado al borde.
    pygame.draw.rect(surface, PALETTE.brick_dark, (x, y + th - 3, tw, 3))

    # "Shelf" superior: banda más clara que sobresale 3 px sobre el
    # ladrillo y crea la silueta del suelo flotante característica.
    shelf_h = 4
    pygame.draw.rect(surface, PALETTE.brick_top, (x, top, tw, shelf_h))
    pygame.draw.line(
        surface,
        _mix(PALETTE.brick_top, PALETTE.primary, 0.5),
        (x, top),
        (x + tw - 1, top),
        1,
    )
    # Sombra fina justo debajo del shelf para separarlo del cuerpo.
    pygame.draw.line(
        surface,
        PALETTE.brick_dark,
        (x, top + shelf_h),
        (x + tw - 1, top + shelf_h),
        1,
    )

    # Cuatro cursos de mortero horizontal.
    courses = 4
    course_h = th // courses
    mortar_ys = [top + i * course_h for i in range(1, courses)]
    for my in mortar_ys:
        pygame.draw.line(surface, PALETTE.mortar, (x, my), (x + tw, my), 1)

    # Mortero vertical en aparejo soga: junta desplazada por curso.
    col_idx = x // tw
    half = tw // 2
    course_tops = [top, *mortar_ys, y + th]
    for i in range(courses):
        cy0 = course_tops[i]
        cy1 = course_tops[i + 1]
        # Patrón soga: filas pares junta en mitad, impares al borde.
        if (i + col_idx) % 2 == 0:
            jx = x + half
        else:
            jx = x
            # también dibuja la otra mitad en el borde derecho
            pygame.draw.line(surface, PALETTE.mortar, (x + tw, cy0), (x + tw, cy1), 1)
        pygame.draw.line(surface, PALETTE.mortar, (jx, cy0), (jx, cy1), 1)


def _mix(a: RGB, b: RGB, t: float) -> RGB:
    """Mezcla lineal entre dos colores (``t=0`` → ``a``, ``t=1`` → ``b``)."""
    return (
        int(a[0] * (1 - t) + b[0] * t),
        int(a[1] * (1 - t) + b[1] * t),
        int(a[2] * (1 - t) + b[2] * t),
    )


def _draw_loose_floor(surface: pygame.Surface, x: int, y: int) -> None:
    """Suelo suelto: como FLOOR pero con grieta diagonal a lo largo de toda la celda."""
    _draw_floor(surface, x, y)
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    pygame.draw.line(
        surface,
        PALETTE.bg,
        (x + tw // 4, y + 4),
        (x + 3 * tw // 4, y + th - 6),
        2,
    )


def _draw_spikes(surface: pygame.Surface, x: int, y: int) -> None:
    """Pinchos: hojas alargadas de hierro emergiendo de un nicho oscuro.

    Cada hoja tiene un cuerpo ligeramente cóncavo (no triangular puro),
    filo iluminado al lado izquierdo, lado oscuro al derecho y brillo
    en la punta. La banda inferior es un nicho metálico donde se
    anclan, sugiriendo que salen del suelo.
    """
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    base_y = y + th - 3
    # Nicho metálico oscuro donde se alojan las hojas.
    pygame.draw.rect(surface, PALETTE.mortar, (x, base_y - 2, tw, 4))

    n_spikes = 4
    spike_w = (tw - 4) // n_spikes
    for i in range(n_spikes):
        sx = x + 2 + i * spike_w
        tip_x = sx + spike_w // 2
        tip_y = base_y - 20
        mid_y = base_y - 6

        # Hoja con forma de daga: ancha en base, cuello angosto, punta.
        pygame.draw.polygon(
            surface,
            PALETTE.blade,
            [
                (sx + 1, base_y),
                (tip_x - 2, mid_y),
                (tip_x, tip_y),
                (tip_x + 2, mid_y),
                (sx + spike_w - 1, base_y),
            ],
        )
        # Filo iluminado izquierdo (acaba en la punta).
        pygame.draw.line(
            surface,
            _mix(PALETTE.blade, PALETTE.primary, 0.55),
            (tip_x, tip_y),
            (sx + 1, base_y),
            1,
        )
        # Lado en sombra derecho.
        pygame.draw.line(
            surface,
            PALETTE.guard_armor,
            (tip_x, tip_y),
            (sx + spike_w - 1, base_y),
            1,
        )
        # Brillo de la punta.
        pygame.draw.circle(surface, PALETTE.primary, (tip_x, tip_y + 1), 1)

    # Banda metálica oscura en la base (donde están clavados).
    pygame.draw.rect(surface, PALETTE.brick_dark, (x, base_y, tw, 3))
    pygame.draw.line(
        surface,
        _mix(PALETTE.brick_dark, PALETTE.primary, 0.2),
        (x, base_y),
        (x + tw, base_y),
        1,
    )


def _draw_gate(surface: pygame.Surface, x: int, y: int, *, open_: bool) -> None:
    """Portcullis: barrotes verticales con puntas puntiagudas + marco.

    Cuando está abierta sube a la mitad superior y deja paso libre.
    """
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    bars_top = y + (-th // 4 if open_ else 0)
    bars_bot = y + th - FLOOR_THICKNESS
    # Marco (jambas laterales)
    pygame.draw.rect(surface, PALETTE.brick_dark, (x, y, 3, bars_bot - y))
    pygame.draw.rect(surface, PALETTE.brick_dark, (x + tw - 3, y, 3, bars_bot - y))
    # Dintel superior (cabecero)
    pygame.draw.rect(surface, PALETTE.brick_dark, (x, y, tw, 4))
    # Travesaño superior dorado de la reja
    pygame.draw.line(surface, PALETTE.warning, (x + 3, bars_top), (x + tw - 3, bars_top), 2)
    # Barrotes verticales con punta de lanza inferior
    n = 5
    for i in range(n):
        bx = x + 4 + (tw - 8) * (i + 1) // (n + 1)
        pygame.draw.line(surface, PALETTE.warning, (bx, bars_top), (bx, bars_bot - 3), 2)
        # Punta puntiaguda inferior
        pygame.draw.polygon(
            surface,
            PALETTE.warning,
            [(bx - 2, bars_bot - 3), (bx, bars_bot + 1), (bx + 2, bars_bot - 3)],
        )
    # Brillo sutil en cada barrote
    for i in range(n):
        bx = x + 4 + (tw - 8) * (i + 1) // (n + 1)
        pygame.draw.line(
            surface,
            _mix(PALETTE.warning, PALETTE.primary, 0.4),
            (bx - 1, bars_top + 1),
            (bx - 1, bars_bot - 5),
            1,
        )


def _draw_pressure(surface: pygame.Surface, x: int, y: int) -> None:
    """Placa de presión: piedra empotrada al ras del suelo con bordes biselados."""
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    top = y + th - FLOOR_THICKNESS - 3
    plate = pygame.Rect(x + 4, top, tw - 8, 5)
    pygame.draw.rect(surface, PALETTE.muted, plate)
    # Bisel superior iluminado
    pygame.draw.line(
        surface,
        _mix(PALETTE.muted, PALETTE.primary, 0.4),
        (plate.x, plate.y),
        (plate.right - 1, plate.y),
        1,
    )
    # Bisel inferior en sombra
    pygame.draw.line(
        surface,
        PALETTE.brick_dark,
        (plate.x, plate.bottom - 1),
        (plate.right - 1, plate.bottom - 1),
        1,
    )
    # Marca arcana violeta (runa central)
    pygame.draw.line(
        surface,
        PALETTE.accent,
        (plate.centerx - 4, plate.centery),
        (plate.centerx + 4, plate.centery),
        1,
    )


def _draw_potion(surface: pygame.Surface, x: int, y: int, *, color: RGB) -> None:
    """Frasco de poción: corcho + cuello + cuerpo bulboso + brillo + líquido."""
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    cx = x + tw // 2
    cy = y + th - FLOOR_THICKNESS - 12
    # Corcho marrón
    pygame.draw.rect(surface, PALETTE.brick_dark, (cx - 3, cy - 12, 6, 3))
    # Cuello del frasco
    pygame.draw.rect(surface, _mix(color, PALETTE.bg, 0.35), (cx - 2, cy - 9, 4, 4))
    # Cuerpo bulboso
    pygame.draw.circle(surface, color, (cx, cy), 7)
    # Sombra inferior del cuerpo
    pygame.draw.circle(surface, _mix(color, PALETTE.bg, 0.5), (cx + 2, cy + 2), 5, 1)
    # Brillo superior izquierdo
    pygame.draw.circle(surface, PALETTE.primary, (cx - 3, cy - 3), 1)
    # Burbuja flotando dentro
    pygame.draw.circle(surface, _mix(color, PALETTE.primary, 0.5), (cx + 1, cy - 1), 1)


def _draw_sword_pickup(surface: pygame.Surface, x: int, y: int) -> None:
    """Sable tirado: hoja, contraguardia + pomo + halo arcano."""
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    base_y = y + th - FLOOR_THICKNESS - 4
    blade_x0 = x + 6
    blade_x1 = x + tw - 10
    # Hoja con filo iluminado
    pygame.draw.line(surface, PALETTE.blade, (blade_x0, base_y), (blade_x1, base_y), 2)
    pygame.draw.line(
        surface,
        _mix(PALETTE.blade, PALETTE.primary, 0.4),
        (blade_x0 + 1, base_y - 1),
        (blade_x1 - 1, base_y - 1),
        1,
    )
    # Contraguardia (cruceta)
    pygame.draw.line(
        surface,
        PALETTE.warning,
        (blade_x1, base_y - 3),
        (blade_x1, base_y + 3),
        2,
    )
    # Empuñadura envuelta + pomo
    pygame.draw.rect(surface, PALETTE.brick_dark, (blade_x1 + 1, base_y - 1, 3, 3))
    pygame.draw.circle(surface, PALETTE.warning, (blade_x1 + 5, base_y), 2)
    # Halo arcano violeta tenue por encima
    halo_cx = (blade_x0 + blade_x1) // 2
    for r, a in ((4, 1), (3, 2), (2, 3)):
        col = _mix(PALETTE.accent, PALETTE.bg, 1 - 0.18 * a)
        pygame.draw.circle(surface, col, (halo_cx, base_y - 4), r, 1)


def _draw_exit(surface: pygame.Surface, x: int, y: int) -> None:
    """Arco de salida: portal con dovelas + halo violeta interno."""
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    arch_top = y + 4
    arch_bot = y + th - FLOOR_THICKNESS
    rect = pygame.Rect(x + 3, arch_top, tw - 6, arch_bot - arch_top)
    radius = (tw - 6) // 2

    # Halo interior (gradiente desde violeta a fondo).
    for inset, alpha in ((0, 0.45), (3, 0.3), (6, 0.15)):
        r = rect.inflate(-inset * 2, -inset * 2)
        col = _mix(PALETTE.bg_far, PALETTE.accent, alpha)
        pygame.draw.rect(
            surface,
            col,
            r,
            border_top_left_radius=max(0, radius - inset),
            border_top_right_radius=max(0, radius - inset),
        )

    # Marco grueso del arco (dovelas).
    pygame.draw.rect(
        surface,
        PALETTE.accent,
        rect,
        3,
        border_top_left_radius=radius,
        border_top_right_radius=radius,
    )
    # Piedra clave (dovela central iluminada).
    key_w = 6
    key_rect = pygame.Rect(rect.centerx - key_w // 2, arch_top - 1, key_w, 5)
    pygame.draw.rect(surface, _mix(PALETTE.accent, PALETTE.primary, 0.4), key_rect)
    # Antorchas a los lados del arco.
    for tx in (rect.x - 2, rect.right + 1):
        pygame.draw.line(surface, PALETTE.brick_dark, (tx, arch_top + 8), (tx, arch_top + 16), 2)
        pygame.draw.circle(surface, PALETTE.warning, (tx, arch_top + 6), 2)
        pygame.draw.circle(surface, PALETTE.error, (tx, arch_top + 5), 1)


def _draw_pillar(surface: pygame.Surface, col: int) -> None:
    """Columna arquitectónica con capitel + fuste estriado + basa.

    Estética de pilar de madera oscura con relieves: capitel en cabecera
    (más ancho), fuste con dos acanaladuras verticales en sombra y
    realce y basa cuadrada al pie.
    """
    cx = col * LAYOUT.tile_w + LAYOUT.tile_w // 2
    top = LAYOUT.hud_top
    bot = LAYOUT.hud_top + LAYOUT.rows * LAYOUT.tile_h
    shaft_w = 6
    cap_w = 10
    cap_h = 6
    base_h = 5

    # Fuste principal.
    pygame.draw.rect(
        surface, PALETTE.pillar, (cx - shaft_w // 2, top + cap_h, shaft_w, bot - top - cap_h)
    )
    # Acanaladuras verticales (sombra al centro + realce a izquierda).
    pygame.draw.line(
        surface,
        PALETTE.mortar,
        (cx, top + cap_h),
        (cx, bot - base_h),
        1,
    )
    pygame.draw.line(
        surface,
        _mix(PALETTE.pillar, PALETTE.primary, 0.25),
        (cx - 2, top + cap_h + 1),
        (cx - 2, bot - base_h - 1),
        1,
    )

    # Capitel (cabecera) ligeramente más ancho.
    pygame.draw.rect(
        surface,
        _mix(PALETTE.pillar, PALETTE.brick_top, 0.15),
        (cx - cap_w // 2, top, cap_w, cap_h),
    )
    pygame.draw.line(
        surface,
        PALETTE.brick_top,
        (cx - cap_w // 2, top),
        (cx + cap_w // 2 - 1, top),
        1,
    )
    pygame.draw.line(
        surface,
        PALETTE.mortar,
        (cx - cap_w // 2, top + cap_h - 1),
        (cx + cap_w // 2 - 1, top + cap_h - 1),
        1,
    )

    # Basa cuadrada al pie del fuste.
    base_y = bot - base_h
    pygame.draw.rect(
        surface,
        _mix(PALETTE.pillar, PALETTE.brick_dark, 0.3),
        (cx - cap_w // 2, base_y, cap_w, base_h),
    )
    pygame.draw.line(
        surface,
        PALETTE.brick_dark,
        (cx - cap_w // 2, bot - 1),
        (cx + cap_w // 2 - 1, bot - 1),
        1,
    )


def _draw_ceiling_strip(surface: pygame.Surface) -> None:
    """Banda fina superior con textura de techo de calabozo."""
    w = surface.get_width()
    y = LAYOUT.hud_top
    pygame.draw.rect(surface, PALETTE.brick_dark, (0, y, w, 4))
    pygame.draw.line(surface, PALETTE.brick_top, (0, y), (w, y), 1)


# ---------------------------------------------------------------------------
# Príncipe — humanoide grande con poses por acción
# ---------------------------------------------------------------------------


def _draw_humanoid(
    surface: pygame.Surface,
    feet_x: int,
    feet_y: int,
    facing: Facing,
    *,
    skin: RGB,
    shadow: RGB,
    sash: RGB | None,
    weapon: bool,
    pose: str,
    phase: float,
    extra_ticks: int = 0,
) -> None:
    """Dibuja un humanoide con poses variables.

    Args:
        feet_x, feet_y: posición de los pies (eje vertical inferior).
        facing: hacia dónde mira (afecta sable y dirección de arm-swing).
        skin: color piel/ropa principal.
        shadow: color de sombra/calzado.
        sash: color de cinturón rojo; ``None`` si no lo lleva (guardia).
        weapon: si está empuñando sable.
        pose: ``"stand"``, ``"walk"``, ``"jump"``, ``"fall"``, ``"crouch"``,
            ``"strike"``, ``"parry"``, ``"hurt"``, ``"dead"``.
        phase: 0..1 dentro de la acción (para animar el paso).
    """
    fdir = 1 if facing is Facing.RIGHT else -1

    # Posicionado del cuerpo — silueta compacta tipo POP1 Apple II (~28 px alto).
    body_h = 28
    head_r = 4
    torso_w = 10
    torso_h = 12

    # Si pose == "dead": colapso gradual durante 30 ticks y luego
    # postura horizontal final.
    if pose == "dead":
        # progress 0..1: rotación desde de pie a tumbado.
        progress = min(1.0, extra_ticks / 30.0)
        # Lerp del torso desde vertical (ángulo 0) a horizontal (ángulo pi/2).
        angle = progress * (math.pi / 2)
        sin_a = math.sin(angle)
        cos_a = math.cos(angle)
        # Cabeza desciende y se separa lateralmente al colapsar.
        head_off_x = int(12 * sin_a) * fdir
        head_off_y = -int(20 * cos_a) - 3
        # Torso como rect inclinado (interpolación visual con dos segmentos).
        body_len = 22
        body_dx = int(body_len * sin_a) * fdir
        body_dy = -int(body_len * cos_a)
        # Cuerpo del torso (línea gruesa).
        pygame.draw.line(
            surface,
            skin,
            (feet_x, feet_y - 1),
            (feet_x - body_dx // 4, feet_y + body_dy + 3),
            5,
        )
        # Pierna doblada bajo el cuerpo.
        pygame.draw.line(
            surface,
            shadow,
            (feet_x, feet_y - 1),
            (feet_x + 6 * fdir, feet_y),
            3,
        )
        # Cabeza
        pygame.draw.circle(surface, skin, (feet_x + head_off_x, feet_y + head_off_y), head_r)
        # Charco oscuro creciente bajo el cuerpo (cuando ya está caído).
        if progress > 0.7:
            pool_w = int(28 * (progress - 0.7) / 0.3)
            pool = pygame.Surface((pool_w + 4, 4), pygame.SRCALPHA)
            pygame.draw.ellipse(pool, (*PALETTE.error, 100), pool.get_rect())
            surface.blit(pool, (feet_x - pool_w // 2 - 2, feet_y - 1))
        # Sash al final (si tiene)
        if sash is not None and progress > 0.5:
            pygame.draw.rect(surface, sash, (feet_x - 2, feet_y + body_dy + 3, 6, 2))
        return

    # Ajuste de altura si está agachado, golpeado o aterrizando.
    if pose == "crouch":
        body_h = 18
        torso_h = 8
    if pose == "land":
        # Compresión moderada al aterrizar.
        body_h = 22
        torso_h = 9
    if pose == "hurt":
        body_h = 26

    # Pose "hang": cuelga del borde con brazos arriba.
    if pose == "hang":
        # Manos en el borde superior (la repisa); cuerpo dangling abajo.
        hand_y = feet_y - 4  # las manos quedan justo encima del cuerpo
        # Dibuja brazos extendidos hacia arriba en sentido contrario a facing
        # (el príncipe mira hacia la repisa, sus manos la agarran).
        hands_dir = -fdir  # las manos van hacia donde mira (repisa atrás del fdir)
        # Cuerpo y cabeza
        body_top = hand_y + 4
        torso_top = body_top
        torso_bot = torso_top + 18
        # Brazos arriba (de los hombros a las manos en la repisa)
        shoulder_l = (feet_x - 4, body_top + 2)
        shoulder_r = (feet_x + 4, body_top + 2)
        hand_l = (feet_x + hands_dir * 6 - 3, hand_y)
        hand_r = (feet_x + hands_dir * 6 + 3, hand_y)
        pygame.draw.line(surface, skin, shoulder_l, hand_l, 3)
        pygame.draw.line(surface, skin, shoulder_r, hand_r, 3)
        # Torso
        pygame.draw.polygon(
            surface,
            skin,
            [
                (feet_x - 6, torso_top),
                (feet_x + 6, torso_top),
                (feet_x + 5, torso_bot),
                (feet_x - 5, torso_bot),
            ],
        )
        if sash is not None:
            pygame.draw.rect(surface, sash, (feet_x - 5, torso_bot - 3, 10, 3))
        # Piernas colgando (ligeramente cruzadas, sin balanceo)
        pygame.draw.line(surface, skin, (feet_x - 3, torso_bot), (feet_x - 2, torso_bot + 10), 3)
        pygame.draw.line(surface, skin, (feet_x + 3, torso_bot), (feet_x + 2, torso_bot + 10), 3)
        # Cabeza (entre los brazos elevados)
        head_cy = body_top - 2
        pygame.draw.circle(surface, skin, (feet_x, head_cy), head_r)
        # Pequeño detalle del filo del sable si lo lleva (envainado en cadera)
        if weapon:
            pygame.draw.line(
                surface,
                PALETTE.warning,
                (feet_x - fdir * 5, torso_bot - 2),
                (feet_x - fdir * 5, torso_bot + 4),
                2,
            )
        return

    head_cx = feet_x
    head_cy = feet_y - body_h + head_r
    torso_top = head_cy + head_r
    torso_bot = torso_top + torso_h
    hip_y = torso_bot

    # Piernas
    leg_sway = 0.0
    if pose in ("walk", "run", "advance", "retreat"):
        leg_sway = math.sin(phase * math.pi * 2) * 5
    if pose == "jump":
        leg_sway = -4
    if pose == "fall":
        leg_sway = 2

    foot_l = (head_cx - 4 + int(leg_sway), feet_y)
    foot_r = (head_cx + 4 - int(leg_sway), feet_y)
    pygame.draw.line(surface, skin, (head_cx - 3, hip_y), foot_l, 3)
    pygame.draw.line(surface, skin, (head_cx + 3, hip_y), foot_r, 3)
    pygame.draw.circle(surface, shadow, foot_l, 2)
    pygame.draw.circle(surface, shadow, foot_r, 2)

    # Torso (trapecio)
    pygame.draw.polygon(
        surface,
        skin,
        [
            (head_cx - torso_w // 2, torso_top),
            (head_cx + torso_w // 2, torso_top),
            (head_cx + torso_w // 2 - 1, torso_bot),
            (head_cx - torso_w // 2 + 1, torso_bot),
        ],
    )
    # Cinturón rojo
    if sash is not None:
        sash_y = torso_bot - 3
        pygame.draw.rect(surface, sash, (head_cx - torso_w // 2 + 1, sash_y, torso_w - 2, 3))

    # Brazos
    arm_swing = 0.0
    if pose in ("walk", "run", "advance", "retreat"):
        arm_swing = -math.sin(phase * math.pi * 2) * 4
    shoulder_l = (head_cx - torso_w // 2, torso_top + 3)
    shoulder_r = (head_cx + torso_w // 2, torso_top + 3)
    if pose in ("strike", "lunge"):
        # Estocada: la versión LUNGE empuja más hacia delante.
        is_lunge = pose == "lunge"
        reach = 26 if is_lunge else 16
        blade_extra = 22 if is_lunge else 14
        hand_x = head_cx + fdir * reach
        hand_y = torso_top + 6
        front_shoulder = shoulder_r if fdir > 0 else shoulder_l
        back_shoulder = shoulder_l if fdir > 0 else shoulder_r
        pygame.draw.line(surface, skin, front_shoulder, (hand_x, hand_y), 3)
        pygame.draw.line(surface, skin, back_shoulder, (head_cx - fdir * 6, torso_top + 10), 3)
        if weapon:
            blade_end = (hand_x + fdir * blade_extra, hand_y - 2)
            # Trail aditivo del sable durante la ventana de impacto.
            if 0.35 <= phase <= 0.85:
                # Stack de 3 estelas cada vez más tenue, dibujadas como
                # arcos detrás del sable, en BLEND_ADD para que destaque.
                trail_surf = pygame.Surface(
                    (abs(fdir * (blade_extra + 8)) + 4, 20), pygame.SRCALPHA
                )
                origin_x = 2 if fdir > 0 else trail_surf.get_width() - 2
                for layer, alpha in ((0, 140), (2, 90), (4, 50)):
                    col = (*PALETTE.accent, alpha)
                    pygame.draw.line(
                        trail_surf,
                        col,
                        (origin_x, 8 + layer),
                        (origin_x + fdir * (blade_extra + 6 - layer), 6 + layer),
                        2,
                    )
                blit_x = hand_x - origin_x
                surface.blit(trail_surf, (blit_x, hand_y - 8), special_flags=pygame.BLEND_ADD)
                # Chispa en la punta del sable.
                pygame.draw.circle(surface, PALETTE.primary, blade_end, 2)
            pygame.draw.line(
                surface, PALETTE.blade, (hand_x, hand_y), blade_end, 3 if is_lunge else 2
            )
            pygame.draw.line(
                surface, PALETTE.warning, (hand_x - 1, hand_y - 2), (hand_x + 1, hand_y + 2), 2
            )
    elif pose == "parry":
        # Sable en guardia vertical delante del cuerpo
        guard_x = head_cx + fdir * 8
        pygame.draw.line(surface, skin, shoulder_l, (guard_x, torso_top + 8), 3)
        pygame.draw.line(surface, skin, shoulder_r, (guard_x, torso_top + 8), 3)
        if weapon:
            pygame.draw.line(
                surface, PALETTE.blade, (guard_x, torso_top - 4), (guard_x, torso_top + 14), 2
            )
    elif pose == "jump":
        pygame.draw.line(surface, skin, shoulder_l, (head_cx - 6, torso_top - 4), 3)
        pygame.draw.line(surface, skin, shoulder_r, (head_cx + 6, torso_top - 4), 3)
    else:
        # Caminar / quieto / caer
        pygame.draw.line(
            surface,
            skin,
            shoulder_l,
            (head_cx - 5 + int(arm_swing), hip_y - 2),
            3,
        )
        pygame.draw.line(
            surface,
            skin,
            shoulder_r,
            (head_cx + 5 - int(arm_swing), hip_y - 2),
            3,
        )
        # Sable enfundado (línea fina en la cadera) si lo tiene
        if weapon:
            hilt = (head_cx - fdir * (torso_w // 2 - 1), hip_y - 4)
            pygame.draw.line(surface, PALETTE.warning, hilt, (hilt[0], hilt[1] + 6), 2)

    # Cabeza
    pygame.draw.circle(surface, skin, (head_cx, head_cy), head_r)

    # Turbante / casco — más visible cuando es príncipe (sash != None) o
    # guardia (sash == None pero con armadura).
    if sash is not None:
        # Príncipe: turbante con pliegue diagonal y banda violeta.
        turban_color = _mix(skin, shadow, 0.45)
        # Banda principal del turbante (arco arriba de la cabeza)
        pygame.draw.arc(
            surface,
            turban_color,
            (head_cx - head_r - 1, head_cy - head_r - 2, (head_r + 1) * 2, (head_r + 2) * 2),
            0,
            math.pi,
            2,
        )
        # Pliegue lateral del turbante (vuela hacia atrás del facing)
        flap_x = head_cx - fdir * (head_r + 1)
        pygame.draw.polygon(
            surface,
            turban_color,
            [
                (flap_x, head_cy - 1),
                (flap_x - fdir * 3, head_cy - 3),
                (flap_x - fdir * 2, head_cy + 1),
            ],
        )
        # Banda decorativa violeta
        pygame.draw.line(
            surface,
            PALETTE.accent,
            (head_cx - head_r, head_cy - head_r),
            (head_cx + head_r, head_cy - head_r),
            1,
        )
        # Capa ondeando atrás (visible al correr / saltar)
        if pose in ("walk", "run", "jump", "fall", "advance", "retreat"):
            cape_back_x = head_cx - fdir * (torso_w // 2 + 1)
            cape_amp = int(math.sin(phase * math.pi * 2) * 2)
            pygame.draw.polygon(
                surface,
                sash,
                [
                    (cape_back_x, torso_top + 2),
                    (cape_back_x - fdir * (4 + cape_amp), torso_top + 6),
                    (cape_back_x - fdir * (3 + cape_amp), hip_y - 2),
                    (cape_back_x, hip_y - 4),
                ],
            )
    else:
        # Guardia: casco con cresta lateral oscura.
        helmet_top = head_cy - head_r - 1
        pygame.draw.arc(
            surface,
            shadow,
            (head_cx - head_r - 1, helmet_top, (head_r + 1) * 2, (head_r + 1) * 2),
            0,
            math.pi,
            2,
        )
        # Cresta del casco (línea vertical breve)
        pygame.draw.line(
            surface,
            shadow,
            (head_cx, helmet_top - 2),
            (head_cx, head_cy - head_r),
            2,
        )

    # Ojo
    eye_x = head_cx + fdir * 3
    eye_y = head_cy - 1
    pygame.draw.circle(surface, PALETTE.bg, (eye_x, eye_y), 1)


def _pose_from_action(p: Prince | Guard) -> str:
    if not p.alive:
        return "dead"
    a = p.action
    if a is Action.STRIKE:
        return "strike"
    if a is Action.LUNGE:
        return "lunge"
    if a is Action.PARRY:
        return "parry"
    if a is Action.HURT:
        return "hurt"
    if a is Action.CROUCH:
        return "crouch"
    if a is Action.HANG:
        return "hang"
    if a is Action.LAND:
        return "land"
    if a in (Action.JUMP_V, Action.JUMP_R):
        return "jump"
    if a is Action.FALL:
        return "fall"
    if a in (Action.WALK, Action.RUN):
        return "walk"
    if a in (Action.ADVANCE, Action.RETREAT):
        return "advance" if a is Action.ADVANCE else "retreat"
    return "stand"


def _phase(p: Prince | Guard) -> float:
    from pop2026.domain.actions import duration_ticks

    dur = duration_ticks(p.action)
    return p.ticks_in_action / max(1, dur)


def _smooth_feet(
    col: int,
    row: int,
    action: Action,
    ticks: int,
    facing: Facing,
    *,
    viewport_x: int = 0,
) -> tuple[int, int]:
    """Calcula píxeles ``(feet_x, feet_y)`` con offset sub-celda (guards)."""
    dx, dy = offset_for(action=action, ticks=ticks, facing_value=int(facing))
    feet_x = int((col - viewport_x + dx) * LAYOUT.tile_w + LAYOUT.tile_w / 2)
    feet_y = int(_floor_top_y(row) + dy * LAYOUT.tile_h)
    return feet_x, feet_y


def _continuous_feet(p: Prince, viewport_x: int = 0) -> tuple[int, int]:
    """Calcula los píxeles del pie del príncipe desde su posición continua.

    Con el ladrillo llenando la celda entera, el borde superior del
    suelo está en ``row * tile_h + hud_top``. Los pies del príncipe
    grounded tienen ``body.pos.y + half_h == row``, así que el píxel
    coincide directamente con la multiplicación: sin offset adicional.
    """
    from pop2026.domain.physics import PRINCE_H

    half_h = PRINCE_H / 2.0
    feet_x = int((p.body.pos.x - viewport_x) * LAYOUT.tile_w)
    feet_y = int((p.body.pos.y + half_h) * LAYOUT.tile_h + LAYOUT.hud_top)
    return feet_x, feet_y


def _draw_landing_dust(surface: pygame.Surface, feet_x: int, feet_y: int, phase: float) -> None:
    """Nubecilla de polvo expandiéndose al aterrizar (fase 0..1)."""
    radius = 3 + int(phase * 4)
    alpha = max(0, int(180 * (1 - phase)))
    dust = pygame.Surface((radius * 4, radius * 2), pygame.SRCALPHA)
    col = (*PALETTE.muted, alpha)
    for dx in (-radius, 0, radius):
        pygame.draw.circle(dust, col, (radius * 2 + dx, radius), max(1, radius - 1))
    surface.blit(dust, (feet_x - radius * 2, feet_y - radius + 2))


def _draw_hit_flash(surface: pygame.Surface, feet_x: int, feet_y: int, phase: float) -> None:
    """Flash rojo radial al recibir golpe (fase 0..1)."""
    if phase > 0.6:
        return
    intensity = int(160 * (1 - phase / 0.6))
    flash = pygame.Surface((48, 48), pygame.SRCALPHA)
    pygame.draw.circle(flash, (*PALETTE.error, intensity), (24, 24), 20)
    pygame.draw.circle(flash, (*PALETTE.error, intensity // 2), (24, 24), 12)
    surface.blit(flash, (feet_x - 24, feet_y - 38), special_flags=pygame.BLEND_ADD)


def _draw_prince(surface: pygame.Surface, p: Prince, viewport_x: int = 0) -> None:
    feet_x, feet_y = _continuous_feet(p, viewport_x=viewport_x)

    # Efecto: polvo al aterrizar (durante la animación LAND).
    if p.action is Action.LAND:
        from pop2026.domain.actions import duration_ticks

        ph = p.ticks_in_action / max(1, duration_ticks(Action.LAND))
        _draw_landing_dust(surface, feet_x, feet_y, ph)

    # Efecto: flash rojo al recibir golpe.
    if p.action is Action.HURT:
        from pop2026.domain.actions import duration_ticks

        ph = p.ticks_in_action / max(1, duration_ticks(Action.HURT))
        _draw_hit_flash(surface, feet_x, feet_y, ph)

    # Respiración sutil en idle (STAND, PARRY) — pequeño bob de 1 px.
    breath_y = 0
    if p.action is Action.STAND:
        breath_y = int(math.sin(p.ticks_in_action * 0.06) * 1)

    _draw_humanoid(
        surface,
        feet_x,
        feet_y + breath_y,
        p.facing,
        skin=PALETTE.primary,
        shadow=PALETTE.primary_dark,
        sash=PALETTE.cloth,
        weapon=p.has_sword,
        pose=_pose_from_action(p),
        phase=_phase(p),
        extra_ticks=p.ticks_in_action,
    )


def _draw_guard(surface: pygame.Surface, g: Guard, viewport_x: int = 0) -> None:
    # Esqueleto: paleta espectral (gris perla / violeta apagado).
    if g.is_skeleton:
        skin = (0xCF, 0xCF, 0xDC)
        shadow = (0x5E, 0x4F, 0x7A)
    else:
        skin = PALETTE.guard_skin
        shadow = PALETTE.guard_armor

    if g.mode is GuardMode.DEAD:
        feet_x, feet_y = _smooth_feet(
            g.pos.col, g.pos.row, Action.DEAD, 0, g.facing, viewport_x=viewport_x
        )
        _draw_humanoid(
            surface,
            feet_x,
            feet_y,
            g.facing,
            skin=skin,
            shadow=shadow,
            sash=None,
            weapon=False,
            pose="dead",
            phase=0.0,
            extra_ticks=g.ticks_in_action,
        )
        return
    feet_x, feet_y = _smooth_feet(
        g.pos.col, g.pos.row, g.action, g.ticks_in_action, g.facing, viewport_x=viewport_x
    )
    _draw_humanoid(
        surface,
        feet_x,
        feet_y,
        g.facing,
        skin=skin,
        shadow=shadow,
        sash=None,
        weapon=True,
        pose=_pose_from_action(g),
        phase=_phase(g),
    )


# ---------------------------------------------------------------------------
# HUD
# ---------------------------------------------------------------------------


def _draw_heart(surface: pygame.Surface, cx: int, cy: int, color: RGB) -> None:
    """Corazón de pixel art: dos círculos arriba + triángulo abajo + brillo."""
    # Dos lóbulos superiores
    pygame.draw.circle(surface, color, (cx - 3, cy - 1), 3)
    pygame.draw.circle(surface, color, (cx + 3, cy - 1), 3)
    # Triángulo inferior
    pygame.draw.polygon(
        surface,
        color,
        [(cx - 5, cy), (cx + 5, cy), (cx, cy + 6)],
    )
    # Brillo en lóbulo izquierdo
    pygame.draw.circle(surface, _mix(color, PALETTE.primary, 0.4), (cx - 4, cy - 2), 1)


def _draw_sword_icon(surface: pygame.Surface, cx: int, cy: int) -> None:
    """Icono pequeño de sable empuñado para indicar que lo lleva."""
    pygame.draw.line(surface, PALETTE.blade, (cx - 6, cy), (cx + 4, cy), 2)
    pygame.draw.line(surface, PALETTE.warning, (cx + 4, cy - 3), (cx + 4, cy + 3), 2)
    pygame.draw.circle(surface, PALETTE.warning, (cx + 7, cy), 2)


def _draw_hud(
    surface: pygame.Surface,
    game: Game,
    font: pygame.font.Font,
    *,
    viewport_x: int = 0,
) -> None:
    # Banda superior con degradado tenue para no quedar plana.
    w = surface.get_width()
    pygame.draw.rect(surface, PALETTE.bg, (0, 0, w, LAYOUT.hud_top))
    pygame.draw.rect(surface, _mix(PALETTE.bg, PALETTE.bg_far, 0.5), (0, LAYOUT.hud_top - 4, w, 4))
    # Línea dorada de separación
    pygame.draw.line(
        surface,
        PALETTE.warning,
        (0, LAYOUT.hud_top - 1),
        (w, LAYOUT.hud_top - 1),
        1,
    )
    pygame.draw.line(
        surface,
        _mix(PALETTE.warning, PALETTE.bg, 0.5),
        (0, LAYOUT.hud_top),
        (w, LAYOUT.hud_top),
        1,
    )

    from pop2026.application.campaign import TOTAL_LEVELS
    from pop2026.application.difficulty import ACT_THEMES, act_for_level

    secs = game.time_left // 60
    mm, ss = divmod(secs, 60)
    rooms = total_rooms(game.level.cols)
    room_txt = ""
    if rooms > 1:
        current_room = viewport_x // LAYOUT.cols + 1
        room_txt = f"   SALA {current_room}/{rooms}"
    # Acto + N/100 (limita el cálculo al rango válido por seguridad)
    act_txt = ""
    if 1 <= game.level_index <= TOTAL_LEVELS:
        act = act_for_level(game.level_index)
        act_txt = f"{ACT_THEMES[act].upper()}  ·  "
    title = f"{act_txt}NIVEL {game.level_index}/{TOTAL_LEVELS}   {mm:02d}:{ss:02d}{room_txt}"
    surface.blit(font.render(title, True, PALETTE.primary), (10, 8))

    # Icono de sable (si lo lleva) entre título y corazones.
    icon_x = w - 16 - game.prince.max_hp * 14 - 30
    if game.prince.has_sword:
        _draw_sword_icon(surface, icon_x, 16)

    # Corazones reales en lugar de rombos.
    hp_x = w - 16 - game.prince.max_hp * 14
    for i in range(game.prince.max_hp):
        cx = hp_x + i * 14 + 6
        cy = 14
        if i < game.prince.hp:
            _draw_heart(surface, cx, cy, PALETTE.error)
        else:
            # Corazón vacío (silueta gris).
            _draw_heart(surface, cx, cy, PALETTE.muted)
            pygame.draw.circle(surface, PALETTE.bg, (cx, cy), 2)

    # Mensaje grande de estado
    msg: str | None
    color: RGB = PALETTE.primary
    if game.status is GameStatus.WON:
        msg, color = "VICTORIA", PALETTE.accent
    elif game.status is GameStatus.LOST_DIED:
        msg, color = "HAS MUERTO", PALETTE.error
    elif game.status is GameStatus.LOST_TIMEOUT:
        msg, color = "TIEMPO AGOTADO", PALETTE.warning
    else:
        msg = None
    if msg is not None:
        big = font.render(msg, True, color)
        rect = big.get_rect(center=(surface.get_width() // 2, surface.get_height() // 2))
        # Fondo translúcido tras el mensaje
        bg = pygame.Surface((rect.width + 40, rect.height + 20), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 180))
        surface.blit(bg, bg.get_rect(center=rect.center))
        surface.blit(big, rect)


# ---------------------------------------------------------------------------
# CRT
# ---------------------------------------------------------------------------


def _draw_crt(surface: pygame.Surface) -> None:
    """Overlay de scanlines (firma visual)."""
    w, h = surface.get_size()
    line = pygame.Surface((w, 2), pygame.SRCALPHA)
    line.fill((0, 0, 0, 30))
    for y in range(0, h, 3):
        surface.blit(line, (0, y))
    # Viñeta sutil en bordes
    vignette = pygame.Surface((w, h), pygame.SRCALPHA)
    for i in range(8):
        alpha = 6 - i // 2
        pygame.draw.rect(vignette, (0, 0, 0, alpha), (i, i, w - 2 * i, h - 2 * i), 1)
    surface.blit(vignette, (0, 0))


# ---------------------------------------------------------------------------
# Render principal
# ---------------------------------------------------------------------------


def render(
    surface: pygame.Surface,
    game: Game,
    font: pygame.font.Font,
    *,
    crt: bool = True,
) -> None:
    """Renderiza un frame completo del juego.

    Si el nivel es más ancho que ``LAYOUT.cols``, la cámara opera en
    modo *room-flick*: salta en bloque cuando el príncipe cruza el
    borde de una habitación lógica (homenaje al cambio de pantalla del
    motor original).
    """
    surface.fill(PALETTE.bg)
    viewport_x = viewport_col(game.prince.pos.col, game.level.cols)

    # Pared trasera + banda de techo
    _draw_back_wall(surface)
    _draw_ceiling_strip(surface)

    # Pilares decorativos cada 5 columnas dentro de la habitación visible.
    for local_c in range(0, LAYOUT.cols, 5):
        _draw_pillar(surface, local_c)

    # Tiles visibles (solo las columnas de la habitación actual)
    col_start = viewport_x
    col_end = min(viewport_x + LAYOUT.cols, game.level.cols)
    for r in range(game.level.rows):
        for c in range(col_start, col_end):
            tile = effective_tile(game.level, game.state, Position(r, c))
            x, y = _cell_to_px(c - viewport_x, r)
            if tile is Tile.FLOOR:
                _draw_floor(surface, x, y)
            elif tile is Tile.LOOSE_FLOOR:
                _draw_loose_floor(surface, x, y)
            elif tile is Tile.SPIKES:
                _draw_spikes(surface, x, y)
            elif tile is Tile.GATE:
                pos = Position(r, c)
                _draw_gate(surface, x, y, open_=pos in game.state.open_gates)
            elif tile is Tile.PRESSURE:
                _draw_pressure(surface, x, y)
            elif tile is Tile.POTION_HEAL:
                _draw_potion(surface, x, y, color=PALETTE.success)
            elif tile is Tile.POTION_POISON:
                _draw_potion(surface, x, y, color=PALETTE.error)
            elif tile is Tile.POTION_MAXHP:
                _draw_potion(surface, x, y, color=PALETTE.accent)
            elif tile is Tile.SWORD:
                _draw_sword_pickup(surface, x, y)
            elif tile is Tile.EXIT:
                _draw_exit(surface, x, y)

    # Actores visibles
    for g in game.guards:
        if col_start - 1 <= g.pos.col <= col_end:
            _draw_guard(surface, g, viewport_x=viewport_x)
    _draw_prince(surface, game.prince, viewport_x=viewport_x)

    _draw_hud(surface, game, font, viewport_x=viewport_x)

    if crt:
        _draw_crt(surface)
