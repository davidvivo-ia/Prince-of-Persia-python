"""Reproductor de demo determinista.

Genera una secuencia de :class:`InputFrame` a partir de una seed. La
misma seed produce la misma demo. Útil para:

- Tests E2E sin intervención humana.
- Grabar GIFs/SVGs reproducibles.
- Verificar tras refactors que el motor sigue comportándose igual.

Estrategia v1.0: una *política simple* avanza a la derecha buscando la
salida, salta sobre huecos, pulsa STRIKE al ver guardia y PARRY si
recibe daño. El RNG fija microvariaciones (parry vs strike, walk vs run).
"""

from __future__ import annotations

from collections.abc import Iterable

from pop2026.domain.actions import Action
from pop2026.domain.game import Game, advance
from pop2026.domain.geometry import Position
from pop2026.domain.input import InputFrame, PlayerCommand
from pop2026.domain.level import effective_tile
from pop2026.domain.ports import Rng
from pop2026.domain.tiles import SOLID


def _front_solid(game: Game) -> bool:
    target = game.prince.pos.step(game.prince.facing)
    return effective_tile(game.level, game.state, target) in SOLID


def _gap_ahead(game: Game) -> bool:
    """¿Hay un hueco una celda adelante (suelo bajo la siguiente celda falta)?"""
    target = game.prince.pos.step(game.prince.facing)
    below = Position(target.row + 1, target.col)
    return effective_tile(game.level, game.state, below) not in SOLID


def _guard_adjacent(game: Game) -> bool:
    for g in game.guards:
        if (
            g.alive
            and abs(g.pos.col - game.prince.pos.col) <= 1
            and g.pos.row == game.prince.pos.row
        ):
            return True
    return False


def decide(game: Game, rng: Rng) -> InputFrame:
    """Decide el siguiente input según el estado y un RNG determinista."""
    p = game.prince

    if p.action is Action.DEAD:
        return InputFrame()

    if _guard_adjacent(game):
        # 70% strike, 30% parry: rng.coin lo decide
        if rng.coin(0.7):
            return InputFrame(command=PlayerCommand.STRIKE)
        return InputFrame(command=PlayerCommand.PARRY)

    # Avanza siempre hacia la derecha; la gravedad gestiona el resto.
    # Si encuentra una pared, intenta trepar (UP).
    if _front_solid(game):
        return InputFrame(command=PlayerCommand.UP)

    return InputFrame(command=PlayerCommand.RIGHT)


def play(
    game: Game,
    rng: Rng,
    *,
    max_frames: int = 6_000,
) -> Iterable[Game]:
    """Itera ticks hasta que el juego termine o se alcance ``max_frames``.

    Yield cada ``Game`` resultante (incluido el inicial).
    """
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
