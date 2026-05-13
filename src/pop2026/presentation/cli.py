"""CLI Typer del juego."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import typer

from pop2026 import __version__
from pop2026.application.campaign import CAMPAIGN, total_levels
from pop2026.presentation.app import AppConfig, run

app = typer.Typer(
    name="pop2026",
    help="Prince of Persia (1989), reimaginado en Python 2026.",
    no_args_is_help=False,
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"pop2026 {__version__}")
        raise typer.Exit(0)


@app.callback(invoke_without_command=True)
def _main(
    ctx: typer.Context,
    *,
    demo: bool = typer.Option(False, "--demo", help="Reproduce una demo determinista."),
    seed: int = typer.Option(42, "--seed", min=0, max=0xFF, help="Semilla del RNG (0..255)."),
    frames: int = typer.Option(0, "--frames", help="Limita el número de ticks (0 = sin límite)."),
    start_level: int = typer.Option(
        1, "--start-level", min=1, max=total_levels(), help=f"Nivel inicial (1..{total_levels()})."
    ),
    headless: bool = typer.Option(False, "--headless", help="Sin ventana ni audio (CI / scripts)."),
    no_crt: bool = typer.Option(False, "--no-crt", help="Desactiva el overlay CRT."),
    mute: bool = typer.Option(False, "--mute", help="Sin audio."),
    skip_title: bool = typer.Option(False, "--skip-title", help="Salta la pantalla de título."),
    difficulty: str = typer.Option(
        "normal", "--difficulty", help="normal | hard (hard: 2 HP iniciales)."
    ),
    resume: bool = typer.Option(False, "--resume", help="Carga la partida guardada (si existe)."),
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Imprime la versión y sale.",
    ),
) -> None:
    """Lanza la campaña o la demo."""
    if ctx.invoked_subcommand is not None:
        return
    _ = version
    config = AppConfig(
        seed=seed,
        demo=demo,
        headless=headless,
        max_frames=frames,
        start_level=start_level,
        crt=not no_crt,
        mute=mute,
        skip_title=skip_title,
        difficulty=difficulty,
        resume=resume,
    )
    code = run(config)
    sys.exit(code)


_PREVIEW_DEFAULT = Path("preview.png")


@app.command()
def preview(
    slug: str = typer.Argument(
        ..., help="Slug del nivel built-in (p. ej. '01_cell', '12_jaffar')."
    ),
    out: Path = typer.Option(  # noqa: B008
        _PREVIEW_DEFAULT, "--out", "-o", help="Ruta del PNG de salida."
    ),
    no_crt: bool = typer.Option(
        False, "--no-crt", help="Desactiva el overlay CRT."
    ),
) -> None:
    """Renderiza un nivel a PNG sin abrir ventana (útil para README y debug)."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    import pygame

    from pop2026.domain.game import new_game
    from pop2026.infrastructure.levels import load_builtin
    from pop2026.presentation import renderer
    from pop2026.presentation.theme import LAYOUT

    valid_slugs = {info.slug for info in CAMPAIGN}
    if slug not in valid_slugs:
        typer.echo(f"Nivel desconocido: {slug!r}", err=True)
        typer.echo(f"Niveles disponibles: {', '.join(sorted(valid_slugs))}", err=True)
        raise typer.Exit(2)

    pygame.init()
    try:
        level = load_builtin(slug)
        game = new_game(level, level_index=1)
        surface = pygame.Surface((LAYOUT.width_px, LAYOUT.height_px))
        font = pygame.font.Font(None, 22)
        renderer.render(surface, game, font, crt=not no_crt)
        out.parent.mkdir(parents=True, exist_ok=True)
        pygame.image.save(surface, str(out))
        typer.echo(f"Preview guardada en {out}")
    finally:
        pygame.quit()
