"""Tests del poster canon — render sin crash + cast por nivel."""

from __future__ import annotations

import os

import pygame
import pytest

from pop2026canon.domain.levels_canon import CANON_LEVELS
from pop2026canon.presentation.poster import (
    LEVEL_CASTS,
    PosterCast,
    cast_for_level,
    draw_poster,
)
from pop2026canon.presentation.screens.cutscene import draw_level_card
from pop2026canon.presentation.screens.title import INTRO_DURATION
from pop2026canon.presentation.screens.title import draw as draw_title

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


@pytest.fixture(scope="module", autouse=True)
def _pygame_init() -> None:
    pygame.init()
    pygame.font.init()


class TestPosterCast:
    def test_default_includes_main_trio(self) -> None:
        c = PosterCast()
        assert c.princess
        assert c.vizier
        assert c.prince
        assert not c.guard

    def test_every_level_has_cast(self) -> None:
        for lvl in CANON_LEVELS:
            assert lvl.number in LEVEL_CASTS

    def test_l3_no_vizier_just_prince(self) -> None:
        c = cast_for_level(3)
        assert c.prince
        assert not c.vizier
        assert not c.princess

    def test_l12_finale_includes_vizier_and_princess(self) -> None:
        c = cast_for_level(12)
        assert c.prince
        assert c.vizier
        assert c.princess

    def test_l13_no_vizier_after_defeat(self) -> None:
        c = cast_for_level(13)
        assert not c.vizier
        assert c.princess

    def test_l14_ending_no_vizier(self) -> None:
        c = cast_for_level(14)
        assert not c.vizier
        assert c.princess


class TestPosterRendering:
    def test_draw_poster_runs(self) -> None:
        surf = pygame.Surface((480, 320))
        font = pygame.font.Font(None, 32)
        draw_poster(surf, font, t=1.0)
        # No crash, surface poblada (no totalmente bg)
        assert surf.get_at((0, 0)) != surf.get_at((surf.get_width() // 2, 50))

    def test_draw_poster_with_each_level_cast(self) -> None:
        surf = pygame.Surface((480, 320))
        font = pygame.font.Font(None, 32)
        for n in range(1, 15):
            draw_poster(surf, font, t=2.0, cast=cast_for_level(n))

    def test_curtains_closed_to_open(self) -> None:
        """Renderizar con cortinas cerradas vs. abiertas produce imágenes
        diferentes en la zona lateral donde las cortinas avanzan."""
        surf_closed = pygame.Surface((480, 320))
        surf_open = pygame.Surface((480, 320))
        font = pygame.font.Font(None, 32)
        draw_poster(surf_closed, font, curtain_openness=0.0, show_title=False)
        draw_poster(surf_open, font, curtain_openness=1.0, show_title=False)
        # Muestrea zona lateral (cortinas más anchas con openness=0).
        y = surf_closed.get_height() // 3
        diff = sum(
            1
            for x in range(60, surf_closed.get_width() - 60, 6)
            if surf_closed.get_at((x, y)) != surf_open.get_at((x, y))
        )
        assert diff > 0, "Cortinas no producen cambio entre closed y open"


class TestTitleScreen:
    def test_title_intro_renders_at_multiple_times(self) -> None:
        surf = pygame.Surface((480, 320))
        font_big = pygame.font.Font(None, 48)
        font_small = pygame.font.Font(None, 18)
        for t in (0.0, INTRO_DURATION / 2, INTRO_DURATION, INTRO_DURATION + 1.0):
            draw_title(surf, font_big, font_small, t)


class TestLevelCard:
    def test_all_levels_render_card(self) -> None:
        surf = pygame.Surface((480, 320))
        font_big = pygame.font.Font(None, 48)
        font_small = pygame.font.Font(None, 18)
        for lvl in CANON_LEVELS:
            draw_level_card(surf, lvl, font_big, font_small, t=1.0)
