"""Idioma español/inglés y cinemáticas de intro y final."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from pop2026canon.application.controller import Command
from pop2026canon.application.hints import HINTS
from pop2026canon.application.session import Session
from pop2026canon.domain.levels_canon import CANON_LEVELS
from pop2026canon.infrastructure.settings import Settings
from pop2026canon.presentation import i18n
from pop2026canon.presentation.i18n import EN, set_language, tr
from pop2026canon.presentation.layout import LAYOUT
from pop2026canon.presentation.menu import CONTROLS, main_menu, options_menu, pause_menu
from pop2026canon.presentation.screens import cinematic
from pop2026canon.presentation.screens.cutscene import LEVEL_TAGLINES
from pop2026canon.presentation.screens.levels import MEDAL_NAMES
from pop2026canon.presentation.themes import theme_for


@pytest.fixture(autouse=True)
def _spanish() -> None:
    set_language("es")
    yield  # type: ignore[misc]
    set_language("es")


class TestI18n:
    def test_spanish_is_identity(self) -> None:
        assert tr("Nueva partida") == "Nueva partida"
        assert i18n.language() == "es"

    def test_english_translates_and_falls_back(self) -> None:
        set_language("en")
        assert tr("Nueva partida") == "New game"
        assert tr("cadena sin traducir") == "cadena sin traducir"

    def test_unknown_language_falls_back_to_spanish(self) -> None:
        set_language("klingon")
        assert i18n.language() == "es"

    def test_every_ui_string_has_english(self) -> None:
        strings: set[str] = set()
        for menu in (main_menu(True, True), pause_menu(), options_menu()):
            if menu.title:
                strings.add(menu.title)
            for item in menu.items:
                strings.add(item.label)
                if item.hint:
                    strings.add(item.hint)
                for value, label in item.choices:
                    if not isinstance(value, int):
                        strings.add(label)
        for row in CONTROLS:
            strings.update(row)
        for hint in HINTS.values():
            strings.add(hint.text)
            strings.add(hint.pad_text)
        strings.update(LEVEL_TAGLINES.values())
        strings.update(MEDAL_NAMES.values())
        strings.update(theme_for(n).title for n in range(1, 15))
        strings.update(text for _, _, text in cinematic.INTRO_LINES + cinematic.ENDING_LINES)
        # Las entradas puramente simbólicas (teclas) no necesitan traducción.
        symbolic = {s for s in strings if not any(c.isalpha() for c in s) or s == "—"}
        missing = sorted(s for s in strings - symbolic - set(EN) if s not in EN)
        allowed = {"↑  /  W", "↓  /  S", "← →  /  A D", "ESC · M", "TAB", "SHIFT", "A", "↑"}
        allowed |= {"A  (Cruz)", "B  (Círculo)", "X  (Cuadrado)", "RB / RT", "LB / LT"}
        allowed |= {"Start · Back", "F11 · Alt+Enter", "Cruceta / stick", "ESPACIO / J"}
        allowed |= {"↑ + dirección", "A + dirección", "R  (mantener)"}
        assert [m for m in missing if m not in allowed] == []

    def test_language_option_in_menu(self) -> None:
        menu = options_menu()
        item = next(i for i in menu.items if i.key == "language")
        assert [v for v, _ in item.choices] == ["es", "en"]
        s = Settings()
        assert menu.value_text(item, s) == "ESPAÑOL"
        assert menu.value_text(item, s.with_(language="en")) == "ENGLISH"

    def test_toggle_labels_follow_language(self) -> None:
        menu = options_menu()
        item = next(i for i in menu.items if i.key == "crt_filter")
        assert menu.value_text(item, Settings()) == "NO"
        set_language("en")
        assert menu.value_text(item, Settings()) == "OFF"


@pytest.fixture(scope="module")
def canvas() -> pygame.Surface:
    pygame.init()
    return pygame.Surface((LAYOUT.window_w, LAYOUT.window_h))


def _mean(surf: pygame.Surface) -> float:
    small = pygame.transform.smoothscale(surf, (32, 21))
    px_ = pygame.surfarray.pixels3d(small)
    return float(px_.mean())


class TestCinematics:
    @pytest.mark.parametrize("t", [0.0, 2.0, 6.9, 7.5, 10.0, 15.9, 16.5, 19.0, 23.9])
    def test_intro_draws_every_scene(self, canvas: pygame.Surface, t: float) -> None:
        cinematic.draw_intro(canvas, t)
        if 0.5 < t < 23.5:
            assert _mean(canvas) > 6, "la escena no está en negro"

    def test_intro_fades_in_from_black(self, canvas: pygame.Surface) -> None:
        cinematic.draw_intro(canvas, 0.0)
        assert _mean(canvas) < 12, "sólo el color de fondo y las bandas"

    @pytest.mark.parametrize("t", [0.5, 2.0, 4.0, 7.0, 11.0, 12.0])
    def test_ending_draws(self, canvas: pygame.Surface, t: float) -> None:
        cinematic.draw_ending(canvas, t)
        assert _mean(canvas) > 6

    def test_hourglass_sand_states(self, canvas: pygame.Surface) -> None:
        for sand in (0.0, 0.5, 1.0):
            canvas.fill((0, 0, 0))
            cinematic.draw_hourglass(canvas, 600, 500, 120, sand, 0.0)
            assert _mean(canvas) > 0

    def test_subtitles_are_translated(self, canvas: pygame.Surface) -> None:
        """La intro en inglés pinta píxeles distintos a la intro en español
        (los subtítulos cambian)."""
        cinematic.draw_intro(canvas, 2.0)
        es = pygame.surfarray.array3d(canvas).copy()
        set_language("en")
        cinematic.draw_intro(canvas, 2.0)
        en = pygame.surfarray.array3d(canvas)
        assert (es != en).any()


@pytest.fixture
def app_factory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    pygame.init()
    from pop2026canon.presentation import app as app_mod
    from pop2026canon.presentation.input_device import InputHub

    monkeypatch.setattr(InputHub, "command", lambda self: Command())
    monkeypatch.setattr(InputHub, "rewind_held", lambda self: False)

    def make(script: dict[int, list[int]], frames: int, settings: str = "") -> app_mod.GameApp:
        phases: list[str] = []
        if settings:
            (tmp_path / "settings.json").write_text(settings, encoding="utf-8")

        class Spy(app_mod.GameApp):
            def _draw(self) -> None:
                super()._draw()
                f = len(phases)
                phases.append(self.phase)
                for k in script.get(f, []):
                    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0))

        spy = Spy(
            session=Session(level_number=1, levels=CANON_LEVELS),
            campaign_levels=CANON_LEVELS,
            max_frames=frames,
            settings_path=tmp_path / "settings.json",
            save_path=tmp_path / "save.json",
            progress_path=tmp_path / "progress.json",
        )
        spy.phases = phases  # type: ignore[attr-defined]
        return spy

    yield make
    pygame.quit()


class TestAppFlow:
    def test_new_game_plays_intro_then_card(self, app_factory) -> None:  # type: ignore[no-untyped-def]
        k = pygame
        script = {
            3: [k.K_RETURN],  # salta la apertura del título
            10: [k.K_RETURN],  # Nueva partida → intro
            30: [k.K_RETURN],  # salta la intro → card
            40: [k.K_RETURN],  # card → jugar
        }
        app = app_factory(script, 60)
        assert app.run() == 0
        seen = list(dict.fromkeys(app.phases))
        assert seen[:4] == ["title", "intro", "card", "playing"]

    def test_intro_ends_on_its_own(self, app_factory, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        k = pygame
        app = app_factory({3: [k.K_RETURN], 10: [k.K_RETURN]}, 40)
        # Con la intro ya "agotada", el siguiente frame pasa a la card.
        orig = app._intro

        def fast(actions):  # type: ignore[no-untyped-def]
            app.phase_t0 = app.now - cinematic.INTRO_DURATION
            orig(actions)

        monkeypatch.setattr(app, "_intro", fast)
        app.run()
        assert "card" in app.phases
        assert app.phases.index("card") > app.phases.index("intro")

    def test_language_setting_applies_on_start(self, app_factory) -> None:  # type: ignore[no-untyped-def]
        app = app_factory({}, 2, settings='{"language": "en"}')
        app.run()
        assert i18n.language() == "en"
        assert tr("Niveles") == "Levels"

    def test_reunion_leads_to_victory(self, app_factory) -> None:  # type: ignore[no-untyped-def]
        from pop2026canon.presentation.input_device import UiAction

        app = app_factory({}, 1)
        app.run()
        app._goto("reunion")
        app._reunion([UiAction.CONFIRM])
        assert app.phase == "reunion", "no se puede saltar en el primer segundo"
        app.phase_t0 = app.now - 2.0
        app._reunion([UiAction.CONFIRM])
        assert app.phase == "victory"
