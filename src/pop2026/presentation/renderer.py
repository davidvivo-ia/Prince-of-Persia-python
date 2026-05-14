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
    """Pinta la pared trasera del calabozo: degradado vertical sutil."""
    w = surface.get_width()
    top_y = LAYOUT.hud_top
    h = LAYOUT.height_px - LAYOUT.hud_top
    # Degradado: arriba bg_far, abajo bg
    steps = 16
    band = max(1, h // steps)
    for i in range(steps):
        t = i / max(1, steps - 1)
        col = tuple(int(PALETTE.bg_far[k] * (1 - t) + PALETTE.bg[k] * t * 0.6) for k in range(3))
        pygame.draw.rect(surface, col, (0, top_y + i * band, w, band + 1))


# ---------------------------------------------------------------------------
# Tiles
# ---------------------------------------------------------------------------


def _draw_floor(surface: pygame.Surface, x: int, y: int) -> None:
    """Dibuja un tile de suelo: el ladrillo llena toda la celda.

    Estilo Apple II HGR: tres cursos horizontales de ladrillo, mortero
    oscuro alternando verticalmente, brillo superior y sombra inferior.
    """
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    top = y  # el ladrillo ocupa la celda entera

    # Cuerpo del ladrillo (toda la celda).
    pygame.draw.rect(surface, PALETTE.brick, (x, top, tw, th))

    # Sombra inferior — efecto de profundidad pegado al borde.
    pygame.draw.rect(surface, PALETTE.brick_dark, (x, y + th - 3, tw, 3))

    # Borde superior iluminado.
    pygame.draw.line(surface, PALETTE.brick_top, (x, top), (x + tw - 1, top), 2)

    # Tres cursos de mortero horizontal.
    course = th // 3
    mortar_y1 = top + course
    mortar_y2 = top + 2 * course
    pygame.draw.line(surface, PALETTE.mortar, (x, mortar_y1), (x + tw, mortar_y1), 1)
    pygame.draw.line(surface, PALETTE.mortar, (x, mortar_y2), (x + tw, mortar_y2), 1)

    # Mortero vertical alternado (ladrillos en aparejo soga).
    offset = (x // tw) % 2  # filas pares vs impares
    half = tw // 2
    # Curso superior (top → mortar_y1): junta en x+half
    pygame.draw.line(surface, PALETTE.mortar, (x + half, top), (x + half, mortar_y1), 1)
    # Curso medio (mortar_y1 → mortar_y2): junta desplazada
    mid_jx = x if offset else x + half
    pygame.draw.line(surface, PALETTE.mortar, (mid_jx, mortar_y1), (mid_jx, mortar_y2), 1)
    # Curso inferior (mortar_y2 → bottom): junta en x+half
    pygame.draw.line(surface, PALETTE.mortar, (x + half, mortar_y2), (x + half, y + th), 1)
    pygame.draw.line(
        surface, PALETTE.mortar, (x + half, mortar_y2), (x + half, top + FLOOR_THICKNESS), 1
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
    """Spikes: triángulos puntiagudos saliendo del suelo."""
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    base_y = y + th - 4
    n_spikes = 5
    spike_w = tw // n_spikes
    for i in range(n_spikes):
        sx = x + i * spike_w
        pygame.draw.polygon(
            surface,
            PALETTE.blade,
            [
                (sx + 1, base_y),
                (sx + spike_w // 2, base_y - 14),
                (sx + spike_w - 1, base_y),
            ],
        )
        # base oscura
    pygame.draw.rect(surface, PALETTE.brick_dark, (x, base_y, tw, 4))


def _draw_gate(surface: pygame.Surface, x: int, y: int, *, open_: bool) -> None:
    """Reja vertical de barrotes. Si está abierta, dibuja media bajada."""
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    bars_top = y + (th // 2 if open_ else 0)
    bars_bot = y + th - FLOOR_THICKNESS
    # Travesaños
    pygame.draw.line(surface, PALETTE.warning, (x, bars_top), (x + tw, bars_top), 2)
    pygame.draw.line(surface, PALETTE.warning, (x, bars_bot), (x + tw, bars_bot), 2)
    # Barrotes verticales
    n = 5
    for i in range(n):
        bx = x + tw * (i + 1) // (n + 1)
        pygame.draw.line(surface, PALETTE.warning, (bx, bars_top), (bx, bars_bot), 2)


def _draw_pressure(surface: pygame.Surface, x: int, y: int) -> None:
    """Placa de presión sobre el suelo."""
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    top = y + th - FLOOR_THICKNESS - 2
    pygame.draw.rect(surface, PALETTE.muted, (x + 4, top, tw - 8, 4))
    pygame.draw.rect(surface, PALETTE.accent, (x + tw // 3, top - 2, tw // 3, 2))


def _draw_potion(surface: pygame.Surface, x: int, y: int, *, color: RGB) -> None:
    """Frasco de poción con cuello y burbuja."""
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    cx = x + tw // 2
    cy = y + th - FLOOR_THICKNESS - 14
    # Cuello
    pygame.draw.rect(surface, PALETTE.primary_dark, (cx - 3, cy - 8, 6, 6))
    # Cuerpo bulboso
    pygame.draw.circle(surface, color, (cx, cy), 8)
    # Brillo
    pygame.draw.circle(surface, PALETTE.primary, (cx - 3, cy - 3), 2)


def _draw_sword_pickup(surface: pygame.Surface, x: int, y: int) -> None:
    """Sable tirado en el suelo, recogible."""
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    base_y = y + th - FLOOR_THICKNESS - 4
    blade_x0 = x + 6
    blade_x1 = x + tw - 10
    pygame.draw.line(surface, PALETTE.blade, (blade_x0, base_y), (blade_x1, base_y), 2)
    # Empuñadura
    pygame.draw.line(surface, PALETTE.warning, (blade_x1, base_y - 2), (blade_x1, base_y + 2), 2)
    pygame.draw.rect(surface, PALETTE.brick_dark, (blade_x1, base_y - 1, 4, 3))
    # Halo violeta tenue
    pygame.draw.circle(surface, PALETTE.accent, ((blade_x0 + blade_x1) // 2, base_y - 2), 1)


def _draw_exit(surface: pygame.Surface, x: int, y: int) -> None:
    """Arco de salida con halo violeta."""
    tw, th = LAYOUT.tile_w, LAYOUT.tile_h
    arch_top = y + 4
    arch_bot = y + th - FLOOR_THICKNESS
    # Arco con borde grueso
    rect = pygame.Rect(x + 4, arch_top, tw - 8, arch_bot - arch_top)
    pygame.draw.rect(surface, PALETTE.accent, rect, 3, border_radius=12)
    # Halo
    inner = rect.inflate(-8, -8)
    pygame.draw.rect(surface, PALETTE.bg_far, inner, border_radius=8)


def _draw_pillar(surface: pygame.Surface, col: int) -> None:
    """Pilar vertical de fondo en una columna concreta."""
    x = col * LAYOUT.tile_w + LAYOUT.tile_w // 2 - 2
    top = LAYOUT.hud_top
    bot = LAYOUT.hud_top + LAYOUT.rows * LAYOUT.tile_h
    pygame.draw.rect(surface, PALETTE.pillar, (x, top, 4, bot - top))


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

    # Si pose == "dead": tumbado horizontal
    if pose == "dead":
        pygame.draw.rect(surface, skin, (feet_x - 12, feet_y - 5, 24, 4))
        pygame.draw.circle(surface, skin, (feet_x - 12 * fdir, feet_y - 3), head_r)
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
    if pose in ("walk", "run"):
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
    if pose in ("walk", "run"):
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
    # Pañuelo / pelo
    pygame.draw.arc(
        surface,
        shadow,
        (head_cx - head_r, head_cy - head_r, head_r * 2, head_r * 2),
        math.pi * (0.0 if fdir > 0 else 1.0),
        math.pi * (1.0 if fdir > 0 else 2.0),
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


def _draw_prince(surface: pygame.Surface, p: Prince, viewport_x: int = 0) -> None:
    feet_x, feet_y = _continuous_feet(p, viewport_x=viewport_x)
    _draw_humanoid(
        surface,
        feet_x,
        feet_y,
        p.facing,
        skin=PALETTE.primary,
        shadow=PALETTE.primary_dark,
        sash=PALETTE.cloth,
        weapon=p.has_sword,
        pose=_pose_from_action(p),
        phase=_phase(p),
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


def _draw_hud(
    surface: pygame.Surface,
    game: Game,
    font: pygame.font.Font,
    *,
    viewport_x: int = 0,
) -> None:
    # Banda superior
    pygame.draw.rect(surface, PALETTE.bg, (0, 0, surface.get_width(), LAYOUT.hud_top))
    pygame.draw.line(
        surface,
        PALETTE.warning,
        (0, LAYOUT.hud_top - 1),
        (surface.get_width(), LAYOUT.hud_top - 1),
        1,
    )

    from pop2026.application.campaign import TOTAL_LEVELS
    from pop2026.application.difficulty import ACT_THEMES, act_for_level

    secs = game.time_left // 60
    mm, ss = divmod(secs, 60)
    sword_txt = "  SABLE" if game.prince.has_sword else ""
    rooms = total_rooms(game.level.cols)
    room_txt = ""
    if rooms > 1:
        current_room = viewport_x // LAYOUT.cols + 1
        room_txt = f"  SALA {current_room}/{rooms}"
    # Acto + N/100 (limita el cálculo al rango válido por seguridad)
    act_txt = ""
    if 1 <= game.level_index <= TOTAL_LEVELS:
        act = act_for_level(game.level_index)
        act_txt = f"{ACT_THEMES[act].upper()}  ·  "
    title = (
        f"{act_txt}NIVEL {game.level_index}/{TOTAL_LEVELS}   {mm:02d}:{ss:02d}{sword_txt}{room_txt}"
    )
    surface.blit(font.render(title, True, PALETTE.primary), (10, 8))

    # Corazones (cada HP es un pequeño rombo rojo)
    hp_x = surface.get_width() - 16 - game.prince.max_hp * 14
    for i in range(game.prince.max_hp):
        cx = hp_x + i * 14 + 6
        cy = 16
        col = PALETTE.error if i < game.prince.hp else PALETTE.muted
        pygame.draw.polygon(surface, col, [(cx, cy - 5), (cx + 5, cy), (cx, cy + 5), (cx - 5, cy)])

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
