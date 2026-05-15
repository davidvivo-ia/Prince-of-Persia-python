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
| STAND (sword DRAWN) | SHIFT | ENGARDE (stance) |
| STAND (sword DRAWN) | down | PUT_SWORD_AWAY |
| RUN_JUMP (corriendo) | up | RUN_JUMP |
| RUN_JUMP (corriendo) | sin dir | STOP_RUN |
| HANG_STRAIGHT | up | CLIMB_UP |
| HANG_STRAIGHT | down | RELEASE_LEDGE_LAND |
| ENGARDE | strike | STRIKE |
| ENGARDE | up | BLOCK_STRIKE |
| ENGARDE | forward | ADVANCE |
| ENGARDE | backward | RETREAT |
| ENGARDE | down | PUT_SWORD_AWAY |
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
    from dataclasses import replace

    sword_drawn = char.sword == SwordStatus.DRAWN

    # Delegación al handler ENGARDE cuando ya estamos en stance.
    if char.curr_seq_id == int(Seq.ENGARDE):
        return _handle_engarde(char, cmd)

    # Up + SHIFT (sin sword): desenfundar espada
    if cmd.up and cmd.shift and char.sword == SwordStatus.SHEATHED:
        return _start(replace(char, sword=SwordStatus.DRAWN), Seq.DRAW_SWORD)

    # Con sword DRAWN: SHIFT entra en stance ENGARDE.
    if sword_drawn and cmd.shift and not cmd.up:
        return _start(char, Seq.ENGARDE)

    # Con sword DRAWN: down → envainar.
    if sword_drawn and cmd.down:
        return _start(replace(char, sword=SwordStatus.SHEATHED), Seq.PUT_SWORD_AWAY)

    # Strike key con espada desenvainada
    if cmd.strike and sword_drawn:
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


def _handle_engarde(char: Char, cmd: Command) -> Char:
    """Stance de combate (sword DRAWN, idle en frame 150)."""
    from dataclasses import replace

    sword_drawn = char.sword == SwordStatus.DRAWN
    if not sword_drawn:
        # Si por algún motivo el char pierde la espada, vuelve a STAND
        return _start(char, Seq.STAND)

    # Strike
    if cmd.strike:
        return _start(char, Seq.STRIKE)

    # Block / up — frames 161-164
    if cmd.up:
        return _start(char, Seq.BLOCK_STRIKE)

    # Down — envainar
    if cmd.down:
        return _start(replace(char, sword=SwordStatus.SHEATHED), Seq.PUT_SWORD_AWAY)

    # Forward/backward → advance/retreat según facing
    forward_is_right = _facing_right(char)
    if cmd.right:
        return _start(char, Seq.ADVANCE if forward_is_right else Seq.RETREAT)
    if cmd.left:
        return _start(char, Seq.RETREAT if forward_is_right else Seq.ADVANCE)

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
