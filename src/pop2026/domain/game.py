"""Agregado raíz: ``Game``. Orquesta príncipe, guardias y nivel.

Una llamada a :func:`advance` representa **un tick lógico** (1/60 s
nominal). El reloj del juego decrece, las entidades se actualizan, las
interacciones con tiles (pociones, placas, gates, spikes) se aplican y
el resultado se devuelve como un nuevo ``Game`` inmutable.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import IntEnum

from pop2026.domain import combat, guard
from pop2026.domain import physics_prince as prince_module
from pop2026.domain.actions import Action
from pop2026.domain.geometry import Position
from pop2026.domain.guard import Guard
from pop2026.domain.input import InputFrame
from pop2026.domain.level import Level, LevelState, effective_tile
from pop2026.domain.physics_prince import PhysicsPrince
from pop2026.domain.physics_prince import initial as prince_initial
from pop2026.domain.ports import Rng
from pop2026.domain.tiles import Tile

DEFAULT_TIME_LIMIT_TICKS: int = 60 * 60 * 60
"""60 minutos por 60 segundos por 60 ticks."""


class GameStatus(IntEnum):
    """Estado global del juego."""

    PLAYING = 0
    WON = 1
    LOST_DIED = 2
    LOST_TIMEOUT = 3


@dataclass(frozen=True, slots=True)
class Game:
    """Estado completo del juego en un tick."""

    level: Level
    state: LevelState
    prince: PhysicsPrince
    guards: tuple[Guard, ...]
    time_left: int
    status: GameStatus = GameStatus.PLAYING
    level_index: int = 1
    hits_dealt_total: int = 0
    hits_received_total: int = 0

    @property
    def running(self) -> bool:
        """``True`` si seguimos jugando."""
        return self.status is GameStatus.PLAYING


def new_game(
    level: Level,
    *,
    level_index: int = 1,
    time_limit: int = DEFAULT_TIME_LIMIT_TICKS,
    starting_hp: int = 3,
) -> Game:
    """Construye una ``Game`` lista para jugar a partir de un ``Level``."""
    p = prince_initial(level.prince_spawn, hp=starting_hp, max_hp=starting_hp)
    gs = tuple(
        Guard(
            pos=pos,
            skill=max(1, skill),
            hp=(2 if skill == -1 else 2 + skill),
            is_skeleton=skill == -1,
        )
        for pos, skill in level.guard_spawns
    )
    # El tiempo del nivel manda si está definido; si no, el argumento.
    effective_time = level.time_limit_ticks if level.time_limit_ticks is not None else time_limit
    return Game(
        level=level,
        state=LevelState(),
        prince=p,
        guards=gs,
        time_left=effective_time,
        level_index=level_index,
    )


def _nearest_gate(level: Level, plate: Position) -> Position | None:
    """Encuentra la gate más cercana (Manhattan) en el nivel."""
    best: Position | None = None
    best_d = 10**9
    for r in range(level.rows):
        for c in range(level.cols):
            if level.grid[r][c] is Tile.GATE:
                d = abs(r - plate.row) + abs(c - plate.col)
                if d < best_d:
                    best_d = d
                    best = Position(r, c)
    return best


def _process_tile_interactions(g: Game) -> Game:
    """Procesa pociones, placas, loose-floors y exit donde está el príncipe."""
    p = g.prince
    state = g.state
    standing_tile = effective_tile(g.level, state, p.pos)

    if standing_tile is Tile.EXIT:
        return replace(g, status=GameStatus.WON)

    if standing_tile is Tile.POTION_HEAL and p.pos not in state.consumed_potions:
        p = p.with_heal(1)
        state = state.with_potion_consumed(p.pos)

    if standing_tile is Tile.POTION_POISON and p.pos not in state.consumed_potions:
        p = p.with_damage(1)
        state = state.with_potion_consumed(p.pos)

    if standing_tile is Tile.SWORD and not p.has_sword:
        from dataclasses import replace as _r

        p = _r(p, has_sword=True)
        state = state.with_potion_consumed(p.pos)

    if standing_tile is Tile.POTION_MAXHP and p.pos not in state.consumed_potions:
        p = p.with_max_hp_bonus(1)
        state = state.with_potion_consumed(p.pos)

    # placas: cualquier actor pisándolas activa la gate más cercana
    pressed: set[Position] = set()
    actors = [p.pos, *(gd.pos for gd in g.guards if gd.alive)]
    for pos in actors:
        if effective_tile(g.level, state, pos) is Tile.PRESSURE:
            pressed.add(pos)
            gate = _nearest_gate(g.level, pos)
            if gate is not None:
                state = state.with_open(gate)
    state = state.with_pressed(frozenset(pressed))

    # loose-floor bajo el príncipe: si lo pisa, se rompe
    below = p.pos.shifted(drow=1)
    if g.level.tile_at(below) is Tile.LOOSE_FLOOR and below not in state.fallen_floors:
        state = state.with_floor_fallen(below)

    # spikes: si está parado sobre celda con spikes con caída previa, muere
    from pop2026.domain.physics import SPIKE_LETHAL_VY

    if standing_tile is Tile.SPIKES and p.last_impact_vy >= SPIKE_LETHAL_VY:
        p = replace(p, hp=0, action=Action.DEAD, ticks_in_action=0)

    return replace(g, prince=p, state=state)


def _check_game_over(g: Game) -> Game:
    """Comprueba muerte o timeout."""
    if g.prince.action is Action.DEAD or g.prince.hp <= 0:
        return replace(g, status=GameStatus.LOST_DIED)
    if g.time_left <= 0:
        return replace(g, status=GameStatus.LOST_TIMEOUT)
    return g


def advance(g: Game, inp: InputFrame, rng: Rng) -> Game:
    """Avanza el juego un tick lógico.

    Args:
        g: Estado actual.
        inp: Frame de input del jugador.
        rng: Generador determinista (ver :class:`pop2026.domain.ports.Rng`).

    Returns:
        Nuevo ``Game`` tras el tick.
    """
    if not g.running:
        return g

    # 1. Step físico del príncipe
    new_prince = prince_module.step(g.prince, g.level, g.state, inp)

    # 2. Step de cada guardia
    new_guards = tuple(guard.step(gd, g.level, g.state, new_prince.pos, rng) for gd in g.guards)

    g2 = replace(g, prince=new_prince, guards=new_guards, time_left=max(0, g.time_left - 1))

    # 3. Combate (resuelve hits si STRIKE/PARRY activos)
    cr = combat.resolve(g2.prince, g2.guards)
    g2 = replace(
        g2,
        prince=cr.prince,
        guards=cr.guards,
        hits_dealt_total=g2.hits_dealt_total + cr.hits_dealt,
        hits_received_total=g2.hits_received_total + cr.hits_received,
    )

    # 4. Si matamos al primer guardia, el príncipe coge la espada
    if cr.hits_dealt > 0 and not g2.prince.has_sword:
        any_dead_now = any(not gd.alive for gd in g2.guards)
        if any_dead_now:
            g2 = replace(g2, prince=replace(g2.prince, has_sword=True))

    # 5. Interacciones tile (placas, pociones, loose-floor, exit, spikes)
    g2 = _process_tile_interactions(g2)

    # 6. Fin de partida
    return _check_game_over(g2)
