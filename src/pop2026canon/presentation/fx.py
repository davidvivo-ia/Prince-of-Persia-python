"""Efectos de presentación — lo que hace que se sienta un juego de 2026.

Nada de esto toca la lógica canon: todo se deriva comparando dos ticks
consecutivos (``detect_fx_events``) o del estado visible.

- **Eventos FX** (puro, testeado): aterrizajes, pasos, heridas, paradas,
  muertes, losas que se rompen o se estrellan, pociones, espada, rejas.
- **Partículas**: polvo, chispas, sangre, cascotes, destellos, ascuas
  de antorcha y motas de polvo flotando en la luz.
- **Iluminación**: mapa de luz multiplicativo con antorchas que
  parpadean, halo del kid, pociones y la puerta de salida abierta; luz
  ambiente fría en mazmorras y cálida en el palacio (tabla canon
  ``tbl_level_type``); brillo aditivo de las llamas.
- **Post-proceso**: viñeta, pulso rojo con 1 HP, destello al recibir
  daño, filtro de rebobinado (sepia + líneas), transición deslizante
  entre salas.
- **Juice**: sacudida de cámara y *hit-stop* (congelar 2-3 frames al
  conectar una estocada).
"""

from __future__ import annotations

import functools
import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto

import pygame

from pop2026canon.domain.actions import Action, Seq
from pop2026canon.domain.chars import Char, CharId
from pop2026canon.domain.game import Game
from pop2026canon.domain.tiles import PotionType, Tile
from pop2026canon.presentation.layout import LAYOUT
from pop2026canon.presentation.renderer import _char_px, _lerp_char_px

PALACE_LEVELS: frozenset[int] = frozenset({4, 5, 6, 10, 11, 14})
"""Canon ``tbl_level_type``: 1 = palacio, 0 = mazmorra."""


def level_is_palace(number: int) -> bool:
    return number in PALACE_LEVELS


# ---------------------------------------------------------------------------
# Eventos (puro)
# ---------------------------------------------------------------------------


class FxKind(Enum):
    LAND = auto()
    STEP = auto()
    HIT = auto()
    PARRY = auto()
    DEATH = auto()
    BLOOD = auto()
    CRUMBLE = auto()
    CRASH = auto()
    POTION = auto()
    SWORD = auto()
    GATE_SLAM = auto()
    EXIT_OPEN = auto()
    STRIKE = auto()


@dataclass(frozen=True, slots=True)
class FxEvent:
    kind: FxKind
    x: int
    y: int
    strength: float = 1.0
    color: tuple[int, int, int] = (255, 255, 255)
    on_kid: bool = False


BODY_H = 46
"""Altura en píxeles del centro del cuerpo sobre los pies."""

_POTION_COLORS: dict[int, tuple[int, int, int]] = {
    int(PotionType.HEAL): (255, 70, 60),
    int(PotionType.MAX_HP): (90, 255, 120),
    int(PotionType.POISON): (80, 120, 255),
    int(PotionType.FLOAT): (180, 220, 255),
    int(PotionType.TIME): (255, 220, 90),
}

_RUN_STEP_FRAMES = frozenset({125, 129})


def _cell_px(col: int, row: int) -> tuple[int, int]:
    """Centro inferior (superficie del suelo) de una celda."""
    return col * LAYOUT.tile_w + LAYOUT.tile_w // 2, LAYOUT.hud_top + (row + 1) * LAYOUT.tile_h - 4


def _started(prev: Char, now: Char, seq: Seq) -> bool:
    return now.curr_seq_id == int(seq) and (
        prev.curr_seq_id != int(seq) or now.curr_seq_idx < prev.curr_seq_idx
    )


