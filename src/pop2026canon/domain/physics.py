"""Física tile-based canónica.

Tres responsabilidades:

1. ``play_seq`` — avanza la secuencia de un char un tick lógico,
   aplicando todos los acts intermedios hasta el próximo FRAME.
2. ``fall_accel`` + ``fall_speed`` — gravedad discreta canónica
   (+3/tick hasta MAX=33).
3. ``check_grab`` — detección de cornisa con SHIFT pulsado.

Más: ``normalize_to_cell`` (redistribuir sub-tile a celda),
``cross_border`` (cambio de sala), ``check_collision`` (revertir
movimientos inválidos).

Ver `docs/design/03-tile-physics.md` para el modelo completo.
"""

from __future__ import annotations

from dataclasses import replace

from pop2026canon.domain.actions import Action, Direction, Seq
from pop2026canon.domain.chars import Char
from pop2026canon.domain.constants import (
    FALLING_SPEED_ACCEL,
    FALLING_SPEED_ACCEL_FEATHER,
    FALLING_SPEED_MAX,
    FALLING_SPEED_MAX_FEATHER,
    GRAB_FALL_Y_THRESHOLD,
    SCREEN_TILECOUNT_X,
    SCREEN_TILECOUNT_Y,
    TILE_SIZE_X,
    TILE_SIZE_Y,
)
from pop2026canon.domain.level import Level
from pop2026canon.domain.room import Room
from pop2026canon.domain.seqtbl import ActKind, get
from pop2026canon.domain.tiles import SOLID, Tile


def _forward_sign(direction: int) -> int:
    """Convierte la representación canónica de direction a signo ±1.

    Canon SDLPoP: ``dir_0_right=0``, ``dir_FF_left=-1``. Esto permite
    comparaciones rápidas en 6502 pero `dx * direction` no funciona
    para right (0 anula). Esta función traduce a +1/-1 utilizable.
    """
    return -1 if direction == int(Direction.LEFT) else 1


# ---------------------------------------------------------------------------
# Sequence runner
# ---------------------------------------------------------------------------


def play_seq(char: Char) -> Char:
    """Avanza la secuencia del char hasta el próximo ``FRAME``.

    Aplica todos los acts intermedios (DX, DY, SND, SETUP, SET_FALL,
    JMP, NOP) y termina cuando encuentra el siguiente ``FRAME``.
    Devuelve el nuevo estado del char.

    Si el char está muerto (``alive >= 0``) no avanza.
    """
    if char.alive >= 0:
        return char

    seq_id = char.curr_seq_id
    idx = char.curr_seq_idx
    sequence = get(seq_id)

    new_x = char.x
    new_y = char.y
    new_action = char.action
    new_fall_x = char.fall_x
    new_fall_y = char.fall_y
    new_seq_id = seq_id

    # Tope de iteraciones — protege contra bucles JMP sin FRAME.
    max_iters = 256
    for _ in range(max_iters):
        if idx >= len(sequence):
            # Secuencia agotada sin FRAME → vuelve a STAND como fallback.
            new_seq_id = int(Seq.STAND)
            sequence = get(new_seq_id)
            idx = 0
            continue

        act = sequence[idx]

        if act.kind is ActKind.FRAME:
            return replace(
                char,
                frame=act.arg,
                x=new_x,
                y=new_y,
                action=new_action,
                fall_x=new_fall_x,
                fall_y=new_fall_y,
                curr_seq_id=new_seq_id,
                curr_seq_idx=idx + 1,
            )

        if act.kind is ActKind.DX:
            new_x += act.arg * _forward_sign(char.direction)
        elif act.kind is ActKind.DY:
            new_y += act.arg
        elif act.kind is ActKind.SND:
            # Sonido: ignorado por el dominio puro; el adaptador audio lo
            # detecta vía transitions diff.
            pass
        elif act.kind is ActKind.SET_FALL:
            new_fall_x = act.arg
            new_fall_y = act.arg2
        elif act.kind is ActKind.SETUP:
            new_action = Action(act.arg)
        elif act.kind is ActKind.JMP:
            new_seq_id = act.arg
            sequence = get(new_seq_id)
            idx = -1  # se incrementa al final, queda en 0
        elif act.kind is ActKind.NOP:
            pass

        idx += 1

    # Si por algún motivo no encontramos FRAME en 256 iteraciones,
    # devolvemos el char sin cambios (defensa).
    return char


def start_seq(char: Char, seq_id: int | Seq) -> Char:
    """Reinicia el char en una nueva secuencia (idx 0)."""
    return replace(char, curr_seq_id=int(seq_id), curr_seq_idx=0)


# ---------------------------------------------------------------------------
# Caída libre — gravedad canónica
# ---------------------------------------------------------------------------


def fall_accel(char: Char, *, has_feather: bool = False) -> Char:
    """Acelera ``fall_y`` si el char está en freefall.

    Canon: +3 por tick hasta MAX=33. Bajo poción de pluma: +1 hasta 4.
    """
    if char.action is not Action.IN_FREEFALL:
        return char
    accel = FALLING_SPEED_ACCEL_FEATHER if has_feather else FALLING_SPEED_ACCEL
    max_speed = FALLING_SPEED_MAX_FEATHER if has_feather else FALLING_SPEED_MAX
    new_fall_y = min(max_speed, char.fall_y + accel)
    return replace(char, fall_y=new_fall_y)


