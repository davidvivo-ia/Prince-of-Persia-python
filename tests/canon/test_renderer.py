"""Tests smoke del renderer canon — pintar no debe crashear."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from pop2026canon.domain.game import new_game
from pop2026canon.domain.levels_canon import CANON_LEVELS


@pytest.fixture(scope="module", autouse=True)
def _pygame_init() -> None:  # type: ignore[misc]
    pygame.init()
    yield
    pygame.quit()


@pytest.fixture
def screen() -> pygame.Surface:
    from pop2026canon.presentation.layout import LAYOUT

    return pygame.Surface((LAYOUT.window_w, LAYOUT.window_h))


@pytest.fixture
def font() -> pygame.font.Font:
    return pygame.font.Font(None, 22)


class TestRendererSmoke:
    def test_render_all_14_levels(self, screen: pygame.Surface, font: pygame.font.Font) -> None:
        """Cada nivel se puede renderizar sin excepciones."""
        from pop2026canon.presentation.renderer import render

        for lvl in CANON_LEVELS:
            game = new_game(lvl)
            render(screen, game, font)  # no debe lanzar

    def test_tile_atlas_dispatches_all_31_types(self, screen: pygame.Surface) -> None:
        """Cada tile value (0..30) dispatcha sin excepción."""
        from pop2026canon.presentation.tile_atlas import draw_tile

        for tile_val in range(31):
            draw_tile(screen, tile_val, 0, 0, modifier=0)
            draw_tile(screen, tile_val, 0, 0, modifier=3)


class TestCharAtlas:
    def test_kid_frame_draws(self, screen: pygame.Surface) -> None:
        from pop2026canon.presentation.char_atlas import CharPalette, draw_kid_frame

        # Frames clave de cada rango
        for frame_id in (
            15,
            121,
            132,
            16,
            43,
            50,
            67,
            91,
            102,
            110,
            150,
            167,
            177,
            179,
            185,
            191,
            207,
        ):
            draw_kid_frame(screen, frame_id, 100, 200, 0, CharPalette.KID)
            draw_kid_frame(screen, frame_id, 100, 200, -1, CharPalette.KID)

    def test_each_palette_kind(self, screen: pygame.Surface) -> None:
        from pop2026canon.presentation.char_atlas import CharPalette, draw_kid_frame

        for kind in CharPalette:
            draw_kid_frame(screen, 15, 100, 200, 0, kind)
