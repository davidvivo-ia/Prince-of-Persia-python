"""Caso de uso: avanzar el juego un tick."""

from __future__ import annotations

from pop2026.domain.game import Game, advance
from pop2026.domain.input import InputFrame
from pop2026.domain.ports import Rng


def execute(game: Game, inp: InputFrame, rng: Rng) -> Game:
    """Avanza el juego un tick. Wrapper sobre el dominio para uniformar
    la capa de aplicación.

    Args:
        game: Estado actual.
        inp: Frame de input del jugador.
        rng: Generador determinista.

    Returns:
        Nuevo ``Game`` tras el tick.
    """
    return advance(game, inp, rng)