def fall_speed(char: Char) -> Char:
    """Aplica ``fall_y`` a ``char.y`` y ``fall_x`` a ``char.x``.

    Sólo si está en freefall.
    """
    if char.action is not Action.IN_FREEFALL:
        return char
    new_y = char.y + char.fall_y
    new_x = char.x + char.fall_x * _forward_sign(char.direction)
    return replace(char, x=new_x, y=new_y)


# ---------------------------------------------------------------------------
# Normalización sub-tile → celda
# ---------------------------------------------------------------------------


def normalize_to_cell(char: Char) -> Char:
    """Redistribuye desbordes de sub-tile a ``curr_col`` / ``curr_row``.

    Después de aplicar dx/dy, ``x`` puede salirse de [0, TILE_SIZE_X-1]
    y ``y`` de [0, TILE_SIZE_Y-1]. Esta función mueve los excesos a las
    coordenadas de celda.
    """
    col = char.curr_col
    x = char.x
    row = char.curr_row
    y = char.y

    while x >= TILE_SIZE_X:
        x -= TILE_SIZE_X
        col += 1
    while x < 0:
        x += TILE_SIZE_X
        col -= 1
    while y >= TILE_SIZE_Y:
        y -= TILE_SIZE_Y
        row += 1
    while y < 0:
        y += TILE_SIZE_Y
        row -= 1

    return replace(char, curr_col=col, curr_row=row, x=x, y=y)


# ---------------------------------------------------------------------------
# Cambio de sala
# ---------------------------------------------------------------------------


def cross_border(char: Char, level: Level) -> Char:
    """Si el char salió por un borde de la sala, lo mueve a la sala
    vecina (o lo deja bumped si no hay link).

    Caída al sur sin link → continúa hacia un abismo (lo gestiona la
    capa de muerte por caída con MAX_FALL_TILES).
    """
    if not (1 <= char.room <= len(level.rooms)):
        return char  # estado inválido, no tocar

    room = level.room(char.room)

    if char.curr_col < 0:
        target = room.link_w
        if target == 0:
            return _bumped(char, side=-1)
        return replace(char, room=target, curr_col=SCREEN_TILECOUNT_X - 1)

    if char.curr_col >= SCREEN_TILECOUNT_X:
        target = room.link_e
        if target == 0:
            return _bumped(char, side=1)
        return replace(char, room=target, curr_col=0)

    if char.curr_row < 0:
        target = room.link_n
        if target == 0:
            return _bumped(char, side=0)
        return replace(char, room=target, curr_row=SCREEN_TILECOUNT_Y - 1)

    if char.curr_row >= SCREEN_TILECOUNT_Y:
        target = room.link_s
        if target == 0:
            # Caída al vacío. El char sigue cayendo; el límite lo
            # impone la lógica de muerte por caída a >10 tiles.
            return char
        return replace(char, room=target, curr_row=0)

    return char


def _bumped(char: Char, *, side: int) -> Char:
    """El char chocó contra pared (no había link en esa dirección).

    Devuelve el char con `action=BUMPED` y posición revertida al borde.
    `side`: +1 east, -1 west, 0 north.
    """
    new_col = char.curr_col
    new_row = char.curr_row
    if side > 0:
        new_col = SCREEN_TILECOUNT_X - 1
    elif side < 0:
        new_col = 0
    elif side == 0:
        new_row = 0
    return replace(
        char,
        curr_col=new_col,
        curr_row=new_row,
        x=TILE_SIZE_X // 2,
        y=TILE_SIZE_Y // 2,
        action=Action.BUMPED,
        fall_x=0,
        fall_y=0,
    )


# ---------------------------------------------------------------------------
# Colisión con tiles sólidos
# ---------------------------------------------------------------------------


def is_solid_at(room: Room, col: int, row: int) -> bool:
    """``True`` si la celda contiene un tile que bloquea el cuerpo.

    Las gates con modifier > 0 (parcialmente abiertas) se consideran
    aún bloqueantes salvo que el modifier llegue a 7 (totalmente
    abierta) — pendiente de gate state machine en FASE 3.4.
    """
    if not (0 <= col < SCREEN_TILECOUNT_X and 0 <= row < SCREEN_TILECOUNT_Y):
        return True  # fuera de sala = sólido
    tile, modifier = room.tile_at(col, row)
    if tile is Tile.GATE:
        # Gate sólida salvo cuando está completamente abierta (modifier=7)
        return modifier < 7
    return tile in SOLID


def check_floor_below(room: Room, col: int, row: int) -> bool:
    """``True`` si la celda (row+1, col) es sólida — hay suelo debajo."""
    return is_solid_at(room, col, row + 1)


# ---------------------------------------------------------------------------
# Hang grab (CHECK_GRAB canónico — exige SHIFT)
# ---------------------------------------------------------------------------


