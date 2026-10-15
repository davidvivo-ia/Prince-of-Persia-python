"""Menús: navegación pura y dibujo sin errores."""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from pop2026canon.infrastructure.settings import Settings
from pop2026canon.presentation import fonts
from pop2026canon.presentation.input_device import UiAction
from pop2026canon.presentation.menu import (
    draw_controls,
    draw_menu,
    main_menu,
    options_menu,
    pause_menu,
)


class TestNavigation:
    def test_wraps_around(self) -> None:
        m = main_menu(has_save=False)
        s = Settings()
        m.handle(UiAction.UP, s)
        assert m.items[m.index].key == "quit"
        m.handle(UiAction.DOWN, s)
        assert m.index == 0

    def test_continue_only_with_save(self) -> None:
        assert main_menu(has_save=True).items[0].key == "continue"
        assert all(i.key != "continue" for i in main_menu(has_save=False).items)

    def test_confirm_returns_key(self) -> None:
        m = pause_menu()
        assert m.handle(UiAction.CONFIRM, Settings())[1] == "resume"
        assert m.handle(UiAction.PAUSE, Settings())[1] == "resume", "Esc/Start reanuda"

    def test_main_menu_cannot_be_backed_out(self) -> None:
        assert main_menu(False).handle(UiAction.BACK, Settings())[1] is None


class TestOptions:
    def _select(self, key: str):  # type: ignore[no-untyped-def]
        m = options_menu()
        m.index = next(i for i, it in enumerate(m.items) if it.key == key)
        return m

    def test_toggle(self) -> None:
        m = self._select("crt_filter")
        s, _ = m.handle(UiAction.CONFIRM, Settings())
        assert s.crt_filter is True
        s, _ = m.handle(UiAction.LEFT, s)
        assert s.crt_filter is False

    def test_slider_clamped(self) -> None:
        m = self._select("music_volume")
        s = Settings().with_(music_volume=0.95)
        s, _ = m.handle(UiAction.RIGHT, s)
        assert s.music_volume == 1.0
        s, _ = m.handle(UiAction.RIGHT, s)
        assert s.music_volume == 1.0
        for _ in range(15):
            s, _ = m.handle(UiAction.LEFT, s)
        assert s.music_volume == 0.0

    def test_choice_cycles(self) -> None:
        m = self._select("game_mode")
        s, _ = m.handle(UiAction.RIGHT, Settings())
        assert s.game_mode == "classic"
        s, _ = m.handle(UiAction.RIGHT, s)
        assert s.game_mode == "modern"
        assert m.value_text(m.items[m.index], s) == "MODERNO"

    def test_every_option_is_a_real_setting(self) -> None:
        s = Settings()
        for item in options_menu().items:
            if item.kind != "action":
                assert hasattr(s, item.key), item.key


class TestDrawing:
    def test_menus_draw(self) -> None:
        pygame.init()
        surf = pygame.Surface((640, 426))
        for m in (main_menu(True), pause_menu(), options_menu()):
            for i in range(len(m.items)):
                m.index = i
                draw_menu(surf, m, Settings(), 0.5)
        draw_controls(surf, 0.0, pad=True)

    def test_fonts_never_render_missing_glyph_boxes(self) -> None:
        pygame.init()
        text = fonts.safe("↑ salta · ← →")
        if not fonts.has_symbols():
            assert "↑" not in text
        assert fonts.render(text, 20, (255, 255, 255)).get_width() > 0
