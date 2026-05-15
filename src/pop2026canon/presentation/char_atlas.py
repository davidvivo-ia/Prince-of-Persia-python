"""Atlas procedural del kid (y otros chars) — silueta por frame.

Los ~180 frames se agrupan en ~12 *building blocks* visuales:
stand, run cycle, jump, fall, hang, climb, sword, drink, death, etc.
Cada función recibe `(surf, x_px, y_px, facing, palette_kind)`.
"""

from __future__ import annotations

import math
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
ColorSet = tuple[RGB, RGB, RGB | None, RGB | None]


def _colors(kind: CharPalette) -> ColorSet:
    """Devuelve (skin, shadow, sash, weapon)."""
    if kind is CharPalette.KID:
        return (PALETTE.primary, PALETTE.primary_dark, PALETTE.cloth, PALETTE.blade)
    if kind is CharPalette.SHADOW:
        return (PALETTE.shadow_silhouette, PALETTE.bg, PALETTE.accent, PALETTE.blade)
    if kind is CharPalette.GUARD:
        return (PALETTE.guard_skin, PALETTE.guard_armor, None, PALETTE.blade)
    if kind is CharPalette.SKELETON:
        return ((0xCF, 0xCF, 0xDC), (0x5E, 0x4F, 0x7A), None, PALETTE.blade)
    if kind is CharPalette.PRINCESS:
        return (PALETTE.primary, PALETTE.princess_robe, PALETTE.princess_robe, None)
    if kind is CharPalette.VIZIER:
        return (PALETTE.guard_skin, PALETTE.vizier_robe, PALETTE.warning, PALETTE.blade)
    return (PALETTE.muted, PALETTE.bg, None, None)


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------


