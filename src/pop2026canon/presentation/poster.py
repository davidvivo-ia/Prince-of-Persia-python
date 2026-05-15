"""Poster procedural inspirado en la portada de POP1 (1989).

Cinco capas en composición:

1. **Cielo nocturno** azul profundo con halo lunar.
2. **Luna llena** crema en el centro-izquierda.
3. **Palacio** de cúpulas y minaretes en silueta pálida sobre el cielo.
4. **Cortinas rojas** carmesí enmarcando la escena por los dos lados,
   con pliegues para dar volumen.
5. **Siluetas** opcionales de los personajes (Jaffar, princesa, prince)
   en primer plano según el nivel.

Todo dibujo procedural — sin assets binarios, sin reproducir el arte
del original (clean-room tributo).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pygame

from pop2026canon.presentation.char_atlas import CharPalette, draw_kid_frame
from pop2026canon.presentation.palette import PALETTE

RGB = tuple[int, int, int]


@dataclass(frozen=True, slots=True)
class PosterCast:
    """Qué personajes incluir en el primer plano del poster."""

    princess: bool = True
    """Silueta de la princesa a la izquierda."""

    vizier: bool = True
    """Silueta amenazante de Jaffar arriba-derecha."""

    prince: bool = True
    """Silueta del prince al centro-bajo."""

    guard: bool = False
    """Guard auxiliar a la derecha."""


# ---------------------------------------------------------------------------
# Capas
# ---------------------------------------------------------------------------


def _draw_sky(surf: pygame.Surface, rect: pygame.Rect, t: float) -> None:
    """Cielo nocturno con halo lunar suave. ``t`` controla parpadeo de
    estrellas para hacerlo dinámico."""
    # Degradado vertical del azul nocturno
    steps = 16
    band_h = max(1, rect.height // steps)
    for i in range(steps):
        k = i / max(1, steps - 1)
        col = (
            int(PALETTE.poster_sky[0] * (1 - k * 0.3)),
            int(PALETTE.poster_sky[1] * (1 - k * 0.3)),
            int(PALETTE.poster_sky[2] * (1 - k * 0.3)),
        )
        pygame.draw.rect(surf, col, (rect.x, rect.y + i * band_h, rect.width, band_h + 1))

    # Estrellas con titileo basado en t
    for n in range(40):
        # Distribución pseudoaleatoria determinista
        sx = rect.x + (n * 41) % rect.width
        sy = rect.y + (n * 23) % (rect.height * 2 // 3)
        phase = (n * 7) % 13
        bright = 0.4 + 0.6 * abs(math.sin(t * 1.4 + phase))
        c = int(220 * bright)
        surf.set_at((sx, sy), (c, c, c))


def _draw_moon(surf: pygame.Surface, cx: int, cy: int, radius: int) -> None:
    """Luna llena con halo concéntrico."""
    # Halo (cuatro círculos cada vez más transparentes)
    for i, alpha in enumerate((30, 60, 90)):
        halo = pygame.Surface((radius * 6, radius * 6), pygame.SRCALPHA)
        pygame.draw.circle(
            halo,
            (*PALETTE.poster_sky_light, alpha),
            (radius * 3, radius * 3),
            radius * 2 - i * 8,
        )
        surf.blit(halo, (cx - radius * 3, cy - radius * 3))
    # Luna
    pygame.draw.circle(surf, PALETTE.poster_moon, (cx, cy), radius)
    # Sombra de cráter sutil (no realista, evocador)
    pygame.draw.circle(
        surf,
        (
            int(PALETTE.poster_moon[0] * 0.85),
            int(PALETTE.poster_moon[1] * 0.85),
            int(PALETTE.poster_moon[2] * 0.85),
        ),
        (cx + 2, cy - 2),
        radius - 4,
    )


def _draw_palace(surf: pygame.Surface, rect: pygame.Rect) -> None:
    """Silueta de palacio con varios minaretes + cúpula central."""
    # Base — bloque del palacio
    base_y = rect.y + rect.height * 3 // 5
    base_h = rect.height - (base_y - rect.y)
    base_rect = pygame.Rect(rect.x + 8, base_y, rect.width - 16, base_h)
    pygame.draw.rect(surf, PALETTE.poster_palace_dark, base_rect)

    # Minaretes (4 — dos a cada lado)
    minaret_w = max(8, rect.width // 16)
    minaret_xs = (
        rect.x + 12,
        rect.x + rect.width // 3 - minaret_w,
        rect.x + rect.width * 2 // 3,
        rect.x + rect.width - 12 - minaret_w,
    )
    for mx in minaret_xs:
        mh = rect.height // 2
        mtop = base_y - mh
        pygame.draw.rect(surf, PALETTE.poster_palace, (mx, mtop, minaret_w, mh))
        # Cúpula bulbosa
        pygame.draw.ellipse(
            surf,
            PALETTE.poster_palace,
            (mx - 2, mtop - minaret_w, minaret_w + 4, minaret_w * 2),
        )
        # Aguja
        pygame.draw.line(
            surf,
            PALETTE.poster_gold,
            (mx + minaret_w // 2, mtop - minaret_w + 2),
            (mx + minaret_w // 2, mtop - minaret_w - 8),
            2,
        )

    # Cúpula central grande
    dome_w = rect.width // 3
    dome_x = rect.x + rect.width // 2 - dome_w // 2
    dome_top = base_y - dome_w // 2
    pygame.draw.ellipse(surf, PALETTE.poster_palace, (dome_x, dome_top - 10, dome_w, dome_w))
    pygame.draw.ellipse(
        surf,
        PALETTE.poster_palace_dark,
        (dome_x, dome_top - 10, dome_w, dome_w),
        2,
    )
    # Aguja central
    pygame.draw.line(
        surf,
        PALETTE.poster_gold,
        (rect.x + rect.width // 2, dome_top - 8),
        (rect.x + rect.width // 2, dome_top - 22),
        3,
    )

    # Ventanas iluminadas (puntos cálidos)
    for n in range(8):
        wx = base_rect.x + 12 + (n * (base_rect.width - 24) // 7)
        wy = base_rect.y + 14
        pygame.draw.rect(surf, PALETTE.poster_gold, (wx, wy, 3, 6))


def _draw_curtains(surf: pygame.Surface, rect: pygame.Rect, openness: float = 1.0) -> None:
    """Cortinas rojas a izquierda y derecha. ``openness`` 0..1 controla
    cuánto se separan del centro (1 = totalmente abiertas)."""
    w = rect.width
    h = rect.height
    side_w = int(w * 0.18 * (2 - openness))  # más anchas si cerradas
    # Cortina izquierda
    left_pts = [
        (rect.x, rect.y),
        (rect.x + side_w, rect.y),
        (rect.x + side_w - 8, rect.y + h),
        (rect.x, rect.y + h),
    ]
    pygame.draw.polygon(surf, PALETTE.poster_curtain, left_pts)
    # Pliegues verticales
    for i in range(4):
        px = rect.x + (i + 1) * side_w // 5
        pygame.draw.line(
            surf,
            PALETTE.poster_curtain_dark,
            (px, rect.y),
            (px - 4, rect.y + h),
            2,
        )
    # Cortina derecha
    right_pts = [
        (rect.x + w - side_w, rect.y),
        (rect.x + w, rect.y),
        (rect.x + w, rect.y + h),
        (rect.x + w - side_w + 8, rect.y + h),
    ]
    pygame.draw.polygon(surf, PALETTE.poster_curtain, right_pts)
    for i in range(4):
        px = rect.x + w - side_w + (i + 1) * side_w // 5
        pygame.draw.line(
            surf,
            PALETTE.poster_curtain_dark,
            (px, rect.y),
            (px + 4, rect.y + h),
            2,
        )
    # Cordones de oro
    pygame.draw.line(
        surf,
        PALETTE.poster_gold,
        (rect.x + side_w - 6, rect.y + h // 2),
        (rect.x + side_w + 12, rect.y + h // 2 + 14),
        2,
    )
    pygame.draw.line(
        surf,
        PALETTE.poster_gold,
        (rect.x + w - side_w + 6, rect.y + h // 2),
        (rect.x + w - side_w - 12, rect.y + h // 2 + 14),
        2,
    )


def _draw_title(
    surf: pygame.Surface, rect: pygame.Rect, font_big: pygame.font.Font, t: float
) -> None:
    """Logo PRINCE OF PERSIA en oro con sombra dorada."""
    pulse = 0.85 + 0.15 * abs(math.sin(t * 1.2))
    main = (
        int(PALETTE.poster_gold[0] * pulse),
        int(PALETTE.poster_gold[1] * pulse),
        int(PALETTE.poster_gold[2] * pulse),
    )
    # Sombra
    shadow = font_big.render("PRINCE OF PERSIA", True, PALETTE.poster_gold_dark)
    title = font_big.render("PRINCE OF PERSIA", True, main)
    cx = rect.x + rect.width // 2
    surf.blit(shadow, shadow.get_rect(center=(cx + 3, rect.y + rect.height // 8 + 3)))
    surf.blit(title, title.get_rect(center=(cx, rect.y + rect.height // 8)))


def _draw_silhouettes(surf: pygame.Surface, rect: pygame.Rect, cast: PosterCast) -> None:
    """Personajes en primer plano usando el atlas del kid con paletas."""
    base_y = rect.y + rect.height - 16

    # Jaffar arriba-derecha en grande
    if cast.vizier:
        draw_kid_frame(
            surf,
            frame_id=15,
            px_x=rect.x + rect.width * 3 // 4,
            px_y=rect.y + rect.height * 3 // 5,
            facing=-1,
            palette=CharPalette.VIZIER,
        )
        # "Aura" amenazante: rectángulo translúcido alrededor
        aura = pygame.Surface((90, 110), pygame.SRCALPHA)
        pygame.draw.ellipse(aura, (*PALETTE.error, 40), aura.get_rect())
        surf.blit(
            aura,
            (rect.x + rect.width * 3 // 4 - 45, rect.y + rect.height * 3 // 5 - 95),
        )

    # Princesa abajo-izquierda
    if cast.princess:
        draw_kid_frame(
            surf,
            frame_id=15,
            px_x=rect.x + rect.width // 5,
            px_y=base_y,
            facing=0,
            palette=CharPalette.PRINCESS,
        )

    # Prince en el centro-bajo, frame de strike para dinamismo
    if cast.prince:
        draw_kid_frame(
            surf,
            frame_id=166,
            px_x=rect.x + rect.width // 2,
            px_y=base_y,
            facing=0,
            palette=CharPalette.KID,
        )

    # Guard a la derecha (opcional)
    if cast.guard:
        draw_kid_frame(
            surf,
            frame_id=15,
            px_x=rect.x + rect.width * 9 // 10,
            px_y=base_y,
            facing=-1,
            palette=CharPalette.GUARD,
        )


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------


def draw_poster(
    surf: pygame.Surface,
    font_big: pygame.font.Font,
    *,
    t: float = 0.0,
    cast: PosterCast | None = None,
    curtain_openness: float = 1.0,
    show_title: bool = True,
) -> None:
    """Pinta el poster canon sobre toda la superficie.

    Args:
        surf: superficie destino (full screen).
        font_big: fuente grande para el título PRINCE OF PERSIA.
        t: tiempo en segundos (para titileo de estrellas y pulso oro).
        cast: qué personajes incluir. ``None`` → cast por defecto
            (princess+vizier+prince, sin guard).
        curtain_openness: 0 cortinas cerradas, 1 abiertas. Útil para
            animar la apertura como cinemática inicial.
        show_title: si dibujar el logo PRINCE OF PERSIA.
    """
    if cast is None:
        cast = PosterCast()

    w, h = surf.get_size()
    full = pygame.Rect(0, 0, w, h)

    # Capa 1: cielo
    inner = pygame.Rect(int(w * 0.1), 0, int(w * 0.8), h)
    _draw_sky(surf, inner, t)
    # Capa 2: luna
    _draw_moon(surf, inner.x + inner.width // 4, inner.y + h // 4, max(24, h // 14))
    # Capa 3: palacio
    palace_rect = pygame.Rect(inner.x, inner.y + h // 5, inner.width, h * 2 // 3)
    _draw_palace(surf, palace_rect)
    # Capa 4: cortinas
    _draw_curtains(surf, full, openness=curtain_openness)
    # Capa 5: siluetas
    _draw_silhouettes(surf, full, cast)
    # Capa 6: título
    if show_title:
        _draw_title(surf, full, font_big, t)


# ---------------------------------------------------------------------------
# Cast por nivel — qué personajes evocar en el level card de cada nivel
# ---------------------------------------------------------------------------

LEVEL_CASTS: dict[int, PosterCast] = {
    1: PosterCast(princess=False, vizier=True, prince=True, guard=True),
    2: PosterCast(princess=False, vizier=True, prince=True, guard=True),
    3: PosterCast(princess=False, vizier=False, prince=True, guard=False),  # skeleton-only
    4: PosterCast(princess=False, vizier=True, prince=True, guard=False),  # mirror/shadow
    5: PosterCast(princess=False, vizier=True, prince=True, guard=False),
    6: PosterCast(princess=False, vizier=True, prince=True, guard=False),
    7: PosterCast(princess=True, vizier=True, prince=True, guard=True),
    8: PosterCast(princess=True, vizier=True, prince=True, guard=False),
    9: PosterCast(princess=False, vizier=True, prince=True, guard=False),
    10: PosterCast(princess=True, vizier=True, prince=True, guard=True),
    11: PosterCast(princess=True, vizier=True, prince=True, guard=True),
    12: PosterCast(princess=True, vizier=True, prince=True, guard=False),  # vizier finale
    13: PosterCast(princess=True, vizier=False, prince=True, guard=False),  # vizier muerto
    14: PosterCast(princess=True, vizier=False, prince=True, guard=False),  # reunion
}
"""Cast del poster para cada nivel. La presencia/ausencia de personajes
refleja la situación narrativa de ese nivel."""


def cast_for_level(level_number: int) -> PosterCast:
    """Devuelve el cast del poster para ``level_number`` (1..14)."""
    return LEVEL_CASTS.get(level_number, PosterCast())
