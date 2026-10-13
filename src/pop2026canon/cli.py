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
    skip_intro: bool = typer.Option(
        False, "--skip-intro", help="Salta la intro animada y empieza en el level card."
    ),
    levels_dat: Path | None = typer.Option(  # noqa: B008 — patrón estándar de typer
        None,
        "--levels-dat",
        help=(
            "Carga los niveles ORIGINALES desde tu copia del juego: "
            "LEVELS.DAT de MS-DOS o directorio con res20NN.bin."
        ),
    ),
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

    code = _run(
        level,
        headless=headless,
        max_frames=max_frames,
        skip_intro=skip_intro,
        levels_dat=levels_dat,
    )
    sys.exit(code)


def _run(
    level_number: int,
    *,
    headless: bool,
    max_frames: int,
    skip_intro: bool = False,
    levels_dat: Path | None = None,
) -> int:
    """Loop principal — campaña completa de 14 niveles.

    Con ventana delega en :class:`pop2026canon.presentation.app.GameApp`
    (menús, ajustes, mando, efectos, audio, rebobinado). ``--headless``
    avanza ticks sin ventana (CI).
    """
    import pygame

    from pop2026canon.application.session import Session

    pygame.init()

    campaign_levels = CANON_LEVELS
    if levels_dat is not None:
        from pop2026canon.infrastructure.levels_dat import load_campaign

        campaign_levels = load_campaign(levels_dat)
        typer.echo(f"Niveles originales cargados desde {levels_dat}")

    session = Session(level_number=level_number, levels=campaign_levels)
    game = session.start_game()

    if headless:
        # Modo headless: avanza ticks sin renderizar y sin pantallas.
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

    from pop2026canon.presentation.app import GameApp

    app = GameApp(
        session=session,
        campaign_levels=campaign_levels,
        autosave_enabled=levels_dat is None,
        skip_intro=skip_intro,
        max_frames=max_frames,
    )
    try:
        return app.run()
    finally:
        pygame.quit()


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

    from pop2026canon.infrastructure.settings import Settings
    from pop2026canon.presentation.layout import LAYOUT
    from pop2026canon.presentation.scene import Scene

    pygame.init()
    try:
        lv = CANON_LEVELS[level - 1]
        game = new_game(lv)
        surf = pygame.Surface((LAYOUT.window_w, LAYOUT.window_h))
        # Escena completa (luz, resplandor, niebla) en un instante fijo.
        scene = Scene(Settings())
        scene.on_level_start(game)
        scene.hud.banner_t = 0.0
        scene.draw(surf, game, None, 1.0, 1.0, sand=None, rewinding=False, show_time=True)
        out.parent.mkdir(parents=True, exist_ok=True)
        pygame.image.save(surf, str(out))
        typer.echo(f"Preview guardado en {out}")
    finally:
        pygame.quit()


_POSTER_DEFAULT = Path("poster_canon.png")


@app.command()
def poster(
    level: int = typer.Option(
        0,
        "--level",
        min=0,
        max=14,
        help="0 = poster genérico con título; 1..14 = level card del nivel.",
    ),
    out: Path = typer.Option(  # noqa: B008
        _POSTER_DEFAULT, "--out", "-o", help="PNG de salida."
    ),
    t: float = typer.Option(4.0, "--time", help="Segundos transcurridos (afecta animación)."),
) -> None:
    """Renderiza un poster canon o level card como PNG."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    import pygame

    from pop2026canon.presentation.layout import LAYOUT
    from pop2026canon.presentation.screens.cutscene import draw_level_card
    from pop2026canon.presentation.screens.title import draw as draw_title

    pygame.init()
    try:
        surf = pygame.Surface((LAYOUT.window_w, LAYOUT.window_h))
        font_big = pygame.font.Font(None, 56)
        font_small = pygame.font.Font(None, 22)
        if level == 0:
            draw_title(surf, font_big, font_small, t)
        else:
            lv = CANON_LEVELS[level - 1]
            draw_level_card(surf, lv, font_big, font_small, t=t)
        out.parent.mkdir(parents=True, exist_ok=True)
        pygame.image.save(surf, str(out))
        typer.echo(f"Poster guardado en {out}")
    finally:
        pygame.quit()


if __name__ == "__main__":
    app()
