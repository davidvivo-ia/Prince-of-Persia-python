"""Entry point del motor canon `pop2026canon`.

Comandos:
- ``pop2026canon`` o ``python -m pop2026canon``: lanza el juego desde L1
- ``--level N``: empieza en el nivel N (1..14)
- ``--headless``: ejecuta sin ventana (para tests)
- ``--preview SLUG``: genera PNG de una sala como preview
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import typer

from pop2026canon import __version__
from pop2026canon.application.controller import Command
from pop2026canon.application.tick import advance
from pop2026canon.domain.game import new_game
from pop2026canon.domain.levels_canon import CANON_LEVELS

app = typer.Typer(
    name="pop2026canon",
    help="Prince of Persia (1989), clon canon Python 2026.",
    no_args_is_help=False,
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"pop2026canon {__version__}")
        raise typer.Exit(0)


@app.callback(invoke_without_command=True)
def _main(
    ctx: typer.Context,
    level: int = typer.Option(1, "--level", min=1, max=14, help="Nivel inicial (1-14)."),
    headless: bool = typer.Option(False, "--headless", help="Sin ventana ni audio (CI)."),
    max_frames: int = typer.Option(0, "--frames", help="Límite de frames (0 = sin límite)."),
    version: bool = typer.Option(
        False, "--version", callback=_version_callback, is_eager=True, help="Imprime versión."
    ),
) -> None:
    """Lanza el juego desde el nivel indicado."""
    if ctx.invoked_subcommand is not None:
        return
    _ = version
    if headless:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    code = _run(level, headless=headless, max_frames=max_frames)
    sys.exit(code)


def _run(level_number: int, *, headless: bool, max_frames: int) -> int:
    """Loop principal del juego."""
    import pygame

    from pop2026canon.presentation import input_device, renderer
    from pop2026canon.presentation.layout import LAYOUT

    pygame.init()

    level = CANON_LEVELS[level_number - 1]
    game = new_game(level)

    if headless:
        # Modo headless: avanza ticks sin renderizar
        frames = 0
        while game.running:
            game = advance(game, Command())
            frames += 1
            if max_frames and frames >= max_frames:
                break
        typer.echo(
            f"status={game.status.name} ticks={game.tick_count} "
            f"hp={game.kid.hp_curr} room={game.kid.room}"
        )
        return 0

    screen = pygame.display.set_mode((LAYOUT.window_w, LAYOUT.window_h))
    pygame.display.set_caption(f"pop2026canon — {level.name} (L{level_number}/14)")
    font = pygame.font.Font(None, 22)
    clock = pygame.time.Clock()

    # Loop 12 FPS lógico, 60 FPS visual
    visual_frames = 0
    while game.running:
        if input_device.should_quit():
            break
        # Cada 5 frames visuales = 1 tick lógico
        if visual_frames % 5 == 0:
            cmd = input_device.poll()
            game = advance(game, cmd)
        renderer.render(screen, game, font)
        pygame.display.flip()
        clock.tick(60)
        visual_frames += 1
        if max_frames and visual_frames >= max_frames:
            break

    pygame.quit()
    return 0


_PREVIEW_DEFAULT = Path("preview_canon.png")


@app.command()
def preview(
    level: int = typer.Argument(..., min=1, max=14, help="Nivel a renderizar (1-14)."),
    out: Path = typer.Option(  # noqa: B008
        _PREVIEW_DEFAULT, "--out", "-o", help="PNG de salida."
    ),
) -> None:
    """Renderiza la primera sala de un nivel como PNG (sin ventana)."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    import pygame

    from pop2026canon.presentation import renderer
    from pop2026canon.presentation.layout import LAYOUT

    pygame.init()
    try:
        lv = CANON_LEVELS[level - 1]
        game = new_game(lv)
        surf = pygame.Surface((LAYOUT.window_w, LAYOUT.window_h))
        font = pygame.font.Font(None, 22)
        renderer.render(surf, game, font)
        out.parent.mkdir(parents=True, exist_ok=True)
        pygame.image.save(surf, str(out))
        typer.echo(f"Preview guardado en {out}")
    finally:
        pygame.quit()


if __name__ == "__main__":
    app()