def _char_events(prev: Char, now: Char, *, on_kid: bool) -> list[FxEvent]:
    out: list[FxEvent] = []
    x, y = _char_px(now)
    body = y - BODY_H
    fwd = 1 if now.direction == 0 else -1
    if _started(prev, now, Seq.HIT_BY_SWORD) or (
        now.alive >= 0 and prev.alive < 0 and now.curr_seq_id == int(Seq.STABBED_TO_DEATH)
    ):
        out.append(FxEvent(FxKind.HIT, x, body, 1.0, (200, 20, 20), on_kid))
    if _started(prev, now, Seq.ATTACK_PARRIED):
        out.append(FxEvent(FxKind.PARRY, x + fwd * 26, body - 6, 1.0, (255, 230, 150), on_kid))
    if _started(prev, now, Seq.STRIKE) or _started(prev, now, Seq.GUARD_STRIKE):
        out.append(FxEvent(FxKind.STRIKE, x + fwd * 30, body - 4, 0.5, (230, 230, 255), on_kid))
    if _started(prev, now, Seq.CHOMPED) or _started(prev, now, Seq.SPIKED):
        out.append(FxEvent(FxKind.BLOOD, x, y - 20, 1.5, (190, 10, 10), on_kid))
    landed = now.landed_fall_y > 0 and prev.landed_fall_y == 0
    if landed or (
        prev.action is Action.IN_FREEFALL
        and now.action is not Action.IN_FREEFALL
        and now.alive < 0
        and now.action is not Action.HANG_CLIMB
    ):
        strength = min(2.0, 0.4 + max(now.landed_fall_y, prev.fall_y) / 18)
        out.append(FxEvent(FxKind.LAND, x, y, strength, (170, 150, 130), on_kid))
    if (
        now.curr_seq_id == int(Seq.RUN)
        and now.frame in _RUN_STEP_FRAMES
        and now.frame != prev.frame
    ):
        out.append(FxEvent(FxKind.STEP, x - fwd * 8, y, 0.4, (150, 130, 110), on_kid))
    if on_kid and now.alive >= 0 and prev.alive < 0:
        out.append(FxEvent(FxKind.DEATH, x, body, 1.0, (120, 0, 0), True))
    return out


def detect_fx_events(prev: Game, now: Game) -> list[FxEvent]:
    """Eventos visuales entre dos ticks consecutivos de la sala visible."""
    room = now.kid.room
    if prev.kid.room != room:
        return []  # cambio de sala: lo cubre la transición
    events = _char_events(prev.kid, now.kid, on_kid=True)
    for i, c in enumerate(now.others):
        if c.room != room or i >= len(prev.others):
            continue
        p = prev.others[i]
        if p.charid is not c.charid or p.room != room:
            continue
        events.extend(_char_events(p, c, on_kid=False))

    level = now.level
    st_prev, st_now = prev.state, now.state
    for rid, col, row in st_now.fallen_floors - st_prev.fallen_floors:
        if rid == room:
            x, y = _cell_px(col, row)
            events.append(FxEvent(FxKind.CRUMBLE, x, y, 1.0, (170, 110, 60)))
    for rid, col, row in st_now.debris_cells - st_prev.debris_cells:
        if rid == room:
            x, y = _cell_px(col, row)
            events.append(FxEvent(FxKind.CRASH, x, y, 1.5, (180, 120, 70)))
    for rid, col, row in st_now.consumed_potions - st_prev.consumed_potions:
        if rid != room or not (1 <= rid <= len(level.rooms)):
            continue
        tile, mod = level.room(rid).tile_at(col, row)
        x, y = _cell_px(col, row)
        if tile is Tile.SWORD:
            events.append(FxEvent(FxKind.SWORD, x, y - 30, 1.5, (255, 220, 120), True))
        elif tile is Tile.POTION:
            color = _POTION_COLORS.get(mod, (255, 120, 200))
            events.append(FxEvent(FxKind.POTION, x, y - 30, 1.2, color, True))
    for rid, col, row in st_prev.open_gates - st_now.open_gates:
        if rid != room or not (1 <= rid <= len(level.rooms)):
            continue
        if level.room(rid).tile_at(col, row)[0] is Tile.GATE:
            x, y = _cell_px(col, row)
            events.append(FxEvent(FxKind.GATE_SLAM, x, y, 0.8, (140, 130, 120)))
    for rid, col, row in st_now.open_gates - st_prev.open_gates:
        if rid != room or not (1 <= rid <= len(level.rooms)):
            continue
        if level.room(rid).tile_at(col, row)[0] in (Tile.LEVEL_DOOR_LEFT, Tile.LEVEL_DOOR_RIGHT):
            x, y = _cell_px(col, row)
            events.append(FxEvent(FxKind.EXIT_OPEN, x, y - 40, 1.0, (255, 210, 120)))
    return events


# ---------------------------------------------------------------------------
# Partículas
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    color: tuple[int, int, int]
    size: float
    gravity: float = 0.0
    drag: float = 0.0
    glow: bool = False
    floor_y: float | None = None


