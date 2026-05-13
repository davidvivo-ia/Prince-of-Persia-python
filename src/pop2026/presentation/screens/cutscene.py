"""Cinemáticas mínimas: pantallas de texto narrativo con dibujo procedural.

Tres viñetas: ``intro`` antes del primer nivel, ``mid`` antes del nivel
6 y ``final`` justo antes de la victoria global. Cada viñeta es una
pantalla estática que se cierra al pulsar una tecla o tras 6 segundos.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pygame

from pop2026.presentation.theme import LAYOUT, PALETTE


@dataclass(frozen=True, slots=True)
class Scene:
    """Definición declarativa de una cinemática."""

    title: str
    body: tuple[str, ...]
    glyph: str  # "prisoner", "stairs", "throne"
    color: tuple[int, int, int]


SCENES: dict[str, Scene] = {
    "intro": Scene(
        title="MEDIANOCHE EN LA MAZMORRA",
        body=(
            "Una hora hasta el alba.",
            "Una hora hasta la sentencia.",
            "Despiertas. Hay un pasillo. Un sable lejano.",
            "Y, en algún piso de arriba, una corona que no debería ser suya.",
        ),
        glyph="prisoner",
        color=PALETTE.cloth,
    ),
    "mid": Scene(
        title="LAS ESCALERAS",
        body=(
            "Atrás quedaron los suelos sueltos.",
            "Las puertas se cierran solas.",
            "Cada paso es una decisión que no admite reverso.",
        ),
        glyph="stairs",
        color=PALETTE.warning,
    ),
    "final": Scene(
        title="EL VISIR",
        body=(
            "El reloj marca un minuto.",
            "Una hoja contra otra hoja, y nada más.",
            "Es ahora.",
        ),
        glyph="throne",
        color=PALETTE.accent,
    ),
}
"""Catálogo de cinemáticas. Diseño narrativo propio."""


def _draw_glyph(surface: pygame.Surface, name: str, color: tuple[int, int, int]) -> None:
    """Dibujo procedural simple, una silueta por glyph."""
    w, h = surface.get_size()
    cx, cy = w // 2, h // 2 - 90
    if name == "prisoner":
        # Silueta encogida con cadena.
        pygame.draw.circle(surface, color, (cx, cy - 6), 9)
        pygame.draw.rect(surface, color, (cx - 12, cy + 4, 24, 16))
        pygame.draw.line(surface, PALETTE.muted, (cx - 18, cy + 10), (cx - 30, cy + 26), 2)
        pygame.draw.line(surface, PALETTE.muted, (cx + 18, cy + 10), (cx + 30, cy + 26), 2)
    elif name == "stairs":
        for i in range(5):
            step = i * 8
            pygame.draw.rect(surface, color, (cx - 30 + step, cy + step, 22, 8))
    elif name == "throne":
        # Trono con figura.
        pygame.draw.rect(surface, color, (cx - 22, cy - 14, 44, 30), 2)
        pygame.draw.rect(surface, color, (cx - 28, cy + 14, 56, 6))
        pygame.draw.circle(surface, color, (cx, cy - 6), 8)


def draw(
    surface: pygame.Surface,
    scene_name: str,
    *,
    font_big: pygame.font.Font,
    font: pygame.font.Font,
    t: float,
) -> None:
    """Renderiza una cinemática completa."""
    scene = SCENES[scene_name]
    surface.fill(PALETTE.bg)

    # Fondo: degradado vertical sutil
    w, h = surface.get_size()
    for i in range(h):
        ratio = i / h
        col = tuple(int(PALETTE.bg_far[k] * (1 - ratio) + PALETTE.bg[k] * ratio) for k in range(3))
        pygame.draw.line(surface, col, (0, i), (w, i))

    # Glyph
    _draw_glyph(surface, scene.glyph, scene.color)

    # Título centrado
    title_img = font_big.render(scene.title, True, scene.color)
    surface.blit(title_img, title_img.get_rect(center=(w // 2, h // 2 - 20)))

    # Cuerpo de texto
    for i, line in enumerate(scene.body):
        line_img = font.render(line, True, PALETTE.primary)
        surface.blit(line_img, line_img.get_rect(center=(w // 2, h // 2 + 24 + i * 24)))

    # Pulsa una tecla (parpadeo)
    alpha = int((math.sin(t * 3.0) + 1.0) * 0.5 * 200) + 30
    msg = font.render("Pulsa una tecla para continuar", True, PALETTE.muted)
    msg.set_alpha(alpha)
    surface.blit(msg, msg.get_rect(center=(w // 2, h - 32)))

    _ = LAYOUT  # silencia "no usado"
