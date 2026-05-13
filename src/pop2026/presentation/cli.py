"""CLI Typer del juego."""

from __future__ import annotations

import sys

import typer

from pop2026 import __version__
from pop2026.application.campaign import total_levels
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
