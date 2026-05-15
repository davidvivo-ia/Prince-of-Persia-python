"""Controller — traduce input del jugador a transiciones de secuencia.

El input es ``Command`` (booleanos de teclas pulsadas este tick). El
controller decide si el ``Char`` cambia de seq según su estado actual
(``action``). Aproximación a `control.c` de SDLPoP — las transiciones
canónicas son:

| Estado | Input | Nueva secuencia |
|---|---|---|
| STAND | right/left misma dir | START_RUN |
| STAND | right/left dir opuesta | TURN |
| STAND | up (sin SHIFT) | STANDING_JUMP |
| STAND | up + SHIFT | DRAW_SWORD |
| STAND | down | CROUCH |
| STAND | SHIFT (con sword) | engarde — TODO |
| RUN_JUMP (corriendo) | up | RUN_JUMP |
| RUN_JUMP (corriendo) | sin dir | STOP_RUN |
| HANG_STRAIGHT | up | CLIMB_UP |
| HANG_STRAIGHT | down | RELEASE_LEDGE_LAND |
| (sword drawn) | strike key | STRIKE |
| (sword drawn) | down | sheathe — TODO |
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from pop2026canon.domain.actions import Action, Direction, Seq, SwordStatus
from pop2026canon.domain.chars import Char


@dataclass(frozen=True, slots=True)
class Command:
    """Input del jugador este tick (booleanos de teclas pulsadas)."""

    left: bool = False
    right: bool = False
    up: bool = False
    down: bool = False
    shift: bool = False
    strike: bool = False
    """Tecla de ataque (canon: tecla "A" del DOS, o spacebar)."""

    def any_dir(self) -> bool:
        return self.left or self.right or self.up or self.down


def apply_input(char: Char, cmd: Command) -> Char:
    """Decide si el char cambia de secuencia según el input.

    Si no aplica ninguna transición, devuelve el char tal cual (la
    secuencia actual seguirá ejecutándose normalmente).
    """
    if char.alive >= 0:
        return char  # muerto, no responde a input

    handler = _DISPATCH.get(char.action)
    if handler is None:
        return char
    return handler(char, cmd)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _start(char: Char, seq: Seq | int) -> Char:
    from dataclasses import replace

    return replace(char, curr_seq_id=int(seq), curr_seq_idx=0)


def _facing_right(char: Char) -> bool:
    return char.direction == int(Direction.RIGHT)


def _facing_left(char: Char) -> bool:
    return char.direction == int(Direction.LEFT)


def _flip(char: Char) -> Char:
    from dataclasses import replace

    new_dir = int(Direction.LEFT) if _facing_right(char) else int(Direction.RIGHT)
    return replace(char, direction=new_dir)


# ---------------------------------------------------------------------------
# Handlers por acción
# ---------------------------------------------------------------------------


def _handle_stand(char: Char, cmd: Command) -> Char:
    # Up + SHIFT: desenfundar espada
    if cmd.up and cmd.shift and char.sword == SwordStatus.SHEATHED:
        from dataclasses import replace

        return _start(replace(char, sword=SwordStatus.DRAWN), Seq.DRAW_SWORD)

    # Strike key con espada desenvainada
    if cmd.strike and char.sword == SwordStatus.DRAWN:
        return _start(char, Seq.STRIKE)

    # Movimiento horizontal
    if cmd.right:
        if _facing_right(char):
            return _start(char, Seq.START_RUN)
        return _start(_flip(char), Seq.TURN)

    if cmd.left:
        if _facing_left(char):
            return _start(char, Seq.START_RUN)
        return _start(_flip(char), Seq.TURN)

    # Salto vertical
    if cmd.up:
        return _start(char, Seq.STANDING_JUMP)

    # Agacharse
    if cmd.down:
        return _start(char, Seq.CROUCH)

    return char


def _handle_running(char: Char, cmd: Command) -> Char:
    # Salto con carrerilla
    if cmd.up:
        return _start(char, Seq.RUN_JUMP)

    # Sin input direccional → parar
    if not cmd.right and not cmd.left:
        return _start(char, Seq.STOP_RUN)

    # Cambio de dirección al correr
    if cmd.right and _facing_left(char):
        return _start(_flip(char), Seq.TURN)
    if cmd.left and _facing_right(char):
        return _start(_flip(char), Seq.TURN)

    return char


def _handle_hang_straight(char: Char, cmd: Command) -> Char:
    # Trepar
    if cmd.up:
        return _start(char, Seq.CLIMB_UP)
    # Soltarse
    if cmd.down:
        return _start(char, Seq.RELEASE_LEDGE_LAND)
    return char


def _handle_freefall(char: Char, cmd: Command) -> Char:
    # No hay transiciones por input en freefall — el grab se gestiona
    # en physics.check_grab() con SHIFT como input.
    return char


def _handle_turn(char: Char, cmd: Command) -> Char:
    # En TURN no aceptamos input adicional hasta que la seq termine.
    return char


_DISPATCH: dict[Action, Callable[[Char, Command], Char]] = {
    Action.STAND: _handle_stand,
    Action.RUN_JUMP: _handle_running,
    Action.HANG_STRAIGHT: _handle_hang_straight,
    Action.HANG_CLIMB: _handle_hang_straight,
    Action.IN_FREEFALL: _handle_freefall,
    Action.IN_MIDAIR: _handle_freefall,
    Action.TURN: _handle_turn,
}
