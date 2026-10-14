"""Identidad visual de cada nivel: tema propio, cada sala se pinta bien
(ni negra ni quemada, con los suelos legibles), decoración y partículas
ambientales del tema."""

from __future__ import annotations

import os
from dataclasses import replace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from pop2026canon.domain.game import new_game
from pop2026canon.domain.levels_canon import CANON_LEVELS
from pop2026canon.infrastructure.settings import Settings
from pop2026canon.presentation.backdrop import decor_lights, decor_spots
from pop2026canon.presentation.fx import Particles
from pop2026canon.presentation.layout import LAYOUT
from pop2026canon.presentation.scene import Scene
from pop2026canon.presentation.themes import (
    DECOR_KINDS,
    MASONRY,
    PALACE_LEVELS,
    PARTICLE_KINDS,
    SKIES,
    THEMES,
    theme_for,
)


@pytest.fixture(scope="module", autouse=True)
def _pygame() -> None:
    pygame.init()


def _lum(c: pygame.Color) -> float:
    return 0.299 * c.r + 0.587 * c.g + 0.114 * c.b


class TestThemes:
    def test_every_level_has_its_own_theme(self) -> None:
        keys = {theme_for(n).key for n in range(1, 15)}
        assert len(keys) == 14

    @pytest.mark.parametrize("n", range(1, 15))
    def test_theme_is_well_formed(self, n: int) -> None:
        th = theme_for(n)
        assert th.palace == (n in PALACE_LEVELS)
        assert set(th.particles) <= PARTICLE_KINDS
        assert set(th.decor) <= DECOR_KINDS
        assert th.masonry in MASONRY
        assert th.sky in SKIES
        assert th.particles, "cada nivel tiene vida ambiental"
        assert th.decor, "cada nivel tiene decoración propia"

    def test_consecutive_levels_look_different(self) -> None:
        for a, b in zip(range(1, 14), range(2, 15), strict=True):
            ta, tb = THEMES[a], THEMES[b]
            color = sum(abs(x - y) for x, y in zip(ta.stone, tb.stone, strict=True))
            assert color > 15 or ta.decor != tb.decor or ta.masonry != tb.masonry, (a, b)

    @pytest.mark.parametrize("n", range(1, 15))
    def test_decor_is_deterministic_and_on_canvas(self, n: int) -> None:
        th = theme_for(n)
        for name in th.decor:
            spots = decor_spots(3, th.key, name)
            assert spots == decor_spots(3, th.key, name)
            for x, row in spots:
                assert 0 <= x <= LAYOUT.window_w
                assert 0 <= row <= 2
        for x, y, r, _c in decor_lights(3, th.key):
            assert 0 <= x <= LAYOUT.window_w
            assert 0 <= y <= LAYOUT.room_h
            assert r > 0

    def test_light_decor_emits_light(self) -> None:
        lit = {
            n for n in range(1, 15) if any(decor_lights(r, theme_for(n).key) for r in range(1, 25))
        }
        for n in range(1, 15):
            if {"candles", "crystals", "windows"} & set(theme_for(n).decor):
                assert n in lit, f"L{n}: su decoración debería dar luz"


@pytest.mark.parametrize("level", CANON_LEVELS, ids=lambda lv: f"L{lv.number}")
def test_every_room_renders_readable(level) -> None:  # type: ignore[no-untyped-def]
    """Cada sala del nivel: ni negra ni quemada, y el borde de cada losa
    se distingue de la pared de detrás."""
    canvas = pygame.Surface((LAYOUT.window_w, LAYOUT.window_h))
    base = new_game(level, has_sword=level.number > 1)
    for room in level.rooms:
        g = replace(base, kid=replace(base.kid, room=room.id))
        sc = Scene(Settings())
        sc.on_level_start(g)
        sc.hud.banner_t = 0.0
        sc.draw(canvas, g, None, 1.0, 1.0, sand=None, rewinding=False, show_time=False)
        world = canvas.subsurface((0, LAYOUT.hud_top, LAYOUT.window_w, LAYOUT.room_h))
        small = pygame.transform.smoothscale(world, (64, 38))
        mean = sum(_lum(small.get_at((x, y))) for x in range(64) for y in range(38)) / (64 * 38)
        assert 12 < mean < 150, f"L{level.number} sala {room.id}: luminancia media {mean:.0f}"
        # Contraste losa/pared: mediana sobre las celdas de suelo liso de
        # cada fila (una vela o una antorcha concreta no cuenta).
        for row in range(3):
            diffs = []
            for col in range(10):
                if room.tile_at(col, row)[0] != 1:
                    continue
                if row and room.tile_at(col, row - 1)[0] == 20:
                    continue
                x = col * LAYOUT.tile_w + LAYOUT.tile_w // 4
                face_y = LAYOUT.hud_top + (row + 1) * LAYOUT.tile_h - LAYOUT.floor_face
                top_y = face_y - LAYOUT.floor_top
                lip = _band(
                    canvas, pygame.Rect(x, top_y + 2, LAYOUT.tile_w // 2, LAYOUT.floor_top - 2)
                )
                wall = _band(
                    canvas, pygame.Rect(x, top_y - LAYOUT.tile_h // 3, LAYOUT.tile_w // 2, 20)
                )
                diffs.append(lip - wall)
            if len(diffs) < 3:
                continue
            diffs.sort()
            median = diffs[len(diffs) // 2]
            assert median > 6, (
                f"L{level.number} sala {room.id} fila {row}: las losas no se distinguen "
                f"de la pared (contraste mediano {median:.0f})"
            )


def _band(surf: pygame.Surface, rect: pygame.Rect) -> float:
    vals = [
        _lum(surf.get_at((x, y)))
        for x in range(rect.left, rect.right, 4)
        for y in range(rect.top, rect.bottom, 2)
    ]
    return sum(vals) / max(1, len(vals))


@pytest.mark.parametrize("n", range(1, 15))
def test_ambient_particles_follow_the_theme(n: int) -> None:
    level = CANON_LEVELS[n - 1]
    g = new_game(level)
    parts = Particles(seed=n)
    shapes: set[str] = set()
    for i in range(360):
        parts.ambient(g, 1 / 60, i / 60)
        parts.update(1 / 60)
        shapes |= {p.shape for p in parts.items}
    th = theme_for(n)
    assert parts.items, f"L{n}: sin partículas ambientales"
    if "petals" in th.particles:
        assert "petal" in shapes
    if "drips" in th.particles:
        assert "streak" in shapes
