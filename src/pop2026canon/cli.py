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

    Fases: TITLE → LEVEL_CARD → PLAYING. Al morir se reintenta el nivel
    (el reloj de 60 min sigue corriendo); al cruzar la exit door se pasa
    al siguiente nivel con card intermedia; alcanzar a la princesa en
    L14 gana el juego. Timeout = derrota definitiva.
    """
    import pygame

    from pop2026canon.application.audio_bridge import play_transitions
    from pop2026canon.application.session import Session, resolve_transition
    from pop2026canon.infrastructure.audio import Beeper
    from pop2026canon.presentation import input_device, renderer
    from pop2026canon.presentation.layout import LAYOUT
    from pop2026canon.presentation.screens import cutscene, ending, title

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

    from pop2026canon.infrastructure import savegame

    screen = pygame.display.set_mode((LAYOUT.window_w, LAYOUT.window_h))
    canvas = pygame.Surface((LAYOUT.window_w, LAYOUT.window_h))
    font = pygame.font.Font(None, 22)
    font_big = pygame.font.Font(None, 56)
    font_small = pygame.font.Font(None, 22)
    clock = pygame.time.Clock()
    beeper = Beeper()

    save_path = savegame.default_save_path()
    # El autosave sólo aplica a la campaña estándar (los niveles de un
    # LEVELS.DAT externo no serían restaurables sin el fichero).
    autosave_enabled = levels_dat is None
    has_save = autosave_enabled and save_path.exists()

    def _autosave() -> None:
        if autosave_enabled:
            slot = savegame.save_game(game, deaths=session.deaths)
            savegame.write_to_disk(slot, save_path)

    def _set_caption() -> None:
        lvl = game.level
        pygame.display.set_caption(f"pop2026canon — {lvl.name} (L{lvl.number}/14)")

    _set_caption()

    phase: str = "card" if skip_intro else "title"
    phase_t0 = pygame.time.get_ticks() / 1000.0
    visual_frames = 0
    frames_since_tick = 0
    prev_game = game
    paused = False
    quit_requested = False
    shake_frames = 0

    def _phase_t() -> float:
        return pygame.time.get_ticks() / 1000.0 - phase_t0

    def _goto(new_phase: str) -> None:
        nonlocal phase, phase_t0
        phase = new_phase
        phase_t0 = pygame.time.get_ticks() / 1000.0

    while not quit_requested:
        # Única pasada de eventos por frame (poll() usa get_pressed, no
        # consume la cola).
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                quit_requested = True
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    quit_requested = True
                elif ev.key == pygame.K_RETURN:
                    if phase in ("title", "card", "dead"):
                        if phase == "dead":
                            _set_caption()
                        if phase == "card":
                            _autosave()
                        _goto("playing" if phase != "title" else "card")
                elif ev.key == pygame.K_c and phase == "title" and has_save:
                    # Continuar la partida guardada
                    try:
                        slot = savegame.read_from_disk(save_path)
                        game = savegame.load_save(slot)
                        prev_game = game
                        session = Session(
                            level_number=slot.level,
                            hp_max=slot.kid_hp_max,
                            time=game.time,
                            deaths=slot.deaths,
                            levels=campaign_levels,
                        )
                        _set_caption()
                        _goto("card")
                    except (ValueError, OSError):
                        pass  # save corrupto: sigue en title
                elif ev.key == pygame.K_p and phase == "playing":
                    paused = not paused
                elif ev.key == pygame.K_r and phase in ("defeat", "victory"):
                    # Reinicia la campaña completa (mismo set de niveles)
                    session = Session(level_number=1, levels=campaign_levels)
                    game = session.start_game()
                    prev_game = game
                    _set_caption()
                    _goto("card")

        if quit_requested:
            break

        target = screen
        if phase == "title":
            title.draw(screen, font_big, font_small, _phase_t())
            if has_save:
                hint = font_small.render("C — continuar la partida guardada", True, (200, 190, 160))
                screen.blit(
                    hint, hint.get_rect(center=(screen.get_width() // 2, screen.get_height() - 28))
                )
        elif phase == "card":
            cutscene.draw_level_card(screen, game.level, font_big, font_small, _phase_t())
        elif phase == "playing":
            if not game.running:
                session, next_game, outcome = resolve_transition(session, game)
                if outcome == "victory":
                    if autosave_enabled and save_path.exists():
                        save_path.unlink()  # campaña completada
                    _goto("victory")
                elif outcome == "timeout":
                    _goto("defeat")
                elif outcome == "card":
                    game = next_game if next_game is not None else game
                    prev_game = game
                    _set_caption()
                    _autosave()
                    _goto("card")
                else:  # respawn tras muerte
                    game = next_game if next_game is not None else game
                    prev_game = game
                    _autosave()
                    _goto("dead")
                continue
            if not paused and frames_since_tick >= 4:
                cmd = input_device.poll()
                prev_game = game
                game = advance(game, cmd)
                play_transitions(beeper, prev_game, game)
                session = session.after_tick(game)
                frames_since_tick = 0
                # Screen shake: impacto fuerte o muerte este tick
                kid, pk = game.kid, prev_game.kid
                if kid.landed_fall_y > 0 and kid.hp_curr < pk.hp_curr:
                    shake_frames = 8
                elif kid.alive >= 0 and pk.alive < 0:
                    shake_frames = 12
            elif not paused:
                frames_since_tick += 1
            keys = pygame.key.get_pressed()
            alpha = min(1.0, (frames_since_tick + 1) / 5.0)
            target = canvas if shake_frames > 0 else screen
            renderer.render(
                target,
                game,
                font,
                show_time=bool(keys[pygame.K_TAB]),
                prev=prev_game,
                alpha=alpha,
            )
            if shake_frames > 0:
                mag = max(1, shake_frames // 3)
                dx = mag if (visual_frames % 4) < 2 else -mag
                dy = -mag if (visual_frames % 2) == 0 else mag
                screen.fill((0, 0, 0))
                screen.blit(canvas, (dx, dy))
                shake_frames -= 1
            if paused:
                _draw_pause_overlay(screen, font_big)
        elif phase == "dead":
            renderer.render(screen, game, font)
            ending.draw_death_overlay(screen, font_big, font_small, deaths=session.deaths)
        elif phase == "victory":
            ending.draw_victory(screen, font_big, font_small)
        elif phase == "defeat":
            ending.draw_defeat(screen, font_big, font_small, timeout=True)

        pygame.display.flip()
        clock.tick(60)
        visual_frames += 1
        if max_frames and visual_frames >= max_frames:
            break

    pygame.quit()
    return 0


def _draw_pause_overlay(screen: object, font_big: object) -> None:
    """Velo de pausa sobre el frame actual."""
    import pygame

    surf = screen
    assert isinstance(surf, pygame.Surface)
    assert isinstance(font_big, pygame.font.Font)
    veil = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    veil.fill((0, 0, 0, 140))
    surf.blit(veil, (0, 0))
    txt = font_big.render("PAUSA", True, (235, 220, 180))
    surf.blit(txt, txt.get_rect(center=(surf.get_width() // 2, surf.get_height() // 2)))


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
