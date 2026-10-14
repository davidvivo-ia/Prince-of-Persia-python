"""Vitaminas de presentación: vestuario de guardia por nivel, cámara
lenta y desaturación al morir, ambiente sonoro por tema, vibración."""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from dataclasses import replace

import numpy as np
import pygame
import pytest

from pop2026canon.application.controller import Command
from pop2026canon.application.tick import advance
from pop2026canon.domain.game import new_game
from pop2026canon.domain.levels_canon import CANON_LEVELS
from pop2026canon.infrastructure.audio import AMBIENCE_SECONDS, SR, AudioEngine, ambience_layer
from pop2026canon.infrastructure.settings import Settings
from pop2026canon.presentation.char_atlas import GUARD_WARDROBE, CharPalette, outfit_for, sprite
from pop2026canon.presentation.fx import desaturate
from pop2026canon.presentation.input_device import InputHub
from pop2026canon.presentation.layout import LAYOUT
from pop2026canon.presentation.scene import Scene
from pop2026canon.presentation.themes import AMBIENCES, theme_for


@pytest.fixture(scope="module", autouse=True)
def _pygame() -> None:
    pygame.init()


class TestGuardWardrobe:
    def test_every_level_dresses_its_guards(self) -> None:
        assert set(GUARD_WARDROBE) == set(range(1, 15))
        shirts = {outfit_for(CharPalette.GUARD, n).shirt for n in range(1, 13)}
        assert len(shirts) >= 10, "los guardias de cada nivel se distinguen"

    def test_variant_only_matters_for_guards(self) -> None:
        assert outfit_for(CharPalette.KID, 7) == outfit_for(CharPalette.KID, 1)
        a, _ = sprite(158, CharPalette.KID, 0, 7)
        b, _ = sprite(158, CharPalette.KID, 0, 1)
        assert a is b

    def test_guard_sprites_differ_by_level(self) -> None:
        a, _ = sprite(158, CharPalette.GUARD, 0, 1)
        b, _ = sprite(158, CharPalette.GUARD, 0, 5)
        assert pygame.image.tobytes(a, "RGBA") != pygame.image.tobytes(b, "RGBA")


class TestAmbience:
    @pytest.mark.parametrize("kind", sorted(AMBIENCES))
    def test_layer_is_a_quiet_finite_loop(self, kind: str) -> None:
        x = ambience_layer(kind)
        assert np.all(np.isfinite(x))
        assert abs(len(x) - AMBIENCE_SECONDS * SR) < SR  # ~9 s (menos el cruce)
        assert 0.1 < float(np.max(np.abs(x))) <= 0.5
        # Sin clic en el bucle: el final y el principio se parecen
        assert abs(float(x[0]) - float(x[-1])) < 0.2

    def test_every_theme_has_an_ambience(self) -> None:
        for n in range(1, 15):
            assert theme_for(n).ambience in AMBIENCES

    def test_engine_switches_and_stops(self) -> None:
        eng = AudioEngine()
        eng.ambience("drips")
        eng.ambience("drips")
        eng.ambience("fire")
        eng.set_volumes(0.5, 0.5)
        eng.ambience(None)
        eng.ambience(None)


class TestDeathSlowMotion:
    def test_death_event_sets_slowmo_and_desaturation(self) -> None:
        lv = CANON_LEVELS[0]
        g = new_game(lv)
        sc = Scene(Settings())
        sc.on_level_start(g)
        dying = replace(g, kid=replace(g.kid, hp_curr=0, alive=0))
        sc.on_tick(g, dying)
        assert sc.slowmo > 0
        assert sc.desat_target > 0.5
        for _ in range(60):
            sc.update(1 / 60, dying, 1.0)
        assert sc.desat > 0.4
        sc.on_respawn(g)
        assert sc.slowmo == 0
        assert sc.desat == 0.0

    def test_desaturate_greys_the_world_but_not_the_hud(self) -> None:
        s = pygame.Surface((LAYOUT.window_w, LAYOUT.window_h))
        s.fill((200, 40, 40))
        desaturate(s, 1.0)
        world = s.get_at((100, LAYOUT.hud_top + 100))
        assert abs(world.r - world.g) < 40
        assert s.get_at((100, 10))[:3] == (200, 40, 40)

    def test_app_advances_slower_during_slowmo(self) -> None:
        from pathlib import Path
        from tempfile import TemporaryDirectory

        from pop2026canon.application.session import Session
        from pop2026canon.presentation import app as app_mod

        with TemporaryDirectory() as tmp:
            app = app_mod.GameApp(
                session=Session(level_number=1, levels=CANON_LEVELS),
                campaign_levels=CANON_LEVELS,
                autosave_enabled=False,
                skip_intro=True,
                settings_path=Path(tmp) / "s.json",
                save_path=Path(tmp) / "save.json",
                progress_path=Path(tmp) / "p.json",
            )
            app.input.command = Command  # type: ignore[method-assign]
            app.input.rewind_held = lambda: False  # type: ignore[method-assign]
            app._start_level()
            app.phase = "playing"
            app.scene.slowmo = 40
            before = app.game.tick_count
            for _ in range(40):
                app._playing([])
            assert app.game.tick_count - before <= 5  # a 60 fps serían 8 ticks
            app.game = advance(app.game, Command())


class TestRumble:
    def test_rumble_without_pad_is_harmless(self) -> None:
        hub = InputHub()
        hub.rumble(1.0, 1.0, 100)
        assert not hub.pad_connected
