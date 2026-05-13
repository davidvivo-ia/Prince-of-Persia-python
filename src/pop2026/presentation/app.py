"""Composition root: monta dependencias y ejecuta el juego.

Dos modos:

- **interactive**: abre ventana pygame, lee teclado, renderiza, audio.
- **demo**: ejecuta :mod:`pop2026.application.demo_player` con o sin
  ventana (``headless=True`` desactiva display y audio).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from pop2026.application import demo_player
from pop2026.domain.game import Game, GameStatus, new_game
from pop2026.domain.input import InputFrame
from pop2026.domain.ports import Rng
from pop2026.infrastructure.levels import load_builtin
from pop2026.infrastructure.rng import LfsrRng
from pop2026.presentation.theme import LAYOUT


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Configuración inmutable de la aplicación."""

    seed: int = 42
    demo: bool = False
    headless: bool = False
    max_frames: int = 0
    level_name: str = "01_dungeon"
    crt: bool = True
    mute: bool = False


def _make_rng(seed: int) -> Rng:
    return LfsrRng(seed)


def run(config: AppConfig) -> int:
    """Entrypoint principal.

    Returns:
        Exit code: 0 si terminó (ganó / acabó / Esc), 1 si error.
    """
    if config.headless:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    rng = _make_rng(config.seed)
    level = load_builtin(config.level_name)
    game = new_game(level)

    if config.demo:
        return _run_demo(game, rng, config)
    return _run_interactive(game, rng, config)


def _run_demo(game: Game, rng: Rng, config: AppConfig) -> int:
    """Ejecuta la demo determinista. Con o sin ventana."""
    if config.headless:
        final = demo_player.run_to_completion(game, rng, max_frames=config.max_frames or 6_000)
        _print_summary(final)
        return 0
    return _run_demo_windowed(game, rng, config)


def _print_summary(game: Game) -> None:
    print(f"status={game.status.name} time_left={game.time_left} hp={game.prince.hp}")
    print(f"pos={game.prince.pos.row},{game.prince.pos.col}")
    print(f"hits_dealt={game.hits_dealt_total} hits_received={game.hits_received_total}")


def _run_demo_windowed(game: Game, rng: Rng, config: AppConfig) -> int:
    import pygame

    from pop2026.presentation import renderer

    pygame.init()
    screen = pygame.display.set_mode((LAYOUT.width_px, LAYOUT.height_px))
    pygame.display.set_caption("pop2026 — demo")
    font = pygame.font.Font(None, 22)
    clock = pygame.time.Clock()
    for frames, state in enumerate(
        demo_player.play(game, rng, max_frames=config.max_frames or 6_000),
        start=1,
    ):
        if pygame.event.peek(pygame.QUIT):
            break
        renderer.render(screen, state, font, crt=config.crt)
        pygame.display.flip()
        clock.tick(60)
        pygame.event.pump()
        if config.max_frames and frames >= config.max_frames:
            break
    pygame.quit()
    return 0


def _run_interactive(game: Game, rng: Rng, config: AppConfig) -> int:
    import contextlib

    import pygame

    from pop2026.application.game_loop import run as loop_run
    from pop2026.presentation import input_device, renderer
    from pop2026.presentation.audio import Beeper

    pygame.init()
    with contextlib.suppress(pygame.error):
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

    screen = pygame.display.set_mode((LAYOUT.width_px, LAYOUT.height_px))
    pygame.display.set_caption("pop2026 — Prince of Persia (1989) reimaginado")
    font = pygame.font.Font(None, 22)
    clock = pygame.time.Clock()
    beeper = Beeper(mute=config.mute or config.headless)

    def src(_g: Game) -> InputFrame:
        return input_device.poll()

    def render_and_tick(state: Game) -> None:
        if input_device.should_quit():
            raise SystemExit(0)
        renderer.render(screen, state, font, crt=config.crt)
        pygame.display.flip()
        clock.tick(60)

    try:
        final = loop_run(
            game,
            input_source=src,
            rng=rng,
            on_render=render_and_tick,
            max_frames=config.max_frames,
        )
    except SystemExit:
        pygame.quit()
        return 0

    if final.status is GameStatus.WON:
        beeper.play("victory")
    elif final.status is GameStatus.LOST_DIED:
        beeper.play("death")
    renderer.render(screen, final, font, crt=config.crt)
    pygame.display.flip()
    pygame.time.wait(1500)
    pygame.quit()
    return 0