@dataclass
class Particles:
    """Sistema de partículas en coordenadas del lienzo (sala visible)."""

    seed: int = 1
    max_particles: int = 700
    items: list[Particle] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.rng = random.Random(self.seed)

    def clear(self) -> None:
        self.items.clear()

    def burst(
        self,
        x: float,
        y: float,
        n: int,
        color: tuple[int, int, int],
        *,
        speed: tuple[float, float] = (30.0, 120.0),
        angle: tuple[float, float] = (0.0, 2 * math.pi),
        life: tuple[float, float] = (0.3, 0.8),
        size: tuple[float, float] = (1.5, 3.0),
        gravity: float = 0.0,
        drag: float = 0.0,
        glow: bool = False,
        floor_y: float | None = None,
        jitter: float = 0.0,
    ) -> None:
        r = self.rng
        for _ in range(n):
            if len(self.items) >= self.max_particles:
                self.items.pop(0)
            a = r.uniform(*angle)
            s = r.uniform(*speed)
            lf = r.uniform(*life)
            c = color
            if jitter:
                c = tuple(  # type: ignore[assignment]
                    max(0, min(255, int(v + r.uniform(-jitter, jitter)))) for v in color
                )
            self.items.append(
                Particle(
                    x + r.uniform(-2, 2),
                    y + r.uniform(-2, 2),
                    math.cos(a) * s,
                    math.sin(a) * s,
                    lf,
                    lf,
                    c,
                    r.uniform(*size),
                    gravity,
                    drag,
                    glow,
                    floor_y,
                )
            )

    def update(self, dt: float) -> None:
        alive: list[Particle] = []
        for p in self.items:
            p.life -= dt
            if p.life <= 0:
                continue
            p.vy += p.gravity * dt
            if p.drag:
                k = max(0.0, 1.0 - p.drag * dt)
                p.vx *= k
                p.vy *= k
            p.x += p.vx * dt
            p.y += p.vy * dt
            if p.floor_y is not None and p.y > p.floor_y:
                p.y = p.floor_y
                p.vy *= -0.3
                p.vx *= 0.6
            alive.append(p)
        self.items = alive

    def draw(self, surf: pygame.Surface, offset: tuple[int, int] = (0, 0)) -> None:
        ox, oy = offset
        for p in self.items:
            t = p.life / p.max_life
            size = max(1, int(p.size * (0.5 + 0.5 * t)))
            pos = (int(p.x) + ox, int(p.y) + oy)
            if p.glow:
                g = _glow_sprite(size * 3, p.color, int(255 * t))
                surf.blit(g, (pos[0] - size * 3, pos[1] - size * 3), special_flags=pygame.BLEND_ADD)
            else:
                col = (*p.color, int(255 * min(1.0, t * 1.5)))
                if size <= 1:
                    surf.fill(p.color, (pos[0], pos[1], 1, 1))
                else:
                    dot = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
                    pygame.draw.circle(dot, col, (size, size), size)
                    surf.blit(dot, (pos[0] - size, pos[1] - size))

    # --- recetas ------------------------------------------------------

    def spawn_for(self, ev: FxEvent) -> None:
        floor = float(ev.y) if ev.kind in (FxKind.LAND, FxKind.STEP) else None
        k = ev.kind
        if k is FxKind.LAND:
            n = int(8 + 14 * ev.strength)
            self.burst(
                ev.x,
                ev.y - 2,
                n,
                ev.color,
                speed=(20, 70 * ev.strength),
                angle=(math.pi * 1.05, math.pi * 1.95),
                life=(0.3, 0.7),
                size=(2, 4),
                gravity=60,
                drag=3,
                floor_y=floor,
                jitter=20,
            )
        elif k is FxKind.STEP:
            self.burst(
                ev.x,
                ev.y - 2,
                3,
                ev.color,
                speed=(10, 30),
                angle=(math.pi * 1.1, math.pi * 1.9),
                life=(0.25, 0.45),
                size=(1.5, 2.5),
                gravity=40,
                drag=4,
                floor_y=floor,
                jitter=15,
            )
        elif k is FxKind.HIT:
            self.burst(
                ev.x,
                ev.y,
                14,
                ev.color,
                speed=(40, 140),
                life=(0.3, 0.7),
                size=(1.5, 3),
                gravity=320,
                jitter=30,
                floor_y=ev.y + BODY_H,
            )
        elif k is FxKind.PARRY:
            self.burst(
                ev.x,
                ev.y,
                16,
                ev.color,
                speed=(80, 220),
                life=(0.15, 0.35),
                size=(1, 2),
                gravity=200,
                glow=True,
            )
        elif k is FxKind.STRIKE:
            self.burst(
                ev.x, ev.y, 3, ev.color, speed=(10, 30), life=(0.1, 0.2), size=(1, 1.5), glow=True
            )
        elif k is FxKind.BLOOD:
            self.burst(
                ev.x,
                ev.y,
                24,
                ev.color,
                speed=(40, 160),
                angle=(math.pi, 2 * math.pi),
                life=(0.4, 0.9),
                size=(1.5, 3.5),
                gravity=380,
                jitter=25,
                floor_y=ev.y + 18,
            )
        elif k is FxKind.DEATH:
            self.burst(
                ev.x,
                ev.y,
                10,
                (90, 0, 0),
                speed=(10, 50),
                life=(0.6, 1.2),
                size=(2, 4),
                gravity=120,
                floor_y=ev.y + BODY_H,
            )
        elif k is FxKind.CRUMBLE:
            self.burst(
                ev.x,
                ev.y - 6,
                18,
                ev.color,
                speed=(15, 60),
                angle=(0, math.pi),
                life=(0.5, 1.1),
                size=(1.5, 3.5),
                gravity=420,
                jitter=30,
            )
        elif k is FxKind.CRASH:
            self.burst(
                ev.x,
                ev.y - 4,
                30,
                ev.color,
                speed=(40, 170),
                angle=(math.pi * 1.05, math.pi * 1.95),
                life=(0.4, 1.0),
                size=(1.5, 4),
                gravity=500,
                drag=1,
                jitter=35,
                floor_y=float(ev.y),
            )
            self.burst(
                ev.x,
                ev.y - 6,
                14,
                (150, 140, 130),
                speed=(10, 45),
                angle=(math.pi * 1.1, math.pi * 1.9),
                life=(0.6, 1.3),
                size=(3, 6),
                gravity=-10,
                drag=2,
            )
        elif k in (FxKind.POTION, FxKind.SWORD, FxKind.EXIT_OPEN):
            self.burst(
                ev.x,
                ev.y,
                26,
                ev.color,
                speed=(15, 70),
                life=(0.6, 1.4),
                size=(1, 2.5),
                gravity=-35,
                drag=1.5,
                glow=True,
            )
        elif k is FxKind.GATE_SLAM:
            self.burst(
                ev.x,
                ev.y - 2,
                14,
                ev.color,
                speed=(20, 60),
                angle=(math.pi * 1.05, math.pi * 1.95),
                life=(0.4, 0.8),
                size=(2, 4),
                gravity=50,
                drag=3,
                floor_y=float(ev.y),
            )

    def ambient(self, game: Game, dt: float, t: float) -> None:
        """Ascuas de antorcha y motas de polvo flotando."""
        room = game.level.room(game.kid.room)
        r = self.rng
        for row in range(3):
            for col in range(10):
                piece = room.tile_at(col, row)[0]
                if piece in (Tile.TORCH, Tile.TORCH_WITH_DEBRIS) and r.random() < dt * 2.2:
                    cx, cy = _torch_flame_px(col, row)
                    self.burst(
                        cx,
                        cy - 6,
                        1,
                        (255, 170, 60),
                        speed=(8, 25),
                        angle=(math.pi * 1.3, math.pi * 1.7),
                        life=(0.6, 1.4),
                        size=(1, 1.6),
                        gravity=-20,
                        glow=True,
                    )
        if r.random() < dt * 1.5:
            x = r.uniform(0, LAYOUT.window_w)
            y = r.uniform(LAYOUT.hud_top + 10, LAYOUT.window_h - 10)
            self.burst(
                x,
                y,
                1,
                (200, 190, 170),
                speed=(2, 8),
                life=(2.5, 4.5),
                size=(0.8, 1.3),
                gravity=-1,
                glow=False,
            )


