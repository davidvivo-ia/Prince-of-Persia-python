"""Smoke tests de la capa de presentación (headless).

Verifican que el renderer y el CLI puedan ejecutarse sin display real
(``SDL_VIDEODRIVER=dummy``).
"""

from __future__ import annotations

import os

import pytest

# Marca todo el módulo con dummy driver
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


def test_renderer_can_draw_a_frame() -> None:
    pygame = pytest.importorskip("pygame")
    pygame.init()
    try:
        from pop2026.domain.game import new_game
        from pop2026.infrastructure.levels import load_builtin
        from pop2026.presentation import renderer
        from pop2026.presentation.theme import LAYOUT

        level = load_builtin("01_dungeon")
        game = new_game(level)
        screen = pygame.Surface((LAYOUT.width_px, LAYOUT.height_px))
        font = pygame.font.Font(None, 22)
        renderer.render(screen, game, font, crt=True)
        # debería haber píxeles no-negros (al menos el fondo bg, no negro puro)
        r, g, b, *_ = screen.get_at((0, 0))
        assert (r, g, b) != (0, 0, 0)
    finally:
        pygame.quit()


def test_cli_demo_headless_returns_zero() -> None:
    from typer.testing import CliRunner

    from pop2026.presentation.cli import app

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["--demo", "--seed", "42", "--frames", "200", "--headless"],
    )
    assert result.exit_code == 0, result.output
    assert "status=" in result.output


def test_cli_version_flag() -> None:
    from typer.testing import CliRunner

    from pop2026.presentation.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "pop2026" in result.output
