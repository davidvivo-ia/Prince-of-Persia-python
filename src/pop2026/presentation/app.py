"""Composition root: monta dependencias y ejecuta la campaña.

Dos modos:

- **interactive**: título → cartas de nivel → 12 niveles encadenados →
  pantalla final. El reloj global de 60 minutos se conserva entre
  niveles (homenaje al original).
- **demo**: ejecuta :mod:`pop2026.application.demo_player` con o sin
  ventana. Por defecto solo el primer nivel.
"""

from __future__ import annotations

import contextlib
import os
from dataclasses import dataclass, replace

import pygame

from pop2026.application import demo_player
from pop2026.application.campaign import CAMPAIGN, LevelInfo, total_levels
from pop2026.domain.game import (
    DEFAULT_TIME_LIMIT_TICKS,
    Game,
    GameStatus,
    advance,
    new_game,
)
from pop2026.domain.ports import Rng
from pop2026.infrastructure.levels import load_builtin
from pop2026.infrastructure.rng import LfsrRng
from pop2026.presentation import input_device, renderer
from pop2026.presentation.audio import Beeper
from pop2026.presentation.screens import card, ending, title
from pop2026.presentation.theme import LAYOUT


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Configuración inmutable de la aplicación."""

    seed: int = 42
    demo: bool = False
    headless: bool = False
    max_frames: int = 0
    start_level: int = 1
    crt: bool = True
    mute: bool = False
    skip_title: bool = False


def _make_rng(seed: int) -> Rng:
    return LfsrRng(seed)


def run(config: AppConfig) -> int:
    """Entrypoint principal. Devuelve el exit code."""
    if config.headless:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    if config.demo:
        return _run_demo(config)
    return _run_interactive(config)


# ---------------------------------------------------------------------------
# Demo (headless o con ventana, primer nivel por defecto)
# ---------------------------------------------------------------------------


def _run_demo(config: AppConfig) -> int:
    rng = _make_rng(config.seed)
    info = CAMPAIGN[max(0, config.start_level - 1)]
    level = load_builtin(info.slug)
    game = new_game(level, level_index=config.start_level)

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


# ---------------------------------------------------------------------------
# Modo interactivo con campaña completa
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class _RunState:
    """Estado persistente entre niveles."""

    time_left: int
    max_hp: int
    has_sword: bool


def _try_init_mixer() -> None:
    with contextlib.suppress(pygame.error):
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)


def _run_interactive(config: AppConfig) -> int:
    pygame.init()
    _try_init_mixer()

    screen = pygame.display.set_mode((LAYOUT.width_px, LAYOUT.height_px))
    pygame.display.set_caption("pop2026 — Prince of Persia (1989) reimaginado")
    font = pygame.font.Font(None, 22)
    font_big = pygame.font.Font(None, 56)
    clock = pygame.time.Clock()
    beeper = Beeper(mute=config.mute or config.headless)
    rng = _make_rng(config.seed)

    if not config.skip_title and not _show_title(screen, clock, font_big, font, config):
        pygame.quit()
        return 0

    state = _RunState(
        time_left=DEFAULT_TIME_LIMIT_TICKS,
        max_hp=3,
        has_sword=False,
    )

    level_idx = config.start_level
    while 1 <= level_idx <= total_levels():
        info = CAMPAIGN[level_idx - 1]

        if not _show_card(screen, clock, font_big, font, info, level_idx):
            pygame.quit()
            return 0

        final = _play_level(screen, clock, font, rng, info, level_idx, state, config)

        if final is None:
            pygame.quit()
            return 0

        if final.status is GameStatus.WON:
            state = _RunState(
                time_left=final.time_left,
                max_hp=final.prince.max_hp,
                has_sword=final.prince.has_sword,
            )
            beeper.play("victory" if level_idx == total_levels() else "jump")
            level_idx += 1
            continue

        timeout = final.status is GameStatus.LOST_TIMEOUT
        beeper.play("death")
        decision = _show_defeat(screen, clock, font_big, font, level_idx, timeout=timeout)
        if decision == "retry" and not timeout:
            continue
        pygame.quit()
        return 0

    _show_final_victory(screen, clock, font_big, font, state.time_left)
    pygame.quit()
    return 0


def _show_title(
    screen: pygame.Surface,
    clock: pygame.time.Clock,
    font_big: pygame.font.Font,
    font: pygame.font.Font,
    config: AppConfig,
) -> bool:
    t = 0.0
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                    return True
        title.draw(screen, font_big, font, t)
        if config.crt:
            _crt(screen)
        pygame.display.flip()
        dt = clock.tick(60) / 1000.0
        t += dt


def _show_card(
    screen: pygame.Surface,
    clock: pygame.time.Clock,
    font_big: pygame.font.Font,
    font: pygame.font.Font,
    info: LevelInfo,
    level_index: int,
) -> bool:
    waited = 0.0
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                if waited > 0.4:
                    return True
        card.draw(screen, info, level_index, total_levels(), font_big=font_big, font=font)
        pygame.display.flip()
        dt = clock.tick(60) / 1000.0
        waited += dt
        if waited > 5.0:
            return True


def _show_defeat(
    screen: pygame.Surface,
    clock: pygame.time.Clock,
    font_big: pygame.font.Font,
    font: pygame.font.Font,
    level_index: int,
    *,
    timeout: bool,
) -> str:
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "quit"
                if event.key == pygame.K_r and not timeout:
                    return "retry"
        ending.draw_defeat(
            screen, level_index=level_index, timeout=timeout, font_big=font_big, font=font
        )
        pygame.display.flip()
        clock.tick(60)


def _show_final_victory(
    screen: pygame.Surface,
    clock: pygame.time.Clock,
    font_big: pygame.font.Font,
    font: pygame.font.Font,
    time_left: int,
) -> None:
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.KEYDOWN and event.key in (
                pygame.K_ESCAPE,
                pygame.K_RETURN,
            ):
                return
        ending.draw_victory(screen, time_left_ticks=time_left, font_big=font_big, font=font)
        pygame.display.flip()
        clock.tick(60)


def _play_level(
    screen: pygame.Surface,
    clock: pygame.time.Clock,
    font: pygame.font.Font,
    rng: Rng,
    info: LevelInfo,
    level_index: int,
    state: _RunState,
    config: AppConfig,
) -> Game | None:
    level = load_builtin(info.slug)
    game = new_game(level, level_index=level_index, time_limit=state.time_left)
    game = replace(
        game,
        prince=replace(
            game.prince,
            max_hp=state.max_hp,
            hp=state.max_hp,
            has_sword=state.has_sword,
        ),
    )

    while game.running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return None

        inp = input_device.poll()
        game = advance(game, inp, rng)
        renderer.render(screen, game, font, crt=config.crt)
        pygame.display.flip()
        clock.tick(60)

    renderer.render(screen, game, font, crt=config.crt)
    pygame.display.flip()
    pygame.time.wait(900)
    return game


def _crt(surface: pygame.Surface) -> None:
    """Overlay CRT también en pantallas de menú."""
    w, h = surface.get_size()
    line = pygame.Surface((w, 2), pygame.SRCALPHA)
    line.fill((0, 0, 0, 26))
    for y in range(0, h, 3):
        surface.blit(line, (0, y))