def _draw_body(
    surf: pygame.Surface,
    feet_x: int,
    feet_y: int,
    facing_sign: int,
    skin: RGB,
    shadow: RGB,
    sash: RGB | None,
    *,
    body_h: int = 56,
    torso_w: int = 14,
    torso_h: int = 22,
    head_r: int = 7,
    arm_angle: float = 0.0,
    leg_spread: int = 8,
    bob: int = 0,
) -> tuple[int, int, int]:
    """Dibuja un cuerpo humanoide básico. Devuelve (head_cx, head_cy, hip_y)."""
    feet_y += bob
    head_cx = feet_x
    head_cy = feet_y - body_h + head_r
    torso_top = head_cy + head_r
    hip_y = torso_top + torso_h
    # Piernas
    foot_l = (head_cx - leg_spread // 2, feet_y)
    foot_r = (head_cx + leg_spread // 2, feet_y)
    pygame.draw.line(surf, skin, (head_cx - 4, hip_y), foot_l, 5)
    pygame.draw.line(surf, skin, (head_cx + 4, hip_y), foot_r, 5)
    pygame.draw.circle(surf, shadow, foot_l, 3)
    pygame.draw.circle(surf, shadow, foot_r, 3)
    # Torso (trapecio)
    pygame.draw.polygon(
        surf,
        skin,
        [
            (head_cx - torso_w // 2, torso_top),
            (head_cx + torso_w // 2, torso_top),
            (head_cx + torso_w // 2 - 2, hip_y),
            (head_cx - torso_w // 2 + 2, hip_y),
        ],
    )
    # Sash
    if sash is not None:
        pygame.draw.rect(surf, sash, (head_cx - torso_w // 2 + 2, hip_y - 5, torso_w - 4, 4))
    # Brazos (animados por arm_angle)
    arm_dx = int(math.cos(arm_angle) * 6)
    arm_dy = int(math.sin(arm_angle) * 4)
    pygame.draw.line(
        surf,
        skin,
        (head_cx - torso_w // 2, torso_top + 4),
        (head_cx - 6 + arm_dx, hip_y - 4 + arm_dy),
        4,
    )
    pygame.draw.line(
        surf,
        skin,
        (head_cx + torso_w // 2, torso_top + 4),
        (head_cx + 6 - arm_dx, hip_y - 4 - arm_dy),
        4,
    )
    # Cabeza
    pygame.draw.circle(surf, skin, (head_cx, head_cy), head_r)
    # Turbante
    if sash is not None:
        pygame.draw.arc(
            surf,
            shadow,
            (head_cx - head_r - 1, head_cy - head_r - 2, (head_r + 1) * 2, (head_r + 2) * 2),
            0,
            math.pi,
            3,
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


def draw_kid_frame(
    surf: pygame.Surface,
    frame_id: int,
    px_x: int,
    px_y: int,
    facing: int,
    palette: CharPalette = CharPalette.KID,
) -> None:
    """Dibuja el frame del char en la posición (px_x, px_y) — pie del char.

    Selección de building block según el rango del frame_id.
    """
    skin, shadow, sash, weapon = _colors(palette)
    fsign = 1 if facing == 0 else -1  # canon: 0 = right, -1 = left

    # Frame ranges canónicos
    if frame_id == 15:
        # Stand
        _draw_body(surf, px_x, px_y, fsign, skin, shadow, sash)
        return

    if 121 <= frame_id <= 132:
        # Run cycle — 12 frames
        phase = (frame_id - 121) / 12.0
        leg_spread = 8 + int(math.sin(phase * math.pi * 2) * 4)
        arm_angle = math.sin(phase * math.pi * 2) * 0.6
        _draw_body(
            surf,
            px_x,
            px_y,
            fsign,
            skin,
            shadow,
            sash,
            leg_spread=leg_spread,
            arm_angle=arm_angle,
        )
        return

    if 7 <= frame_id <= 11 or 50 <= frame_id <= 52:
        # Startrun / stoprun — body ligeramente inclinado
        _draw_body(surf, px_x, px_y, fsign, skin, shadow, sash, leg_spread=6)
        return

    if 16 <= frame_id <= 27 or 34 <= frame_id <= 44:
        # Standing jump / run jump — silueta agrupada
        bob = -8 if 18 <= frame_id <= 22 else 0
        _draw_body(
            surf,
            px_x,
            px_y,
            fsign,
            skin,
            shadow,
            sash,
            body_h=52,
            leg_spread=4,
            bob=bob,
        )
        return

    if 45 <= frame_id <= 49:
        # Turn — body más estrecho
        _draw_body(surf, px_x, px_y, fsign, skin, shadow, sash, torso_w=10)
        return

    if 67 <= frame_id <= 99 or 135 <= frame_id <= 149:
        # Hang / climb — body con brazos arriba
        _draw_body(
            surf,
            px_x,
            px_y,
            fsign,
            skin,
            shadow,
            sash,
            arm_angle=-math.pi / 2,
            body_h=52,
        )
        return

    if 102 <= frame_id <= 108:
        # Fall / land
        bob = 0 if frame_id < 106 else 4
        _draw_body(
            surf,
            px_x,
            px_y,
            fsign,
            skin,
            shadow,
            sash,
            body_h=50,
            leg_spread=12,
            bob=bob,
        )
        return

    if 110 <= frame_id <= 119:
        # Crouch / standup
        _draw_body(
            surf,
            px_x,
            px_y,
            fsign,
            skin,
            shadow,
            sash,
            body_h=36,
            torso_h=14,
            leg_spread=12,
        )
        return

    if 150 <= frame_id <= 167:
        # Sword combat: engarde / strike
        head_cx, _, hip_y = _draw_body(surf, px_x, px_y, fsign, skin, shadow, sash, leg_spread=10)
        if weapon is not None:
            hand_y = hip_y - 12
            if 165 <= frame_id <= 167:
                # Strike window — sable totalmente extendido
                _draw_sword(surf, head_cx + fsign * 14, hand_y, fsign, weapon)
            else:
                _draw_sword(surf, head_cx + fsign * 8, hand_y, fsign, weapon)
        return

    if 161 <= frame_id <= 164:
        # Block — sable vertical delante
        head_cx, _, hip_y = _draw_body(surf, px_x, px_y, fsign, skin, shadow, sash)
        if weapon is not None:
            pygame.draw.line(
                surf, weapon, (head_cx + fsign * 8, hip_y - 30), (head_cx + fsign * 8, hip_y + 4), 3
            )
        return

    if frame_id == 177:
        # Spiked — slumped sobre pinchos
        pygame.draw.line(surf, skin, (px_x - 10, px_y - 4), (px_x + 10, px_y - 4), 6)
        pygame.draw.circle(surf, skin, (px_x - fsign * 12, px_y - 6), 5)
        return

    if frame_id == 178:
        # Chomped
        pygame.draw.rect(surf, skin, (px_x - 8, px_y - 16, 16, 16))
        return

    if 179 <= frame_id <= 185:
        # Death — gradual collapse
        progress = (frame_id - 179) / 6.0
        angle = progress * (math.pi / 2)
        sa = math.sin(angle)
        ca = math.cos(angle)
        body_dx = int(20 * sa) * fsign
        body_dy = -int(40 * ca) - 4
        pygame.draw.line(surf, skin, (px_x, px_y - 2), (px_x - body_dx // 2, px_y + body_dy + 4), 6)
        pygame.draw.circle(surf, skin, (px_x + body_dx, px_y + body_dy), 7)
        if progress > 0.7:
            pool_w = int(28 * (progress - 0.7) / 0.3)
            pool = pygame.Surface((pool_w + 4, 4), pygame.SRCALPHA)
            pygame.draw.ellipse(pool, (*PALETTE.error, 100), pool.get_rect())
            surf.blit(pool, (px_x - pool_w // 2 - 2, px_y - 1))
        return

    if 191 <= frame_id <= 205:
        # Drinking potion
        head_cx, head_cy, _ = _draw_body(
            surf, px_x, px_y, fsign, skin, shadow, sash, arm_angle=math.pi / 4
        )
        pygame.draw.circle(surf, PALETTE.success, (head_cx + fsign * 5, head_cy + 2), 4)
        return

    if 207 <= frame_id <= 210:
        # Draw sword animation
        head_cx, _, hip_y = _draw_body(surf, px_x, px_y, fsign, skin, shadow, sash)
        if weapon is not None:
            pygame.draw.line(
                surf,
                weapon,
                (head_cx + fsign * 4, hip_y - 6),
                (head_cx + fsign * 12, hip_y - 22),
                3,
            )
        return

    # Fallback: stand
    _draw_body(surf, px_x, px_y, fsign, skin, shadow, sash)
