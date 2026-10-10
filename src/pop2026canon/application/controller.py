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


def apply_input(char: Char, cmd: Command, level: object | None = None) -> Char:
    """Decide si el char cambia de secuencia según el input.

    Si no aplica ninguna transición, devuelve el char tal cual (la
    secuencia actual seguirá ejecutándose normalmente).

    ``level`` (opcional) habilita los verbos que miran el terreno: el
    paso cuidadoso (no cae por el borde) y colgarse de un borde para
    bajar un piso.
    """
    if char.alive >= 0:
        return char  # muerto, no responde a input

    handler = _DISPATCH.get(char.action)
    if handler is None:
        return char
    if handler is _handle_stand:
        return _handle_stand(char, cmd, level)
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


def _forward_sign(char: Char) -> int:
    return 1 if _facing_right(char) else -1


def _floor_ahead(char: Char, level: object | None) -> bool | None:
    """¿Hay suelo bajo la celda de delante? ``None`` si no hay nivel."""
    if level is None:
        return None
    from pop2026canon.domain.physics import has_floor_at

    col = char.curr_col + _forward_sign(char)
    if not (0 <= col < 10):
        return True  # cambio de sala: lo resuelve la física
    return has_floor_at(level, char.room, col, char.curr_row)  # type: ignore[arg-type]


def _climb_down(char: Char, level: object | None) -> Char | None:
    """↓+SHIFT en un borde: el kid se descuelga y queda colgado de la
    cornisa que pisaba (geometría canon: cuerpo en la celda de delante,
    una fila más abajo, mirando hacia la cornisa). ``None`` si no hay
    borde delante."""
    from dataclasses import replace

    from pop2026canon.domain.physics import is_solid_at

    if level is None:
        return None
    fwd = _forward_sign(char)
    body_col = char.curr_col + fwd
    body_row = char.curr_row + 1
    if not (0 <= body_col < 10 and body_row < 3):
        return None
    room = level.room(char.room)  # type: ignore[attr-defined]
    # Borde: la celda de delante es aire y la que pisa es suelo (la
    # cornisa). La celda del cuerpo puede ser suelo (el piso de abajo):
    # al soltarse aterriza en él de inmediato (canon).
    if is_solid_at(room, body_col, char.curr_row):
        return None
    if not is_solid_at(room, char.curr_col, char.curr_row):
        return None
    return replace(
        char,
        curr_col=body_col,
        curr_row=body_row,
        x=2 if fwd > 0 else 11,
        y=4,
        direction=int(Direction.LEFT) if fwd > 0 else int(Direction.RIGHT),
        action=Action.HANG_STRAIGHT,
        curr_seq_id=int(Seq.GRAB_LEDGE_MIDAIR),
        curr_seq_idx=0,
        fall_x=0,
        fall_y=0,
        fall_dist=0,
    )


def _handle_stand(char: Char, cmd: Command, level: object | None = None) -> Char:
    from dataclasses import replace

    sword_drawn = char.sword == SwordStatus.DRAWN

    # Delegación al handler ENGARDE cuando ya estamos en stance.
    if char.curr_seq_id == int(Seq.ENGARDE):
        return _handle_engarde(char, cmd)

    # Up + SHIFT con espada envainada: desenfundar (sólo si la posee)
    if cmd.up and cmd.shift and char.sword == SwordStatus.SHEATHED and char.has_sword:
        return _start(replace(char, sword=SwordStatus.DRAWN), Seq.DRAW_SWORD)

    # Con sword DRAWN: SHIFT entra en stance ENGARDE.
    if sword_drawn and cmd.shift and not cmd.up and not (cmd.left or cmd.right or cmd.down):
        return _start(char, Seq.ENGARDE)

    # Con sword DRAWN: down → envainar.
    if sword_drawn and cmd.down and not cmd.shift:
        return _start(replace(char, sword=SwordStatus.SHEATHED), Seq.PUT_SWORD_AWAY)

    # Strike key con espada desenvainada
    if cmd.strike and sword_drawn:
        return _start(char, Seq.STRIKE)

    # ↓ + SHIFT: descolgarse del borde (bajar un piso sin daño)
    if cmd.down and cmd.shift:
        hung = _climb_down(char, level)
        if hung is not None:
            return hung
        return char

    horizontal = cmd.right or cmd.left
    wants_right = cmd.right
    facing_ok = (wants_right and _facing_right(char)) or (cmd.left and _facing_left(char))

    if horizontal and not facing_ok:
        return _start(_flip(char), Seq.TURN)

    # ↑ + dirección: salto largo desde parado (canon: libra 2 celdas)
    if horizontal and cmd.up:
        return _start(char, Seq.STANDING_JUMP_FORWARD)

    # SHIFT + dirección: paso cuidadoso — nunca cae por el borde
    if horizontal and cmd.shift:
        if _floor_ahead(char, level) is False:
            return char  # canon: te detienes en el borde
        return _start(char, Seq.STEP)

    # Movimiento horizontal
    if horizontal:
        return _start(char, Seq.START_RUN)

    # Salto vertical (trepar / agarrar cornisa de arriba)
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
    # Secuencias de aterrizaje/frenado en curso: dejarlas terminar —
    # re-arrancarlas cada tick las congelaría en su primer frame.
    if char.curr_seq_id in (
        int(Seq.STOP_RUN),
        int(Seq.SOFT_LAND),
        int(Seq.MED_LAND),
        int(Seq.HARD_LAND),
    ):
        return char

    # Salto con carrerilla — sólo desde el ciclo de carrera real.
    if cmd.up and char.curr_seq_id in (int(Seq.RUN), int(Seq.START_RUN)):
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
