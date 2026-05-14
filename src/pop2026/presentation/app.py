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
from pop2026.application.level_source import load_level
from pop2026.domain.game import (
    Game,
    GameStatus,
    advance,
    new_game,
)
from pop2026.domain.ports import Rng
from pop2026.infrastructure.rng import LfsrRng
from pop2026.presentation import input_device, renderer
from pop2026.presentation.audio import Beeper, play_transitions, zone_for_level
from pop2026.presentation.screens import card, cutscene, ending, title
from pop2026.presentation.theme import LAYOUT


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Configuración inmutable de la aplicación."""

    seed: int = 42
    demo: bool = False
    headless: bool = False
    max_frames: int = 0
    start_level: int = 1
    crt: bool = False
    """Overlay CRT desactivado por defecto (homenaje Apple II: HGR no tiene scanlines)."""
    mute: bool = False
    skip_title: bool = False
    difficulty: str = "normal"
    """``normal`` (3 HP iniciales) o ``hard`` (2 HP iniciales, daño x1.5)."""
    resume: bool = False
    """Si ``True``, carga la partida guardada al arrancar."""


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
    level = load_level(config.start_level, seed=config.seed)
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


DEFAULT_PER_LEVEL_TIME_TICKS: int = 90 * 60
"""Tiempo por defecto para niveles hand-crafted sin ``time_limit_ticks``."""


@dataclass(slots=True)
class _RunState:
    """Estado persistente entre niveles (sin reloj global)."""

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

    starting_hp = 2 if config.difficulty == "hard" else 3
    state = _RunState(
        max_hp=starting_hp,
        has_sword=False,
    )
    level_idx = config.start_level
    shown_cutscenes: set[str] = set()
    _ = cutscene  # uso diferido más abajo

    # Cargar partida si se pidió.
    if config.resume:
        from pop2026.infrastructure import savegame

        try:
            slot = savegame.load()
        except Exception:
            slot = None
        if slot is not None:
            level_idx = slot.level
            state = _RunState(
                max_hp=slot.max_hp,
                has_sword=False,
            )
    while 1 <= level_idx <= total_levels():
        info = CAMPAIGN[level_idx - 1]

        # Música ambient por zona (dungeon/palace/throne)
        beeper.play_music(zone_for_level(level_idx))

        # Cinemática al inicio de cada acto (1, 26, 51, 76)
        scene_at_level: dict[int, str] = {1: "act1", 26: "act2", 51: "act3", 76: "act4"}
        scene_name = scene_at_level.get(level_idx)
        if scene_name is not None and scene_name not in shown_cutscenes:
            shown_cutscenes.add(scene_name)
            if not _show_cutscene(screen, clock, font_big, font, scene_name):
                pygame.quit()
                return 0

        if not _show_card(screen, clock, font_big, font, info, level_idx):
            pygame.quit()
            return 0

        final = _play_level(screen, clock, font, beeper, rng, info, level_idx, state, config)

        if final is None:
            pygame.quit()
            return 0

        if final.status is GameStatus.WON:
            state = _RunState(
                max_hp=final.prince.max_hp,
                has_sword=final.prince.has_sword,
            )
            beeper.play("victory" if level_idx == total_levels() else "jump")
            # Guardado automático al completar un nivel
            try:
                from pop2026.infrastructure import savegame

                slot = savegame.SaveGame(
                    version=savegame.SAVE_VERSION,
                    level=min(level_idx + 1, total_levels()),
                    hp=state.max_hp,
                    max_hp=state.max_hp,
                    time_left_ms=0,  # sin reloj global; cada nivel tiene el suyo
                    rng_seed=config.seed,
                )
                savegame.save(slot)
            except Exception:
                pass  # no fatal si no se puede guardar
            level_idx += 1
            continue

        timeout = final.status is GameStatus.LOST_TIMEOUT
        beeper.play("death")
        decision = _show_defeat(screen, clock, font_big, font, level_idx, timeout=timeout)
        if decision == "retry" and not timeout:
            continue
        pygame.quit()
        return 0

    # Cinemática final (única, antes del cuadro de victoria).
    if "victory100" not in shown_cutscenes:
        shown_cutscenes.add("victory100")
        _show_cutscene(screen, clock, font_big, font, "victory100")
    _show_final_victory(screen, clock, font_big, font, 0)
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


def _show_cutscene(
    screen: pygame.Surface,
    clock: pygame.time.Clock,
    font_big: pygame.font.Font,
    font: pygame.font.Font,
    scene_name: str,
) -> bool:
    """Muestra una cinemática. Devuelve ``False`` si el usuario pulsa Esc."""
    t = 0.0
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                if t > 0.4:
                    return True
        cutscene.draw(screen, scene_name, font_big=font_big, font=font, t=t)
        pygame.display.flip()
        dt = clock.tick(60) / 1000.0
        t += dt
        if t > 6.0:
            return True


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
    beeper: Beeper,
    rng: Rng,
    info: LevelInfo,
    level_index: int,
    state: _RunState,
    config: AppConfig,
) -> Game | None:
    _ = info  # campaign info ya está disponible; el slug no se usa aquí
    level = load_level(level_index, seed=config.seed)
    # El tiempo del nivel viene del propio Level (procedural) o del default
    # per-level si es hand-crafted (sin time_limit_ticks propio).
    game = new_game(level, level_index=level_index, time_limit=DEFAULT_PER_LEVEL_TIME_TICKS)
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
        prev = game
        game = advance(game, inp, rng)
        play_transitions(beeper, prev, game)
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
