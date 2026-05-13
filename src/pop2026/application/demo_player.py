"""Reproductor de demo determinista.

Genera una secuencia de :class:`InputFrame` a partir de una seed y una
política sencilla, en orden de prioridad:

1. Si hay guardia adyacente: alterna ``STRIKE`` y ``PARRY`` con
   probabilidad influida por el RNG.
2. Si la celda de delante es sólida (pared o cornisa): pide ``UP`` para
   trepar.
3. Si la celda inmediatamente delante es sólida y la de delante-arriba
   también, intenta saltar.
4. En cualquier otro caso, ``RIGHT``.

La misma seed produce la misma demo, lo que permite tests E2E y
reproducción de partidas grabadas.
"""

from __future__ import annotations

from collections.abc import Iterable

from pop2026.domain.actions import Action, duration_ticks
from pop2026.domain.game import Game, advance
from pop2026.domain.geometry import Facing, Position
from pop2026.domain.input import InputFrame, PlayerCommand
from pop2026.domain.level import Level, LevelState, effective_tile
from pop2026.domain.ports import Rng
from pop2026.domain.tiles import SOLID, Tile


def _front_solid(game: Game) -> bool:
    target = game.prince.pos.step(game.prince.facing)
    return effective_tile(game.level, game.state, target) in SOLID


def _can_climb_up_from(level: Level, state: LevelState, pos: Position, facing: Facing) -> bool:
    """¿Hay una cornisa accesible delante para trepar desde ``pos``?"""
    fwd = pos.step(facing)
    above_fwd = fwd.shifted(drow=-1)
    above = pos.shifted(drow=-1)
    landing = fwd.shifted(drow=-2)
    eff = effective_tile
    return (
        eff(level, state, above_fwd) in SOLID
        and eff(level, state, fwd) not in SOLID
        and eff(level, state, above) not in SOLID
        and eff(level, state, landing) not in SOLID
    )


def _can_climb_up(game: Game) -> bool:
    return _can_climb_up_from(game.level, game.state, game.prince.pos, game.prince.facing)


def _climb_after_step(game: Game) -> bool:
    """¿Tendrá oportunidad de trepar tras avanzar un paso?"""
    next_pos = game.prince.pos.step(game.prince.facing)
    return _can_climb_up_from(game.level, game.state, next_pos, game.prince.facing)


def _front_is_spike(game: Game) -> bool:
    target = game.prince.pos.step(game.prince.facing)
    return effective_tile(game.level, game.state, target) is Tile.SPIKES


def _gap_under_front(game: Game) -> bool:
    """¿No hay suelo bajo la celda inmediatamente delante?"""
    target = game.prince.pos.step(game.prince.facing)
    below = Position(target.row + 1, target.col)
    return effective_tile(game.level, game.state, below) not in SOLID


def _guard_adjacent(game: Game) -> bool:
    return any(
        g.alive and abs(g.pos.col - game.prince.pos.col) <= 1 and g.pos.row == game.prince.pos.row
        for g in game.guards
    )


def decide(game: Game, rng: Rng) -> InputFrame:
    """Decide el siguiente input según el estado y un RNG determinista."""
    p = game.prince

    if p.action is Action.DEAD:
        return InputFrame()

    # Si está colgado, sube a la repisa para no quedarse pendiendo.
    if p.action is Action.HANG:
        return InputFrame(command=PlayerCommand.UP)

    if _guard_adjacent(game) and p.has_sword:
        if rng.coin(0.7):
            return InputFrame(command=PlayerCommand.STRIKE)
        return InputFrame(command=PlayerCommand.PARRY)

    # Pinchos delante: saltar para evitar caer encima con velocidad.
    if _front_is_spike(game):
        return InputFrame(command=PlayerCommand.JUMP)

    # Cornisa accesible: trepar.
    if _can_climb_up(game):
        return InputFrame(command=PlayerCommand.UP)

    # Está a punto de completar un paso y aterrizará en una cornisa: pide UP
    # justo en el tick previo para que la transición CLIMB_UP encaje en el
    # boundary de la acción.
    if (
        p.action in (Action.RUN, Action.WALK)
        and p.ticks_in_action == duration_ticks(p.action) - 1
        and _climb_after_step(game)
    ):
        return InputFrame(command=PlayerCommand.UP)

    # Pared inmediata: probar salto vertical.
    if _front_solid(game):
        return InputFrame(command=PlayerCommand.JUMP)

    # Hueco delante: saltar (salto direccional si veníamos corriendo).
    if _gap_under_front(game):
        if p.action in (Action.RUN, Action.WALK):
            return InputFrame(command=PlayerCommand.JUMP)
        # Aún no corre: empieza a correr para llegar al salto con velocidad.
        return InputFrame(command=PlayerCommand.RIGHT)

    return InputFrame(command=PlayerCommand.RIGHT)


def play(
    game: Game,
    rng: Rng,
    *,
    max_frames: int = 6_000,
) -> Iterable[Game]:
    """Itera ticks hasta que el juego termine o se alcance ``max_frames``."""
    yield game
    for _ in range(max_frames):
        if not game.running:
            return
        inp = decide(game, rng)
        game = advance(game, inp, rng)
        yield game


def run_to_completion(
    game: Game,
    rng: Rng,
    *,
    max_frames: int = 6_000,
) -> Game:
    """Ejecuta la demo y devuelve el último estado."""
    last = game
    for g in play(game, rng, max_frames=max_frames):
        last = g
    return last