def can_grab(char: Char, room: Room, *, shift_held: bool) -> tuple[int, int] | None:
    """Detecta si el char puede engancharse a una cornisa.

    Replica canon (`seg006.c::check_grab`):
    - SHIFT debe estar pulsado.
    - El char debe estar en freefall.
    - ``fall_y`` debe ser < ``GRAB_FALL_Y_THRESHOLD`` (32).
    - Tiene que haber un tile sólido enfrente a la altura de la cabeza.
    - El tile encima de ese sólido debe ser no-sólido (espacio para la
      cabeza).

    Devuelve ``(ledge_col, ledge_row)`` si se puede agarrar; ``None`` si no.
    """
    if not shift_held:
        return None
    if char.action is not Action.IN_FREEFALL:
        return None
    if char.fall_y >= GRAB_FALL_Y_THRESHOLD:
        return None
    if char.alive >= 0:
        return None

    forward_col = char.curr_col + _forward_sign(char.direction)
    head_row = char.curr_row - 1

    if forward_col < 0 or forward_col >= SCREEN_TILECOUNT_X:
        return None
    if head_row < 0:
        return None

    # La cornisa: tile sólido a la altura de la cabeza, en el lado al
    # que mira el char.
    ledge_tile_row = char.curr_row  # cell con sólido (el "borde")
    if not is_solid_at(room, forward_col, ledge_tile_row):
        return None
    # Encima del ledge debe haber espacio (head_row no sólido)
    if is_solid_at(room, forward_col, head_row):
        return None

    return forward_col, ledge_tile_row


def snap_to_hang(char: Char, ledge_col: int, ledge_row: int) -> Char:
    """Coloca el char colgando de la cornisa: vel=0, acción HANG_STRAIGHT."""
    # Posición canónica: el char queda en la celda contigua al ledge,
    # mismo row, con sub-tile cerca del borde de la pared.
    fwd = _forward_sign(char.direction)
    body_col = ledge_col - fwd
    snap_x = TILE_SIZE_X - 4 if fwd > 0 else 4
    snap_y = 0  # cabeza tocando el techo de la celda (parte alta)

    return replace(
        char,
        curr_col=body_col,
        curr_row=ledge_row,
        x=snap_x,
        y=snap_y,
        action=Action.HANG_STRAIGHT,
        fall_x=0,
        fall_y=0,
        curr_seq_id=int(Seq.GRAB_LEDGE_MIDAIR),
        curr_seq_idx=0,
    )


def hang_shuffle(char: Char, room: Room, *, direction: int) -> Char:
    """Mueve al char colgado lateralmente una celda en `direction` (±1).

    Sólo aplica si está en HANG_STRAIGHT y la cornisa adyacente sigue siendo
    una pared sólida arriba con vacío al lado para que el cuerpo cuelgue.
    Si no se puede shuffle, devuelve el char tal cual.
    """
    if char.action is not Action.HANG_STRAIGHT:
        return char
    sign = 1 if direction > 0 else -1
    new_col = char.curr_col + sign
    if not (0 <= new_col < SCREEN_TILECOUNT_X):
        return char
    # La celda superior contigua sigue siendo sólida (techo de la pared).
    grab_col = new_col + _forward_sign(char.direction)
    if not (0 <= grab_col < SCREEN_TILECOUNT_X):
        return char
    above_row = char.curr_row - 1
    if above_row >= 0 and not is_solid_at(room, grab_col, above_row):
        # Ya no hay cornisa por encima en la dirección de cuelgue
        return char
    return replace(char, curr_col=new_col, x=TILE_SIZE_X // 2)


def release_hang(char: Char) -> Char:
    """Suelta la cornisa: pasa a IN_FREEFALL con fall_y inicial 0."""
    if char.action is not Action.HANG_STRAIGHT:
        return char
    return replace(
        char,
        action=Action.IN_FREEFALL,
        curr_seq_id=int(Seq.FALL),
        curr_seq_idx=0,
        fall_x=0,
        fall_y=0,
    )


# ---------------------------------------------------------------------------
# Step físico completo (orden canónico por tick)
# ---------------------------------------------------------------------------


def step_physics(
    char: Char,
    level: Level,
    *,
    shift_held: bool = False,
    has_feather: bool = False,
) -> Char:
    """Un tick completo de física para un char.

    Orden de operaciones (canon SDLPoP):

    1. ``play_seq`` — avanza la secuencia (aplica dx/dy).
    2. ``fall_accel`` — acelera fall_y si freefall.
    3. ``fall_speed`` — aplica fall_y/fall_x a x/y.
    4. ``normalize_to_cell`` — redistribuye desbordes sub-tile.
    5. ``cross_border`` — cambio de sala si cruzó.
    6. ``can_grab`` — engancha cornisa si SHIFT + condiciones.
    """
    char = play_seq(char)
    char = fall_accel(char, has_feather=has_feather)
    char = fall_speed(char)
    char = normalize_to_cell(char)
    char = cross_border(char, level)

    if 1 <= char.room <= len(level.rooms):
        room = level.room(char.room)
        ledge = can_grab(char, room, shift_held=shift_held)
        if ledge is not None:
            char = snap_to_hang(char, *ledge)

    return char
