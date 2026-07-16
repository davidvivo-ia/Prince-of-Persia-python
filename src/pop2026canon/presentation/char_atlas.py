"""Atlas procedural del kid (y otros chars) — silueta por frame.

Los ~180 frames se agrupan en ~12 *building blocks* visuales:
stand, run cycle, jump, fall, hang, climb, sword, drink, death, etc.
Cada función recibe `(surf, x_px, y_px, facing, palette_kind)`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import IntEnum

import pygame

from pop2026canon.presentation.palette import PALETTE


class CharPalette(IntEnum):
    """Variantes de paleta por tipo de char."""

    KID = 0
    SHADOW = 1
    GUARD = 2
    SKELETON = 3
    PRINCESS = 4
    VIZIER = 5
    MOUSE = 6


RGB = tuple[int, int, int]


@dataclass(frozen=True, slots=True)
class CharColors:
    """Paleta completa para dibujar un char humanoide.

    Cada char tiene piel, pelo, túnica, cinturón, pantalones, botas y
    arma. Los building blocks usan estos roles para que cualquier char
    quede coherente.
    """

    skin: RGB
    hair: RGB
    tunic: RGB
    tunic_shade: RGB
    belt: RGB
    pants: RGB
    boots: RGB
    weapon: RGB | None = None


def _colors(kind: CharPalette) -> CharColors:
    if kind is CharPalette.KID:
        return CharColors(
            skin=PALETTE.kid_skin,
            hair=PALETTE.kid_hair,
            tunic=PALETTE.kid_tunic,
            tunic_shade=PALETTE.kid_tunic_dark,
            belt=PALETTE.kid_belt,
            pants=PALETTE.kid_tunic,
            boots=PALETTE.kid_boot,
            weapon=PALETTE.blade,
        )
    if kind is CharPalette.SHADOW:
        sil = PALETTE.shadow_silhouette
        return CharColors(
            skin=sil,
            hair=PALETTE.bg,
            tunic=sil,
            tunic_shade=PALETTE.bg,
            belt=PALETTE.accent,
            pants=sil,
            boots=PALETTE.bg,
            weapon=PALETTE.blade,
        )
    if kind is CharPalette.GUARD:
        return CharColors(
            skin=PALETTE.guard_skin,
            hair=(0x20, 0x18, 0x18),
            tunic=PALETTE.guard_armor,
            tunic_shade=(0x20, 0x20, 0x30),
            belt=(0x60, 0x40, 0x18),
            pants=PALETTE.guard_armor,
            boots=(0x20, 0x18, 0x10),
            weapon=PALETTE.blade,
        )
    if kind is CharPalette.SKELETON:
        bone = (0xCF, 0xCF, 0xDC)
        bone_dark = (0x5E, 0x4F, 0x7A)
        return CharColors(
            skin=bone,
            hair=bone_dark,
            tunic=bone_dark,
            tunic_shade=PALETTE.bg,
            belt=bone_dark,
            pants=bone_dark,
            boots=PALETTE.bg,
            weapon=PALETTE.blade,
        )
    if kind is CharPalette.PRINCESS:
        return CharColors(
            skin=PALETTE.kid_skin,
            hair=(0x40, 0x20, 0x60),
            tunic=PALETTE.princess_robe,
            tunic_shade=(0x80, 0x28, 0x60),
            belt=PALETTE.warning,
            pants=PALETTE.princess_robe,
            boots=(0x40, 0x20, 0x40),
            weapon=None,
        )
    if kind is CharPalette.VIZIER:
        return CharColors(
            skin=PALETTE.guard_skin,
            hair=(0x10, 0x08, 0x08),
            tunic=PALETTE.vizier_robe,
            tunic_shade=(0x10, 0x08, 0x10),
            belt=PALETTE.warning,
            pants=PALETTE.vizier_robe,
            boots=(0x10, 0x08, 0x08),
            weapon=PALETTE.blade,
        )
    # Mouse / fallback
    return CharColors(
        skin=PALETTE.muted,
        hair=PALETTE.bg,
        tunic=PALETTE.muted,
        tunic_shade=PALETTE.bg,
        belt=PALETTE.bg,
        pants=PALETTE.muted,
        boots=PALETTE.bg,
        weapon=None,
    )


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------


def _draw_body(
    surf: pygame.Surface,
    feet_x: int,
    feet_y: int,
    facing_sign: int,
    colors: CharColors,
    *,
    body_h: int = 56,
    torso_w: int = 16,
    torso_h: int = 22,
    head_r: int = 7,
    arm_angle: float = 0.0,
    leg_spread: int = 8,
    bob: int = 0,
) -> tuple[int, int, int]:
    """Dibuja un cuerpo humanoide con ropa canónica.

    Capas (de atrás a delante): pantalones → botas → torso/túnica →
    cinturón → brazos con mangas → cabeza con pelo.
    Devuelve ``(head_cx, head_cy, hip_y)``.
    """
    feet_y += bob
    head_cx = feet_x
    head_cy = feet_y - body_h + head_r
    torso_top = head_cy + head_r
    hip_y = torso_top + torso_h
    half_w = torso_w // 2

    # ---- Piernas (pantalones blancos) + botas
    foot_l = (head_cx - max(2, leg_spread // 2), feet_y)
    foot_r = (head_cx + max(2, leg_spread // 2), feet_y)
    # Muslo+pierna como rectángulos rellenos para mayor cuerpo
    pygame.draw.line(surf, colors.pants, (head_cx - 4, hip_y), foot_l, 7)
    pygame.draw.line(surf, colors.pants, (head_cx + 4, hip_y), foot_r, 7)
    # Sombra interior del pantalón (línea fina al borde)
    pygame.draw.line(surf, colors.tunic_shade, (head_cx - 4, hip_y), foot_l, 1)
    pygame.draw.line(surf, colors.tunic_shade, (head_cx + 4, hip_y), foot_r, 1)
    # Botas
    pygame.draw.ellipse(surf, colors.boots, (foot_l[0] - 4, feet_y - 3, 9, 6))
    pygame.draw.ellipse(surf, colors.boots, (foot_r[0] - 5, feet_y - 3, 9, 6))

    # ---- Torso (túnica) — trapecio relleno + outline
    torso_pts = [
        (head_cx - half_w, torso_top),
        (head_cx + half_w, torso_top),
        (head_cx + half_w - 2, hip_y),
        (head_cx - half_w + 2, hip_y),
    ]
    pygame.draw.polygon(surf, colors.tunic, torso_pts)
    pygame.draw.polygon(surf, colors.tunic_shade, torso_pts, 1)
    # Pliegue central de la túnica
    pygame.draw.line(
        surf,
        colors.tunic_shade,
        (head_cx, torso_top + 2),
        (head_cx, hip_y - 2),
        1,
    )

    # ---- Cinturón rojo (siempre visible — clave canon)
    belt_y = hip_y - 4
    belt_rect = pygame.Rect(head_cx - half_w + 1, belt_y, torso_w - 2, 4)
    pygame.draw.rect(surf, colors.belt, belt_rect)
    pygame.draw.rect(surf, colors.tunic_shade, belt_rect, 1)

    # ---- Brazos con manga blanca + mano piel
    # arm_angle = 0 → brazos colgando; pi/4 → enfrente; -pi/2 → arriba.
    shoulder_l = (head_cx - half_w + 1, torso_top + 3)
    shoulder_r = (head_cx + half_w - 1, torso_top + 3)
    arm_len = 16
    elbow_dx = int(math.cos(arm_angle) * arm_len * 0.55)
    elbow_dy = int(math.sin(arm_angle) * arm_len * 0.55) + 6
    # Brazo derecho (delante) — empuja hacia facing
    elbow_r = (shoulder_r[0] + elbow_dx * facing_sign, shoulder_r[1] + elbow_dy)
    hand_r = (
        elbow_r[0] + int(math.cos(arm_angle + 0.3) * 7) * facing_sign,
        elbow_r[1] + int(math.sin(arm_angle + 0.3) * 7) + 4,
    )
    pygame.draw.line(surf, colors.tunic, shoulder_r, elbow_r, 5)
    pygame.draw.line(surf, colors.skin, elbow_r, hand_r, 4)
    pygame.draw.circle(surf, colors.skin, hand_r, 2)
    # Brazo trasero — más sombreado, ángulo simétrico
    elbow_l = (shoulder_l[0] - elbow_dx * facing_sign, shoulder_l[1] + elbow_dy)
    hand_l = (
        elbow_l[0] - int(math.cos(arm_angle + 0.3) * 6) * facing_sign,
        elbow_l[1] + int(math.sin(arm_angle + 0.3) * 6) + 4,
    )
    pygame.draw.line(surf, colors.tunic_shade, shoulder_l, elbow_l, 5)
    pygame.draw.line(surf, colors.skin, elbow_l, hand_l, 3)
    pygame.draw.circle(surf, colors.skin, hand_l, 2)

    # ---- Cabeza (piel) + pelo
    pygame.draw.circle(surf, colors.skin, (head_cx, head_cy), head_r)
    # Cuello
    pygame.draw.rect(surf, colors.skin, (head_cx - 2, head_cy + head_r - 2, 4, 4))
    # Casquete del pelo: arco superior y mechón hacia atrás
    hair_rect = (
        head_cx - head_r - 1,
        head_cy - head_r - 1,
        (head_r + 1) * 2,
        (head_r + 1) * 2,
    )
    pygame.draw.arc(surf, colors.hair, hair_rect, math.pi * 0.15, math.pi * 0.95, 3)
    # Mechón detrás (hacia el lado contrario al facing)
    pygame.draw.line(
        surf,
        colors.hair,
        (head_cx - facing_sign * (head_r - 1), head_cy - head_r + 1),
        (head_cx - facing_sign * (head_r + 2), head_cy + 2),
        2,
    )
    # Ojo
    pygame.draw.circle(surf, PALETTE.bg, (head_cx + facing_sign * 3, head_cy - 1), 1)
    return head_cx, head_cy, hip_y


def _draw_sword(
    surf: pygame.Surface, hand_x: int, hand_y: int, facing_sign: int, weapon: RGB
) -> None:
    """Sable horizontal extendido hacia facing."""
    blade_end = hand_x + facing_sign * 22
    pygame.draw.line(surf, weapon, (hand_x, hand_y), (blade_end, hand_y - 1), 3)
    pygame.draw.line(surf, PALETTE.warning, (hand_x, hand_y - 3), (hand_x, hand_y + 3), 2)


# ---------------------------------------------------------------------------
# Frame → drawer dispatch
# ---------------------------------------------------------------------------


CHAR_SCALE: float = 1.5
"""Factor de escala del char en pantalla. El cuerpo base mide ~60 px;
con 1.5x el kid ocupa ~90 px de los 126 de un piso (proporción POP1)."""

_CANVAS = 160
_CANVAS_FEET = (80, 130)


def draw_kid_frame(
    surf: pygame.Surface,
    frame_id: int,
    px_x: int,
    px_y: int,
    facing: int,
    palette: CharPalette = CharPalette.KID,
) -> None:
    """Dibuja el frame del char en la posición (px_x, px_y) — pie del char.

    Renderiza el cuerpo en un lienzo temporal y lo escala ``CHAR_SCALE``
    para que la proporción char/sala sea la del original.
    """
    canvas = pygame.Surface((_CANVAS, _CANVAS), pygame.SRCALPHA)
    _draw_kid_frame_raw(canvas, frame_id, _CANVAS_FEET[0], _CANVAS_FEET[1], facing, palette)
    scaled_size = int(_CANVAS * CHAR_SCALE)
    scaled = pygame.transform.scale(canvas, (scaled_size, scaled_size))
    fx = int(_CANVAS_FEET[0] * CHAR_SCALE)
    fy = int(_CANVAS_FEET[1] * CHAR_SCALE)
    surf.blit(scaled, (px_x - fx, px_y - fy))


def _draw_kid_frame_raw(
    surf: pygame.Surface,
    frame_id: int,
    px_x: int,
    px_y: int,
    facing: int,
    palette: CharPalette = CharPalette.KID,
) -> None:
    """Dibuja el frame a escala 1:1 del atlas (uso interno)."""
    colors = _colors(palette)
    fsign = 1 if facing == 0 else -1  # canon: 0 = right, -1 = left

    # Frame ranges canónicos
    if frame_id == 15:
        _draw_body(surf, px_x, px_y, fsign, colors)
        return

    if 121 <= frame_id <= 132:
        # Run cycle — 12 frames
        phase = (frame_id - 121) / 12.0
        leg_spread = 10 + int(math.sin(phase * math.pi * 2) * 5)
        arm_angle = math.sin(phase * math.pi * 2) * 0.6
        _draw_body(
            surf,
            px_x,
            px_y,
            fsign,
            colors,
            leg_spread=leg_spread,
            arm_angle=arm_angle,
        )
        return

    if 7 <= frame_id <= 11 or 50 <= frame_id <= 52:
        _draw_body(surf, px_x, px_y, fsign, colors, leg_spread=6)
        return

    if 16 <= frame_id <= 27 or 34 <= frame_id <= 44:
        # Standing jump / run jump
        bob = -8 if 18 <= frame_id <= 22 else 0
        _draw_body(
            surf,
            px_x,
            px_y,
            fsign,
            colors,
            body_h=52,
            leg_spread=4,
            bob=bob,
            arm_angle=0.4,
        )
        return

    if 45 <= frame_id <= 49:
        _draw_body(surf, px_x, px_y, fsign, colors, torso_w=12)
        return

    if 67 <= frame_id <= 99 or 135 <= frame_id <= 149:
        _draw_body(surf, px_x, px_y, fsign, colors, arm_angle=-math.pi / 2, body_h=52)
        return

    if 102 <= frame_id <= 108:
        bob = 0 if frame_id < 106 else 4
        _draw_body(
            surf,
            px_x,
            px_y,
            fsign,
            colors,
            body_h=50,
            leg_spread=12,
            bob=bob,
        )
        return

    if 110 <= frame_id <= 119:
        _draw_body(
            surf,
            px_x,
            px_y,
            fsign,
            colors,
            body_h=36,
            torso_h=14,
            leg_spread=12,
        )
        return

    if 150 <= frame_id <= 167:
        # Sword combat: engarde / strike
        head_cx, _, hip_y = _draw_body(
            surf, px_x, px_y, fsign, colors, leg_spread=10, arm_angle=0.4
        )
        if colors.weapon is not None:
            hand_y = hip_y - 12
            if 165 <= frame_id <= 167:
                _draw_sword(surf, head_cx + fsign * 14, hand_y, fsign, colors.weapon)
            else:
                _draw_sword(surf, head_cx + fsign * 8, hand_y, fsign, colors.weapon)
        return

    if 161 <= frame_id <= 164:
        # Block — sable vertical delante
        head_cx, _, hip_y = _draw_body(surf, px_x, px_y, fsign, colors)
        if colors.weapon is not None:
            pygame.draw.line(
                surf,
                colors.weapon,
                (head_cx + fsign * 8, hip_y - 30),
                (head_cx + fsign * 8, hip_y + 4),
                3,
            )
        return

    if frame_id == 177:
        # Spiked — slumped sobre pinchos
        pygame.draw.line(surf, colors.tunic, (px_x - 10, px_y - 4), (px_x + 10, px_y - 4), 6)
        pygame.draw.circle(surf, colors.skin, (px_x - fsign * 12, px_y - 6), 5)
        return

    if frame_id == 178:
        # Chomped
        pygame.draw.rect(surf, colors.tunic, (px_x - 8, px_y - 16, 16, 16))
        return

    if 179 <= frame_id <= 185:
        progress = (frame_id - 179) / 6.0
        angle = progress * (math.pi / 2)
        sa = math.sin(angle)
        ca = math.cos(angle)
        body_dx = int(20 * sa) * fsign
        body_dy = -int(40 * ca) - 4
        pygame.draw.line(
            surf, colors.tunic, (px_x, px_y - 2), (px_x - body_dx // 2, px_y + body_dy + 4), 6
        )
        pygame.draw.circle(surf, colors.skin, (px_x + body_dx, px_y + body_dy), 7)
        if progress > 0.7:
            pool_w = int(28 * (progress - 0.7) / 0.3)
            pool = pygame.Surface((pool_w + 4, 4), pygame.SRCALPHA)
            pygame.draw.ellipse(pool, (*PALETTE.error, 100), pool.get_rect())
            surf.blit(pool, (px_x - pool_w // 2 - 2, px_y - 1))
        return

    if 191 <= frame_id <= 205:
        head_cx, head_cy, _ = _draw_body(surf, px_x, px_y, fsign, colors, arm_angle=math.pi / 4)
        pygame.draw.circle(surf, PALETTE.success, (head_cx + fsign * 5, head_cy + 2), 4)
        return

    if 207 <= frame_id <= 210:
        head_cx, _, hip_y = _draw_body(surf, px_x, px_y, fsign, colors)
        if colors.weapon is not None:
            pygame.draw.line(
                surf,
                colors.weapon,
                (head_cx + fsign * 4, hip_y - 6),
                (head_cx + fsign * 12, hip_y - 22),
                3,
            )
        return

    _draw_body(surf, px_x, px_y, fsign, colors)
