"""Bucle del juego con ventana: fases, menús, ayudas, efectos y audio.

Fases::

    title ─▶ card ─▶ playing ⇄ paused ⇄ (options | controls | map)
                        │
                        ├─▶ dead ─▶ playing (rebobinar / reaparecer)
                        ├─▶ level_done ─▶ card
                        └─▶ victory | defeat ─▶ title

La lógica corre a 12 ticks/s (canon) y el dibujo a 60 fps con
interpolación; el rebobinado recorre el pasado a 30 ticks/s.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pygame

from pop2026canon.application.assist import RoomCheckpoint, TimeRewind
from pop2026canon.application.audio_bridge import play_transitions
from pop2026canon.application.controller import Command
from pop2026canon.application.hints import HINTS, detect_hint
from pop2026canon.application.session import Session, resolve_transition
from pop2026canon.application.stats import LevelStats
from pop2026canon.application.tick import advance
from pop2026canon.domain.combat import char_opp_dist, is_hostile
from pop2026canon.domain.game import Game, GameStatus
from pop2026canon.infrastructure import savegame
from pop2026canon.infrastructure import settings as settings_io
from pop2026canon.infrastructure.audio import SND_REWIND, SND_UI_MOVE, SND_UI_SELECT, AudioEngine
from pop2026canon.infrastructure.settings import Settings
from pop2026canon.presentation import fonts
from pop2026canon.presentation.display import Display
from pop2026canon.presentation.fx import level_is_palace
from pop2026canon.presentation.input_device import InputHub, UiAction
from pop2026canon.presentation.layout import LAYOUT
from pop2026canon.presentation.menu import (
    Menu,
    dim,
    draw_controls,
    draw_menu,
    main_menu,
    options_menu,
    pause_menu,
)
from pop2026canon.presentation.minimap import draw_minimap
from pop2026canon.presentation.scene import Scene
from pop2026canon.presentation.screens import cutscene, ending, title

FRAMES_PER_TICK = 5
"""60 fps / 12 ticks lógicos."""

REWIND_FRAMES_PER_STEP = 2
"""El pasado se recorre a 30 ticks/s (2.5x)."""


@dataclass
class _Overlay:
    """Pantalla superpuesta (opciones / controles) y a qué fase vuelve."""

    kind: str
    back_to: str
    menu: Menu | None = None


@dataclass
class GameApp:
    session: Session
    campaign_levels: tuple  # type: ignore[type-arg]
    autosave_enabled: bool = True
    skip_intro: bool = False
    max_frames: int = 0
    settings_path: Path | None = None
    save_path: Path = field(default_factory=savegame.default_save_path)

    def __post_init__(self) -> None:
        self.settings: Settings = settings_io.load(self.settings_path)
        self.display = Display(self.settings)
        self.canvas = self.display.canvas
        self.input = InputHub()
        self.audio = AudioEngine(
            sfx_volume=self.settings.effective_sfx, music_volume=self.settings.effective_music
        )
        self.scene = Scene(self.settings)
        self.font_big = pygame.font.Font(None, 56)
        self.font_small = pygame.font.Font(None, 22)
        self.clock = pygame.time.Clock()
        self.game: Game = self.session.start_game()
        self.prev_game: Game = self.game
        self.rewind = TimeRewind()
        self.checkpoint = RoomCheckpoint()
        self.stats = LevelStats(level=self.game.level.number)
        self.phase = "card" if self.skip_intro else "title"
        self.phase_t0 = 0.0
        self.now = 0.0
        self.frames_since_tick = 0
        self.rewind_frames = 0
        self.rewinding = False
        self.menu: Menu = main_menu(self._has_save())
        self.overlay: _Overlay | None = None
        self.quit = False
        self._map_from_play = False
        self._died_hint_shown = False
        self._set_caption()

    # --- utilidades ------------------------------------------------------

    def _has_save(self) -> bool:
        return self.autosave_enabled and self.save_path.exists()

    def _set_caption(self) -> None:
        lvl = self.game.level
        pygame.display.set_caption(f"Prince of Persia — {lvl.name} ({lvl.number}/14)")

    def _goto(self, phase: str) -> None:
        self.phase = phase
        self.phase_t0 = self.now

    @property
    def phase_t(self) -> float:
        return self.now - self.phase_t0

    def _autosave(self) -> None:
        if self.autosave_enabled:
            slot = savegame.save_game(self.game, deaths=self.session.deaths)
            savegame.write_to_disk(slot, self.save_path)

    def _apply_settings(self, new: Settings) -> None:
        if new == self.settings:
            return
        self.settings = new
        self.display.apply(new)
        self.scene.settings = new
        self.audio.set_volumes(new.effective_sfx, new.effective_music)

    def _save_settings(self) -> None:
        settings_io.save(self.settings, self.settings_path)

    def _music_for_level(self) -> str:
        return "palace" if level_is_palace(self.game.level.number) else "dungeon"

    def _start_level(self) -> None:
        self.prev_game = self.game
        self.rewind.reset()
        self.checkpoint.reset(self.game)
        self.stats = LevelStats(level=self.game.level.number)
        self.stats.start(self.game)
        self.scene.on_level_start(self.game)
        self.frames_since_tick = 0
        self.audio.music(self._music_for_level())
        self._set_caption()

    # --- eventos ---------------------------------------------------------

    def _handle_events(self) -> list[UiAction]:
        actions: list[UiAction] = []
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.quit = True
            elif ev.type == pygame.VIDEORESIZE:
                self.display.on_resize((ev.w, ev.h))
            elif ev.type == pygame.WINDOWFOCUSLOST and self.phase == "playing":
                self._pause()
            else:
                actions += self.input.handle_event(ev)
        for a in list(actions):
            if a is UiAction.FULLSCREEN:
                actions.remove(a)
                self._apply_settings(self.settings.with_(fullscreen=not self.settings.fullscreen))
                self._save_settings()
        return actions

    def _pause(self) -> None:
        self.menu = pause_menu()
        self.audio.duck(0.6)
        self.audio.loop(None)
        self._goto("paused")

    def _menu_sound(self, result: str | None) -> None:
        if result in {"_move", "_change"}:
            self.audio.play(SND_UI_MOVE, volume=0.6)
        elif result:
            self.audio.play(SND_UI_SELECT, volume=0.7)

    # --- fases -----------------------------------------------------------

    def _update_overlay(self, actions: list[UiAction]) -> bool:
        """Opciones / controles por encima de otra fase. ``True`` si está activo."""
        ov = self.overlay
        if ov is None:
            return False
        for a in actions:
            if ov.kind == "controls":
                if a in (UiAction.CONFIRM, UiAction.BACK, UiAction.PAUSE):
                    self.audio.play(SND_UI_SELECT, volume=0.7)
                    self.overlay = None
            elif ov.menu is not None:
                new, result = ov.menu.handle(a, self.settings)
                self._menu_sound(result)
                self._apply_settings(new)
                if result == "back":
                    self._save_settings()
                    self.overlay = None
        return True

    def _title(self, actions: list[UiAction]) -> None:
        intro_done = self.phase_t >= title.INTRO_DURATION
        for a in actions:
            if not intro_done:
                if a in (UiAction.CONFIRM, UiAction.PAUSE):
                    self.phase_t0 = self.now - title.INTRO_DURATION
                continue
            if a is UiAction.CONTINUE and self._has_save():
                self._choose_title("continue")
                continue
            _, result = self.menu.handle(a, self.settings)
            self._menu_sound(result)
            if result and not result.startswith("_"):
                self._choose_title(result)

    def _choose_title(self, key: str) -> None:
        if key == "continue":
            try:
                slot = savegame.read_from_disk(self.save_path)
                self.game = savegame.load_save(slot)
                self.session = Session(
                    level_number=slot.level,
                    hp_max=slot.kid_hp_max,
                    time=self.game.time,
                    deaths=slot.deaths,
                    has_sword=slot.has_sword,
                    levels=self.campaign_levels,
                )
                self._set_caption()
                self._goto("card")
            except (ValueError, OSError):
                self.menu = main_menu(False)
        elif key == "new":
            self.session = Session(level_number=1, levels=self.campaign_levels)
            self.game = self.session.start_game()
            self._set_caption()
            self._goto("card")
        elif key == "options":
            self.overlay = _Overlay("options", "title", options_menu())
        elif key == "controls":
            self.overlay = _Overlay("controls", "title")
        elif key == "quit":
            self.quit = True

    def _card(self, actions: list[UiAction]) -> None:
        if any(a in (UiAction.CONFIRM, UiAction.PAUSE) for a in actions) or self.phase_t > 6.0:
            self._autosave()
            self._start_level()
            self._goto("playing")

    def _paused(self, actions: list[UiAction]) -> None:
        for a in actions:
            if self.phase == "map":
                if a in (UiAction.CONFIRM, UiAction.BACK, UiAction.PAUSE, UiAction.MAP):
                    if self._map_from_play:
                        self._map_from_play = False
                        self.audio.duck(0.0)
                        self._goto("playing")
                    else:
                        self._goto("paused")
                continue
            _, result = self.menu.handle(a, self.settings)
            self._menu_sound(result)
            if result == "resume":
                self.audio.duck(0.0)
                self._goto("playing")
            elif result == "restart":
                self.session = self.session.after_tick(self.game)
                self.game = self.session.start_game()
                self._start_level()
                self.audio.duck(0.0)
                self._goto("playing")
            elif result == "map":
                self._goto("map")
            elif result == "options":
                self.overlay = _Overlay("options", "paused", options_menu())
            elif result == "controls":
                self.overlay = _Overlay("controls", "paused")
            elif result == "title":
                self.audio.duck(0.0)
                self.audio.music("dungeon")
                self.menu = main_menu(self._has_save())
                self._goto("title")
                self.phase_t0 = self.now - title.INTRO_DURATION

    def _show_hint(self, key: str) -> None:
        s = self.settings
        if not s.hints or key in s.seen_hints or self.scene.hud.toast_t > 0:
            return
        hint = HINTS[key]
        self.scene.hud.show_toast(hint.pad_text if self.input.pad_connected else hint.text)
        self._apply_settings(s.with_(seen_hints=(*s.seen_hints, key)))
        self._save_settings()

    def _combat_active(self) -> bool:
        k = self.game.kid
        return any(
            is_hostile(c)
            and c.alive < 0
            and c.room == k.room
            and c.curr_row == k.curr_row
            and abs(char_opp_dist(k, c)) < 120
            for c in self.game.others
        )

    def _playing(self, actions: list[UiAction]) -> None:
        for a in actions:
            if a is UiAction.PAUSE:
                self._pause()
                return
            if a is UiAction.MAP:
                self.menu = pause_menu()
                self.audio.duck(0.6)
                self._map_from_play = True
                self._goto("map")
                return

        modern = self.settings.modern
        want_rewind = modern and self.input.rewind_held()
        if want_rewind and self.rewind.can_rewind:
            self.rewinding = True
            self.audio.loop(SND_REWIND)
            self.rewind_frames += 1
            if self.rewind_frames >= REWIND_FRAMES_PER_STEP:
                self.rewind_frames = 0
                back = self.rewind.step_back()
                if back is not None:
                    self.prev_game = back
                    self.game = back
                    self.stats.rewound_ticks += 1
            self.frames_since_tick = FRAMES_PER_TICK - 1
            return
        if self.rewinding:
            self.rewinding = False
            self.audio.loop(None)
            self.scene.on_respawn(self.game)

        if self.scene.hitstop > 0:
            self.scene.hitstop -= 1
            return
        self.frames_since_tick += 1
        if self.frames_since_tick < FRAMES_PER_TICK:
            return
        self.frames_since_tick = 0
        cmd: Command = self.input.command()
        if modern and self.game.kid.alive < 0:
            # Sólo se recuerdan estados con el kid vivo: rebobinar desde la
            # muerte vuelve directamente al instante anterior al golpe.
            self.rewind.record(self.game)
        prev = self.game
        self.prev_game = prev
        self.game = advance(prev, cmd)
        self.scene.on_tick(prev, self.game)
        play_transitions(self.audio, prev, self.game, self.scene.last_events)
        self.session = self.session.after_tick(self.game)
        self.stats.observe(prev, self.game)
        self.checkpoint.observe(self.game)
        self.audio.combat(self._combat_active())
        hint = detect_hint(self.game)
        if hint is not None and (hint != "rewind" or modern):
            self._show_hint(hint)
        if not self.game.running:
            self._on_level_end()

    def _on_level_end(self) -> None:
        status = self.game.status
        self.audio.combat(False)
        if status is GameStatus.WON_LEVEL:
            self._goto("level_done")
        elif status is GameStatus.WON_GAME:
            if self.autosave_enabled and self.save_path.exists():
                self.save_path.unlink()
            self.audio.music("palace")
            self._goto("victory")
        elif status is GameStatus.LOST_TIMEOUT or self.game.time.is_zero():
            self._goto("defeat")
        else:
            self.stats.deaths += 1
            if self.settings.modern and not self._died_hint_shown:
                self._died_hint_shown = True
                self._show_hint("rewind")
            self._goto("dead")

    def _dead(self, actions: list[UiAction]) -> None:
        modern = self.settings.modern
        if modern and self.input.rewind_held() and self.rewind.can_rewind:
            self._goto("playing")
            return
        if self.phase_t < 0.6:
            return
        if any(a in (UiAction.CONFIRM, UiAction.PAUSE) for a in actions):
            dead = self.game
            if modern:
                self.session = self.session.on_death(dead)
                back = self.checkpoint.respawn(dead)
                self.game = back if back is not None else self.session.start_game()
                self.prev_game = self.game
                self.rewind.reset()
                self.scene.on_respawn(self.game)
                self.frames_since_tick = 0
            else:
                self.session, nxt, outcome = resolve_transition(self.session, dead)
                if outcome != "respawn" or nxt is None:
                    self._goto("defeat")
                    return
                self.game = nxt
                self._start_level()
            self._autosave()
            self._goto("playing")

    def _level_done(self, actions: list[UiAction]) -> None:
        if self.phase_t < 1.0:
            return
        if any(a in (UiAction.CONFIRM, UiAction.PAUSE) for a in actions):
            self.session, nxt, outcome = resolve_transition(self.session, self.game)
            if outcome == "card" and nxt is not None:
                self.game = nxt
                self._set_caption()
                self._autosave()
                self._goto("card")
            elif outcome == "victory":
                self._goto("victory")
            else:
                self._goto("defeat")

    def _end_screen(self, actions: list[UiAction]) -> None:
        if self.phase_t < 1.0:
            return
        if any(a in (UiAction.CONFIRM, UiAction.PAUSE) for a in actions):
            self.session = Session(level_number=1, levels=self.campaign_levels)
            self.game = self.session.start_game()
            self.menu = main_menu(self._has_save())
            self.audio.music("dungeon")
            self._goto("title")
            self.phase_t0 = self.now - title.INTRO_DURATION

    # --- dibujo ------------------------------------------------------------

    def _draw_scene(self, *, hud: bool = True, toast: bool = True) -> None:
        alpha = min(1.0, (self.frames_since_tick + 1) / FRAMES_PER_TICK)
        if self.rewinding or self.phase != "playing":
            alpha = 1.0
        self.scene.draw(
            self.canvas,
            self.game,
            self.prev_game,
            alpha,
            self.now,
            sand=self.rewind.sand_fraction if self.settings.modern else None,
            rewinding=self.rewinding,
            show_time=self.input.timer_held(),
            hud=hud,
            toast=toast,
        )

    def _draw(self) -> None:
        c = self.canvas
        p = self.phase
        if p == "title":
            intro_done = self.phase_t >= title.INTRO_DURATION
            title.draw(c, self.font_big, self.font_small, self.phase_t, with_controls=False)
            if intro_done:
                draw_menu(
                    c,
                    self.menu,
                    self.settings,
                    self.now,
                    center_y=LAYOUT.window_h * 2 // 3 + 10,
                    width=260,
                )
                if self.input.pad_connected:
                    pad = fonts.render("Mando conectado", 16, (150, 200, 150))
                    c.blit(pad, pad.get_rect(bottomright=(c.get_width() - 8, c.get_height() - 6)))
        elif p == "card":
            cutscene.draw_level_card(
                c, self.game.level, self.font_big, self.font_small, self.phase_t
            )
        elif p == "playing":
            self._draw_scene()
        elif p in ("paused", "map"):
            self._draw_scene(toast=False)
            dim(c, 150)
            if p == "map":
                draw_minimap(
                    c,
                    self.game.level,
                    self.stats.visited,
                    self.game.kid.room,
                    fonts.font(16),
                    self.now,
                )
                t1 = fonts.render(f"MAPA · {self.game.level.name}", 28, (232, 192, 64), bold=True)
                c.blit(t1, t1.get_rect(midtop=(c.get_width() // 2, LAYOUT.hud_top + 8)))
                t2 = fonts.render("Enter / B para volver", 18, (92, 76, 108))
                c.blit(t2, t2.get_rect(midbottom=(c.get_width() // 2, c.get_height() - 8)))
            elif self.overlay is None:
                draw_menu(c, self.menu, self.settings, self.now)
        elif p == "dead":
            self._draw_scene(toast=False)
            ending.draw_death_overlay(
                c,
                deaths=self.session.deaths + 1,
                can_rewind=self.settings.modern and self.rewind.can_rewind,
                modern=self.settings.modern,
                pad=self.input.pad_connected,
                t=self.now,
            )
        elif p == "level_done":
            self._draw_scene(hud=False, toast=False)
            ending.draw_level_complete(
                c,
                self.stats,
                self.game.level.name,
                len(self.game.level.rooms),
                self.phase_t,
                pad=self.input.pad_connected,
            )
        elif p == "victory":
            t = self.session.time
            ending.draw_victory(
                c,
                t=self.phase_t,
                deaths=self.session.deaths,
                time_left=f"{t.minutes:02d}:{t.ticks // 12:02d}",
            )
        elif p == "defeat":
            ending.draw_defeat(c, timeout=True, t=self.phase_t)
        ov = self.overlay
        if ov is not None:
            dim(c, 120)
            if ov.kind == "controls":
                draw_controls(c, self.now, self.input.pad_connected)
            elif ov.menu is not None:
                draw_menu(c, ov.menu, self.settings, self.now, width=420)

    # --- bucle -------------------------------------------------------------

    def run(self) -> int:
        frames = 0
        self.audio.music("dungeon")
        while not self.quit:
            dt = self.clock.tick(60) / 1000.0
            dt = min(dt, 0.05)
            self.now += dt
            actions = self._handle_events()
            if self.quit:
                break
            if not self._update_overlay(actions):
                handler = {
                    "title": self._title,
                    "card": self._card,
                    "playing": self._playing,
                    "paused": self._paused,
                    "map": self._paused,
                    "dead": self._dead,
                    "level_done": self._level_done,
                    "victory": self._end_screen,
                    "defeat": self._end_screen,
                }[self.phase]
                handler(actions)
            if self.phase in ("playing", "dead", "level_done"):
                self.scene.update(dt, self.game, self.now)
            self.audio.update(dt)
            self._draw()
            self.display.present()
            frames += 1
            if self.max_frames and frames >= self.max_frames:
                break
        self._save_settings()
        return 0