@functools.lru_cache(maxsize=256)
def _glow_sprite_cached(radius: int, color: tuple[int, int, int], level: int) -> pygame.Surface:
    surf = pygame.Surface((radius * 2, radius * 2))
    surf.fill((0, 0, 0))
    k = level / 255.0
    for i in range(radius, 0, -1):
        f = (1 - i / radius) ** 1.8 * k
        col = tuple(min(255, int(c * f)) for c in color)
        pygame.draw.circle(surf, col, (radius, radius), i)
    return surf


def _glow_sprite(radius: int, color: tuple[int, int, int], level: int) -> pygame.Surface:
    q = (level // 32) * 32 + 16
    return _glow_sprite_cached(max(2, radius), color, min(255, q))


def _torch_flame_px(col: int, row: int) -> tuple[int, int]:
    """Posición de la llama (coincide con ``tile_atlas.draw_torch``)."""
    cx = col * LAYOUT.tile_w + LAYOUT.tile_w // 2
    cy = LAYOUT.hud_top + row * LAYOUT.tile_h + LAYOUT.tile_h // 2 - 10 - 8
    return cx, cy


# ---------------------------------------------------------------------------
# Iluminación
# ---------------------------------------------------------------------------


@functools.lru_cache(maxsize=64)
def _light_texture(radius: int, color: tuple[int, int, int]) -> pygame.Surface:
    surf = pygame.Surface((radius * 2, radius * 2))
    surf.fill((0, 0, 0))
    step = max(1, radius // 48)
    for i in range(radius, 0, -step):
        f = (1 - i / radius) ** 1.35
        pygame.draw.circle(surf, tuple(int(c * f) for c in color), (radius, radius), i)
    return surf


DUNGEON_AMBIENT = (74, 78, 112)
PALACE_AMBIENT = (112, 98, 104)


class Lighting:
    """Mapa de luz por frame (multiplicativo) + brillo aditivo."""

    def __init__(self) -> None:
        self.lightmap = pygame.Surface((LAYOUT.window_w, LAYOUT.room_h))
        self.glowmap = pygame.Surface((LAYOUT.window_w, LAYOUT.room_h))
        self.flashes: list[list[float]] = []  # [x, y, radius, life, r, g, b]

    def flash(self, x: float, y: float, radius: float, color: tuple[int, int, int]) -> None:
        self.flashes.append([x, y, radius, 0.18, *color])

    def update(self, dt: float) -> None:
        for f in self.flashes:
            f[3] -= dt
        self.flashes = [f for f in self.flashes if f[3] > 0]

    def apply(
        self,
        surf: pygame.Surface,
        game: Game,
        kid_px: tuple[int, int],
        t: float,
        *,
        offset: tuple[int, int] = (0, 0),
    ) -> None:
        palace = level_is_palace(game.level.number)
        lm = self.lightmap
        gm = self.glowmap
        lm.fill(PALACE_AMBIENT if palace else DUNGEON_AMBIENT)
        gm.fill((0, 0, 0))
        top = LAYOUT.hud_top
        room = game.level.room(game.kid.room)

        def add(
            cx: float, cy: float, radius: int, color: tuple[int, int, int], glow: float = 0.0
        ) -> None:
            pos = (int(cx) - radius, int(cy) - top - radius)
            lm.blit(_light_texture(radius, color), pos, special_flags=pygame.BLEND_ADD)
            if glow > 0:
                gcol = (int(color[0] * glow), int(color[1] * glow), int(color[2] * glow))
                gm.blit(_light_texture(radius, gcol), pos, special_flags=pygame.BLEND_ADD)

        torches: list[tuple[int, int, int]] = []
        for row in range(3):
            for col in range(10):
                tile, mod = room.tile_at(col, row)
                if tile in (Tile.TORCH, Tile.TORCH_WITH_DEBRIS):
                    cx, cy = _torch_flame_px(col, row)
                    flick = (
                        math.sin(t * 13.0 + col * 1.7 + row) * 0.5
                        + math.sin(t * 7.3 + col * 0.9) * 0.5
                    )
                    radius = int(175 + 14 * flick)
                    add(cx, cy, radius, (235, 150, 70), glow=0.4)
                    torches.append((cx, cy, int(4 * flick)))
                elif tile is Tile.POTION and (room.id, col, row) not in game.state.consumed_potions:
                    x, y = _cell_px(col, row)
                    add(x, y - 18, 40, _POTION_COLORS.get(mod, (200, 80, 160)), glow=0.4)
                elif tile in (Tile.LEVEL_DOOR_LEFT, Tile.LEVEL_DOOR_RIGHT) and any(
                    g[0] == room.id and g[1] in (col, col - 1, col + 1) and g[2] == row
                    for g in game.state.open_gates
                ):
                    x, y = _cell_px(col, row)
                    add(x, y - 40, 120, (170, 130, 60), glow=0.3)
        kx, ky = kid_px
        add(kx, ky - 40, 120, (80, 78, 86))
        # Un poco de luz sobre cada enemigo: que no se pierda en la sombra.
        from pop2026canon.domain.combat import is_hostile

        for c in game.others:
            if c.room == room.id and is_hostile(c):
                ex, ey = _char_px(c)
                add(ex, ey - 40, 100, (90, 86, 100))
        for f in self.flashes:
            k = f[3] / 0.18
            add(f[0], f[1], int(f[2]), (int(f[4] * k), int(f[5] * k), int(f[6] * k)), glow=0.5)
        ox, oy = offset
        surf.blit(lm, (ox, top + oy), special_flags=pygame.BLEND_MULT)
        surf.blit(gm, (ox, top + oy), special_flags=pygame.BLEND_ADD)
        # Brillo aditivo de las llamas (bloom barato)
        for cx, cy, fl in torches:
            glow = _glow_sprite(22 + fl, (255, 150, 60), 200)
            surf.blit(
                glow,
                (cx - glow.get_width() // 2 + ox, cy - glow.get_height() // 2 + oy),
                special_flags=pygame.BLEND_ADD,
            )


# ---------------------------------------------------------------------------
# Sombras de personajes
# ---------------------------------------------------------------------------

_AIR = (Action.IN_FREEFALL, Action.IN_MIDAIR, Action.HANG_CLIMB, Action.HANG_STRAIGHT)


@functools.lru_cache(maxsize=4)
def _shadow_sprite(w: int, h: int) -> pygame.Surface:
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    for i in range(4):
        a = 40 + i * 18
        pygame.draw.ellipse(s, (0, 0, 0, a), (i * 3, i, w - i * 6, h - i * 2))
    return s


def draw_char_shadows(surf: pygame.Surface, game: Game, prev: Game | None, alpha: float) -> None:
    room = game.kid.room
    chars: list[tuple[Char, Char | None]] = []
    prev_others = prev.others if prev else ()
    for i, c in enumerate(game.others):
        if c.room == room and c.charid is not CharId.MOUSE:
            pc = prev_others[i] if i < len(prev_others) else None
            chars.append((c, pc))
    chars.append((game.kid, prev.kid if prev else None))
    sprite = _shadow_sprite(40, 10)
    for c, pc in chars:
        if c.action in _AIR or c.alive >= 30:
            continue
        x, y = _lerp_char_px(pc, c, alpha)
        surf.blit(sprite, (x - 20, y - 6))


# ---------------------------------------------------------------------------
# Post-proceso
# ---------------------------------------------------------------------------


@functools.lru_cache(maxsize=4)
def _vignette(w: int, h: int, strength: int) -> pygame.Surface:
    """Viñeta multiplicativa: blanco en el centro, más oscuro al borde."""
    small = pygame.Surface((64, 43))
    for y in range(43):
        for x in range(64):
            dx = (x - 31.5) / 32
            dy = (y - 21) / 21.5
            d = min(1.0, math.sqrt(dx * dx + dy * dy))
            v = int(255 - strength * max(0.0, d - 0.45) / 0.55)
            small.set_at((x, y), (v, v, v))
    return pygame.transform.smoothscale(small, (w, h))


@functools.lru_cache(maxsize=4)
def _edge_glow(w: int, h: int, color: tuple[int, int, int]) -> pygame.Surface:
    small = pygame.Surface((64, 43), pygame.SRCALPHA)
    for y in range(43):
        for x in range(64):
            dx = (x - 31.5) / 32
            dy = (y - 21) / 21.5
            d = min(1.0, math.sqrt(dx * dx + dy * dy))
            a = int(255 * max(0.0, d - 0.55) / 0.45)
            small.set_at((x, y), (*color, a))
    return pygame.transform.smoothscale(small, (w, h))


@dataclass
class PostFx:
    flash: float = 0.0
    flash_color: tuple[int, int, int] = (255, 40, 40)

    def damage_flash(
        self, color: tuple[int, int, int] = (255, 40, 40), amount: float = 1.0
    ) -> None:
        self.flash = max(self.flash, amount)
        self.flash_color = color

    def update(self, dt: float) -> None:
        self.flash = max(0.0, self.flash - dt * 4.0)

    def vignette(self, surf: pygame.Surface) -> None:
        w, h = surf.get_size()
        surf.blit(
            _vignette(w, h - LAYOUT.hud_top, 120),
            (0, LAYOUT.hud_top),
            special_flags=pygame.BLEND_MULT,
        )

    def apply(
        self,
        surf: pygame.Surface,
        *,
        low_hp: bool,
        t: float,
        flashes_enabled: bool,
        vignette: bool = True,
    ) -> None:
        w, h = surf.get_size()
        world = pygame.Rect(0, LAYOUT.hud_top, w, h - LAYOUT.hud_top)
        if vignette:
            surf.blit(
                _vignette(w, h - LAYOUT.hud_top, 120),
                world.topleft,
                special_flags=pygame.BLEND_MULT,
            )
        if low_hp:
            pulse = 0.35 + 0.35 * (0.5 + 0.5 * math.sin(t * 5.0))
            glow = _edge_glow(w, h - LAYOUT.hud_top, (170, 0, 0)).copy()
            glow.set_alpha(int(255 * pulse))
            surf.blit(glow, world.topleft)
        if self.flash > 0 and flashes_enabled:
            veil = pygame.Surface(world.size, pygame.SRCALPHA)
            veil.fill((*self.flash_color, int(110 * self.flash)))
            surf.blit(veil, world.topleft)


def rewind_filter(surf: pygame.Surface, t: float) -> None:
    """Sepia desaturado con líneas que suben: el tiempo va hacia atrás."""
    w, h = surf.get_size()
    world = pygame.Rect(0, LAYOUT.hud_top, w, h - LAYOUT.hud_top)
    sub = surf.subsurface(world)
    gray = pygame.transform.grayscale(sub)
    gray.fill((255, 214, 160), special_flags=pygame.BLEND_RGB_MULT)
    gray.fill((24, 14, 0), special_flags=pygame.BLEND_RGB_ADD)
    surf.blit(gray, world.topleft)
    lines = pygame.Surface(world.size, pygame.SRCALPHA)
    off = int(t * 240) % 24
    for y in range(-off, world.h, 24):
        pygame.draw.line(lines, (255, 230, 180, 26), (0, y), (w, y), 2)
    surf.blit(lines, world.topleft)


# ---------------------------------------------------------------------------
# Transición entre salas
# ---------------------------------------------------------------------------


class RoomTransition:
    """Desliza la sala vieja fuera y la nueva dentro (0.22 s)."""

    DURATION = 0.22

    def __init__(self) -> None:
        self.old: pygame.Surface | None = None
        self.dir = (0, 0)
        self.t = 0.0

    @property
    def active(self) -> bool:
        return self.old is not None

    def start(self, old_frame: pygame.Surface, direction: tuple[int, int]) -> None:
        world = pygame.Rect(0, LAYOUT.hud_top, LAYOUT.window_w, LAYOUT.room_h)
        self.old = old_frame.subsurface(world).copy()
        self.dir = direction
        self.t = 0.0

    def update(self, dt: float) -> None:
        if self.old is None:
            return
        self.t += dt
        if self.t >= self.DURATION:
            self.old = None

    def compose(self, surf: pygame.Surface) -> None:
        """``surf`` ya tiene la sala nueva pintada: mezcla la vieja."""
        if self.old is None:
            return
        p = min(1.0, self.t / self.DURATION)
        e = 1 - (1 - p) ** 3  # ease-out cúbico
        world = pygame.Rect(0, LAYOUT.hud_top, LAYOUT.window_w, LAYOUT.room_h)
        new = surf.subsurface(world).copy()
        dx, dy = self.dir
        w, h = world.size
        off_x, off_y = int(-dx * w * e), int(-dy * h * e)
        surf.fill((0, 0, 0), world)
        surf.blit(self.old, (world.x + off_x, world.y + off_y))
        surf.blit(new, (world.x + off_x + dx * w, world.y + off_y + dy * h))


def transition_direction(game_prev: Game, game_now: Game) -> tuple[int, int] | None:
    """Dirección del cambio de sala según los enlaces (o ``None``)."""
    a, b = game_prev.kid.room, game_now.kid.room
    if a == b or not (1 <= a <= len(game_now.level.rooms)):
        return None
    rm = game_now.level.room(a)
    if b == rm.link_e:
        return (1, 0)
    if b == rm.link_w:
        return (-1, 0)
    if b == rm.link_s:
        return (0, 1)
    if b == rm.link_n:
        return (0, -1)
    return None
