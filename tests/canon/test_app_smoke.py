"""El bucle con ventana (GameApp) de punta a punta, con driver de vídeo
y audio *dummy*: título → menú → nivel → pausa → opciones → juego."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from pop2026canon.application.controller import Command
from pop2026canon.application.session import Session
from pop2026canon.domain.levels_canon import CANON_LEVELS
from pop2026canon.infrastructure.settings import load


@pytest.fixture
def app_factory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    pygame.init()
    from pop2026canon.presentation import app as app_mod
    from pop2026canon.presentation.input_device import InputHub

    monkeypatch.setattr(InputHub, "command", lambda self: Command(right=True))
    monkeypatch.setattr(InputHub, "rewind_held", lambda self: False)

    def make(script: dict[int, list[int]], frames: int) -> app_mod.GameApp:
        phases: list[str] = []

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


def test_full_menu_flow(app_factory, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    k = pygame
    script = {
        3: [k.K_RETURN],  # salta la intro
        10: [k.K_RETURN],  # Nueva partida → intro
        15: [k.K_RETURN],  # salta la intro → card
        20: [k.K_RETURN],  # card → jugar
        120: [k.K_ESCAPE],  # pausa
        125: [k.K_DOWN, k.K_DOWN, k.K_DOWN],  # Opciones
        128: [k.K_RETURN],
        132: [k.K_DOWN] * 11,
        135: [k.K_RETURN],  # Filtro CRT → SÍ
        140: [k.K_BACKSPACE],  # volver (guarda ajustes)
        145: [k.K_UP, k.K_UP, k.K_UP],
        148: [k.K_RETURN],  # Reanudar
    }
    app = app_factory(script, 220)
    assert app.run() == 0
    seen = list(dict.fromkeys(app.phases))
    assert seen[:5] == ["title", "intro", "card", "playing", "paused"]
    assert app.phases[-1] == "playing"
    assert load(tmp_path / "settings.json").crt_filter is True
    assert (tmp_path / "save.json").exists(), "autosave al empezar el nivel"
    assert app.game.tick_count > 10, "la lógica avanzó"
