"""Escena: compone un frame con todas las capas modernas.

Orden: pared y tiles (renderer canon) → sombras → personajes →
partículas → luz → post-proceso → transición → filtro de rebobinado →
HUD, rótulo y pistas. La sacudida de cámara mueve sólo el mundo; el HUD
queda quieto.
"""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from pop2026canon.domain.game import Game
from pop2026canon.infrastructure.settings import Settings
from pop2026canon.presentation import renderer
from pop2026canon.presentation.backdrop import backdrop
from pop2026canon.presentation.fx import (
    FxEvent,
    FxKind,
    Lighting,
    Particles,
    PostFx,
    RoomTransition,
    detect_fx_events,
    draw_char_shadows,
    level_is_palace,
    rewind_filter,
    transition_direction,
)
from pop2026canon.presentation.hud import (
    HudState,
    draw_banner,
    draw_hud,
    draw_rewind_icon,
    draw_toast,
)
from pop2026canon.presentation.layout import LAYOUT


@dataclass
class Shake:
    amount: float = 0.0

    def add(self, amount: float) -> None:
        self.amount = min(14.0, max(self.amount, amount))

    def update(self, dt: float) -> None:
        self.amount = max(0.0, self.amount - dt * 40.0)

    def offset(self, t: float) -> tuple[int, int]:
        if self.amount < 0.5:
            return 0, 0
        a = self.amount
        return int(a * _noise(t * 37.0)), int(a * _noise(t * 41.0 + 3.1))


def _noise(x: float) -> float:
    import math

    return math.sin(x) * 0.6 + math.sin(x * 2.3 + 1.7) * 0.4


class Scene:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.particles = Particles(seed=2026)
        self.lighting = Lighting()
        self.post = PostFx()
        self.transition = RoomTransition()
        self.hud = HudState()
        self.shake = Shake()
        self.hitstop = 0
        self._t = 0.0
        self._world = pygame.Surface((LAYOUT.window_w, LAYOUT.window_h))
        self._last_frame = pygame.Surface((LAYOUT.window_w, LAYOUT.window_h))
        self.last_events: list[FxEvent] = []

    # --- ciclo de vida -------------------------------------------------

    def on_level_start(self, game: Game) -> None:
        self.particles.clear()
        self.transition.old = None
        self.hud.shown_hp = float(game.kid.hp_curr)
        self.hud.show_banner()

    def on_respawn(self, game: Game) -> None:
        self.particles.clear()
        self.transition.old = None
        self.hud.shown_hp = float(game.kid.hp_curr)

    def on_tick(self, prev: Game, now: Game) -> None:
        events = detect_fx_events(prev, now)
        self.last_events = events
        s = self.settings
        for ev in events:
            if s.particles:
                self.particles.spawn_for(ev)
            k = ev.kind
            if k is FxKind.HIT:
                self.hitstop = max(self.hitstop, 3)
                self.lighting.flash(ev.x, ev.y, 70, (160, 40, 30))
                if ev.on_kid:
                    self.post.damage_flash((255, 30, 30), 1.0)
                    self._shake(7)
                else:
                    self._shake(4)
            elif k is FxKind.PARRY:
                self.hitstop = max(self.hitstop, 2)
                self.lighting.flash(ev.x, ev.y, 90, (255, 220, 150))
                self._shake(2)
            elif k is FxKind.LAND and ev.strength > 1.1 and ev.on_kid:
                self._shake(3 * ev.strength)
            elif k is FxKind.DEATH:
                self._shake(10)
                self.post.damage_flash((120, 0, 0), 1.0)
            elif k is FxKind.BLOOD and ev.on_kid:
                self.post.damage_flash((255, 0, 0), 1.0)
                self._shake(8)
            elif k is FxKind.CRASH:
                self._shake(5)
            elif k in (FxKind.POTION, FxKind.SWORD):
                self.lighting.flash(ev.x, ev.y, 120, ev.color)
                self.post.damage_flash(ev.color, 0.5)
            elif k is FxKind.GATE_SLAM:
                self._shake(2)
        if now.kid.hp_curr < prev.kid.hp_curr and not any(e.on_kid for e in events):
            self.post.damage_flash((255, 30, 30), 0.8)
        direction = transition_direction(prev, now)
        if direction is not None:
            # La sala que sale se pinta SIN personajes: el kid ya está en
            # la nueva y no debe verse dos veces durante el deslizamiento.
            self._render_room(self._last_frame, prev, None, 1.0, self._t, chars=False)
            self.transition.start(self._last_frame, direction)
            self.particles.clear()

    def _shake(self, amount: float) -> None:
        if self.settings.screen_shake:
            self.shake.add(amount)

    def update(self, dt: float, game: Game, t: float) -> None:
        self.particles.update(dt)
        if self.settings.particles and not self.transition.active:
            self.particles.ambient(game, dt, t)
        self.lighting.update(dt)
        self.post.update(dt)
        self.transition.update(dt)
        self.hud.update(dt, game.kid.hp_curr)
        self.shake.update(dt)

    # --- dibujo ----------------------------------------------------------

    def _render_room(
        self,
        world: pygame.Surface,
        game: Game,
        prev: Game | None,
        alpha: float,
        t: float,
        *,
        chars: bool,
    ) -> None:
        """Sala con luz, sombras, personajes y partículas (sin HUD)."""
        s = self.settings
        world.fill((0, 0, 0))
        world.blit(backdrop(game.kid.room, level_is_palace(game.level.number)), (0, LAYOUT.hud_top))
        renderer._draw_room_tiles(world, game)
        if not s.lighting:
            renderer._draw_torch_flicker(world, game)
        if chars:
            draw_char_shadows(world, game, prev, alpha)
            renderer._draw_chars(world, game, prev, alpha)
            if s.particles:
                self.particles.draw(world)
        if s.lighting:
            prev_kid = prev.kid if prev is not None else None
            kid_px = renderer._lerp_char_px(prev_kid, game.kid, alpha)
            self.lighting.apply(world, game, kid_px, t)
            self.post.vignette(world)

    def draw(
        self,
        canvas: pygame.Surface,
        game: Game,
        prev: Game | None,
        alpha: float,
        t: float,
        *,
        sand: float | None,
        rewinding: bool,
        show_time: bool,
        hud: bool = True,
        toast: bool = True,
    ) -> None:
        s = self.settings
        self._t = t
        world = self._world
        self._render_room(world, game, prev, alpha, t, chars=True)
        self.post.apply(
            world,
            low_hp=game.kid.hp_curr == 1 and game.kid.alive < 0,
            t=t,
            flashes_enabled=s.flashes,
            vignette=False,
        )
        self.transition.compose(world)
        if rewinding:
            rewind_filter(world, t)
        self._last_frame.blit(world, (0, 0))

        ox, oy = self.shake.offset(t)
        canvas.fill((0, 0, 0))
        area = pygame.Rect(0, LAYOUT.hud_top, LAYOUT.window_w, LAYOUT.room_h)
        canvas.blit(world, (ox, LAYOUT.hud_top + oy), area)
        if hud:
            draw_hud(
                canvas,
                game,
                self.hud,
                t=t,
                sand=sand,
                rewinding=rewinding,
                show_time=show_time or s.always_show_timer,
            )
            draw_banner(canvas, game, self.hud)
            if toast:
                draw_toast(canvas, self.hud)
            if rewinding:
                draw_rewind_icon(canvas, t)
