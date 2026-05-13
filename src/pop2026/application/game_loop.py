"""Bucle de juego en la capa de aplicación.

Independiente de pygame: recibe un *callable* que devuelve un
``InputFrame`` por tick y delega la actualización al dominio. La capa
de presentación implementa ese callable leyendo eventos pygame.
"""

from __future__ import annotations

from collections.abc import Callable

from pop2026.domain.game import Game, advance
from pop2026.domain.input import InputFrame
from pop2026.domain.ports import Rng

InputSource = Callable[[Game], InputFrame]
"""Función que, dado el estado, devuelve el siguiente ``InputFrame``."""

OnRender = Callable[[Game], None]
"""Callback opcional al final de cada tick, para renderizar."""


def run(
    game: Game,
    *,
    input_source: InputSource,
    rng: Rng,
    on_render: OnRender | None = None,
    max_frames: int = 0,
) -> Game:
    """Ejecuta el bucle de juego.

    Args:
        game: Estado inicial.
        input_source: Función que entrega el input del tick.
        rng: RNG determinista inyectado.
        on_render: Callback opcional tras cada tick (para presentación).
        max_frames: Si > 0, corta el bucle tras ese número de ticks.

    Returns:
        Estado final del juego (cuando ``running`` es ``False`` o se
        alcanzó ``max_frames``).
    """
    frame = 0
    while game.running:
        inp = input_source(game)
        game = advance(game, inp, rng)
        if on_render is not None:
            on_render(game)
        frame += 1
        if max_frames and frame >= max_frames:
            break
    return game
