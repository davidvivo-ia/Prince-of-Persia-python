"""CLI Typer del juego. Stub durante el andamiaje; completado en Fase 7."""

from __future__ import annotations

import typer

app = typer.Typer(
    name="pop2026",
    help="Prince of Persia (1989), reimaginado en Python 2026.",
    no_args_is_help=False,
    add_completion=False,
)


@app.callback(invoke_without_command=True)
def _main(
    ctx: typer.Context,
    *,
    demo: bool = typer.Option(False, "--demo", help="Ejecuta una demo determinista."),
    seed: int = typer.Option(42, "--seed", help="Semilla del RNG."),
    frames: int = typer.Option(0, "--frames", help="Frames máximos (0 = sin límite)."),
    headless: bool = typer.Option(False, "--headless", help="Sin ventana (CI/tests)."),
) -> None:
    """Entrypoint principal — durante el scaffolding solo informa."""
    if ctx.invoked_subcommand is not None:
        return
    # Stub: se completará en la fase de presentación.
    typer.echo(
        f"pop2026 (scaffolding) — demo={demo} seed={seed} frames={frames} headless={headless}"
    )
