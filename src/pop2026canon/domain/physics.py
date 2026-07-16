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
    LAND_DEAD_FALL_DIST,
    LAND_MED_FALL_DIST,
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

    Sólo si está en freefall. Acumula ``fall_dist`` para el cálculo de
    daño al aterrizar.
    """
    if char.action is not Action.IN_FREEFALL:
        return char
    new_y = char.y + char.fall_y
    new_x = char.x + char.fall_x * _forward_sign(char.direction)
    return replace(char, x=new_x, y=new_y, fall_dist=char.fall_dist + char.fall_y)


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


def is_solid_at(
    room: Room,
    col: int,
    row: int,
    broken_floors: frozenset[tuple[int, int, int]] = frozenset(),
) -> bool:
    """``True`` si la celda contiene un tile que SOPORTA peso (se puede
    estar de pie encima / aterrizar en él).

    Las gates con modifier > 0 (parcialmente abiertas) se consideran
    aún bloqueantes salvo que el modifier llegue a 7 (totalmente
    abierta). Un LOOSE cuya losa ya cayó (``broken_floors`` de
    :class:`LevelState`) deja un agujero real.
    """
    if not (0 <= col < SCREEN_TILECOUNT_X and 0 <= row < SCREEN_TILECOUNT_Y):
        return True  # fuera de sala = sólido
    tile, modifier = room.tile_at(col, row)
    if tile is Tile.GATE:
        # Gate sólida salvo cuando está completamente abierta (modifier=7)
        return modifier < 7
    if tile is Tile.LOOSE and (room.id, col, row) in broken_floors:
        return False
    return tile in SOLID


def blocks_body_at(
    room: Room,
    col: int,
    row: int,
    open_gates: frozenset[tuple[int, int, int]] = frozenset(),
) -> bool:
    """``True`` si la celda bloquea el CUERPO horizontalmente.

    Canon POP1: sólo los muros y las gates cerradas cortan el paso.
    Los pilares (PILLAR, BIGPILLAR_*) son decorado en primer plano —
    el kid corre por detrás de ellos.

    ``open_gates`` es el set dinámico de :class:`LevelState` — una gate
    abierta por plate deja de bloquear aunque su modifier estático siga
    siendo 0.
    """
    if not (0 <= col < SCREEN_TILECOUNT_X and 0 <= row < SCREEN_TILECOUNT_Y):
        return True
    tile, modifier = room.tile_at(col, row)
    if tile is Tile.WALL:
        return True
    if tile is Tile.GATE:
        if modifier >= 7:
            return False
        return (room.id, col, row) not in open_gates
    return False


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
        fall_dist=0,
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


# Secuencias de locomoción "con los pies en el suelo" — si el tile bajo
# el char desaparece durante una de ellas, el char cae. Las secuencias
# aéreas (STANDING_JUMP, RUN_JUMP, FALL...) gestionan su propia caída.
_GROUNDED_SEQS: frozenset[int] = frozenset(
    {
        int(Seq.STAND),
        int(Seq.START_RUN),
        int(Seq.RUN),
        int(Seq.STOP_RUN),
        int(Seq.RUNTURN),
        int(Seq.TURN),
        int(Seq.BUMP),
        int(Seq.ENGARDE),
        int(Seq.ADVANCE),
        int(Seq.RETREAT),
        int(Seq.STRIKE),
        int(Seq.BLOCK_STRIKE),
        int(Seq.BLOCK_TO_STRIKE),
        int(Seq.CROUCH),
        int(Seq.STAND_UP_FROM_CROUCH),
        int(Seq.DRAW_SWORD),
        int(Seq.PUT_SWORD_AWAY),
        int(Seq.SOFT_LAND),
        int(Seq.MED_LAND),
        int(Seq.HARD_LAND),
    }
)

# Acciones exentas de colisión horizontal: el cuerpo pasa por celdas
# "sólidas" legítimamente (trepando la cornisa, colgado del borde).
_CLIMB_ACTIONS: frozenset[Action] = frozenset({Action.HANG_STRAIGHT, Action.HANG_CLIMB})


def floor_below_solid(
    level: Level,
    room_id: int,
    col: int,
    row: int,
    broken_floors: frozenset[tuple[int, int, int]] = frozenset(),
) -> bool:
    """¿Hay suelo sólido bajo (col, row)? Mira la sala sur si hace falta."""
    if not (1 <= room_id <= len(level.rooms)):
        return False
    room = level.room(room_id)
    if row + 1 < SCREEN_TILECOUNT_Y:
        return is_solid_at(room, col, row + 1, broken_floors)
    south = room.link_s
    if not south:
        return False  # abismo
    return is_solid_at(level.room(south), col, 0, broken_floors)


def start_fall(char: Char) -> Char:
    """El suelo desapareció bajo los pies: inicia caída libre."""
    return replace(
        char,
        action=Action.IN_FREEFALL,
        curr_seq_id=int(Seq.FALL),
        curr_seq_idx=0,
        fall_x=0,
        fall_y=0,
        fall_dist=0,
    )


def _land(char: Char, *, on_row: int) -> Char:
    """Aterrizaje: decide soft / med (-1 HP) / mortal según la distancia
    de caída acumulada.

    Canon POP1: 1 piso es seguro, 2 pisos cuestan 1 HP, 3 pisos matan.
    Con la poción FLOAT activa el aterrizaje siempre es suave.
    """
    dist = char.fall_dist
    landed = replace(
        char,
        curr_row=max(0, on_row),
        y=0,
        fall_x=0,
        fall_y=0,
        fall_dist=0,
        landed_fall_y=char.fall_y,
    )
    if char.float_ticks > 0 or dist < LAND_MED_FALL_DIST:
        return replace(
            landed,
            action=Action.STAND,
            curr_seq_id=int(Seq.SOFT_LAND),
            curr_seq_idx=0,
        )
    if dist >= LAND_DEAD_FALL_DIST:
        return replace(
            landed,
            hp_curr=0,
            alive=0,
            action=Action.HURT,
            curr_seq_id=int(Seq.HARD_LAND),
            curr_seq_idx=0,
        )
    new_hp = max(0, char.hp_curr - 1)
    if new_hp == 0:
        return replace(
            landed,
            hp_curr=0,
            alive=0,
            action=Action.HURT,
            curr_seq_id=int(Seq.HARD_LAND),
            curr_seq_idx=0,
        )
    return replace(
        landed,
        hp_curr=new_hp,
        action=Action.STAND,
        curr_seq_id=int(Seq.MED_LAND),
        curr_seq_idx=0,
    )


def _die_in_abyss(char: Char) -> Char:
    """Cayó fuera del mapa (sin sala al sur): muerte por caída."""
    return replace(
        char,
        hp_curr=0,
        alive=0,
        action=Action.HURT,
        fall_x=0,
        fall_y=0,
        curr_seq_id=int(Seq.HARD_LAND),
        curr_seq_idx=0,
    )


def step_physics(
    char: Char,
    level: Level,
    *,
    shift_held: bool = False,
    has_feather: bool = False,
    open_gates: frozenset[tuple[int, int, int]] = frozenset(),
    broken_floors: frozenset[tuple[int, int, int]] = frozenset(),
) -> Char:
    """Un tick completo de física para un char.

    Orden de operaciones (canon SDLPoP):

    1. ``play_seq`` — avanza la secuencia (aplica dx/dy).
    2. ``fall_accel`` — acelera fall_y si freefall.
    3. ``fall_speed`` — aplica fall_y/fall_x a x/y.
    4. ``normalize_to_cell`` — redistribuye desbordes sub-tile.
    5. ``cross_border`` — cambio de sala si cruzó.
    6. Colisión horizontal — revierte el movimiento si acabó dentro de
       un tile que bloquea el cuerpo (muro, gate cerrada).
    7. Aterrizaje — freefall que entra en tile sólido aterriza encima
       (soft / med -1HP / mortal según ``fall_y``); sin sala al sur, el
       char muere en el abismo.
    8. ``can_grab`` — engancha cornisa si SHIFT + condiciones.
    9. Walk-off — locomoción de suelo sin suelo debajo inicia caída.

    ``open_gates`` viene de :class:`LevelState` — las gates abiertas
    por plate dejan de bloquear.
    """
    snapshot = char
    char = replace(char, landed_fall_y=0) if char.landed_fall_y else char
    char = play_seq(char)
    char = fall_accel(char, has_feather=has_feather)
    char = fall_speed(char)
    char = normalize_to_cell(char)
    char = cross_border(char, level)

    if not (1 <= char.room <= len(level.rooms)):
        return char
    room = level.room(char.room)

    in_air = char.action in (Action.IN_FREEFALL, Action.IN_MIDAIR)
    in_cell = 0 <= char.curr_row < SCREEN_TILECOUNT_Y and 0 <= char.curr_col < SCREEN_TILECOUNT_X

    # 5b. Head-bump: subiendo en un salto contra un sólido (el techo /
    #     suelo del piso de arriba) → el arco se aplana a la fila previa.
    if (
        char.action is Action.IN_MIDAIR
        and char.alive < 0
        and char.room == snapshot.room
        and char.curr_row < snapshot.curr_row
        and in_cell
        and is_solid_at(room, char.curr_col, char.curr_row, broken_floors)
    ):
        char = replace(char, curr_row=snapshot.curr_row, y=0)

    # 6. Colisión horizontal: acabó dentro de un tile que bloquea el
    #    cuerpo (muro, gate cerrada) → en tierra revierte + BUMP; en el
    #    aire corta el vuelo y cae recto desde la posición previa.
    if (
        in_cell
        and blocks_body_at(room, char.curr_col, char.curr_row, open_gates)
        and char.action not in _CLIMB_ACTIONS
        and char.alive < 0
    ):
        if in_air:
            return start_fall(replace(snapshot, landed_fall_y=0))
        return replace(
            snapshot,
            landed_fall_y=0,
            action=Action.BUMPED,
            curr_seq_id=int(Seq.BUMP),
            curr_seq_idx=0,
            frame=char.frame,
        )

    # 7. Aterrizaje: cayendo y ENTRÓ este tick en un tile sólido →
    #    aterriza encima. La condición de entrada evita falsos
    #    aterrizajes cuando la caída empieza DENTRO de una celda-soporte
    #    (p.ej. walk-off dentro de una plataforma o del hueco del techo).
    if char.action is Action.IN_FREEFALL and char.alive < 0:
        entered_new_cell = (
            char.room != snapshot.room
            or char.curr_row != snapshot.curr_row
            or char.curr_col != snapshot.curr_col
        )
        if (
            in_cell
            and entered_new_cell
            and is_solid_at(room, char.curr_col, char.curr_row, broken_floors)
        ):
            if char.curr_row == 0 and room.link_n:
                # El sólido es el techo de esta sala: el char queda de
                # pie ENCIMA, es decir, en la fila 2 de la sala norte.
                char = replace(char, room=room.link_n)
                return _land(char, on_row=SCREEN_TILECOUNT_Y - 1)
            return _land(char, on_row=char.curr_row - 1)
        if char.curr_row >= SCREEN_TILECOUNT_Y:
            # Bajo la última fila sin link sur: abismo.
            return _die_in_abyss(char)

    # 8. Hang grab
    ledge = can_grab(char, room, shift_held=shift_held)
    if ledge is not None:
        return snap_to_hang(char, *ledge)

    # 9. Walk-off: locomoción de suelo sobre el vacío → cae.
    if (
        char.alive < 0
        and not in_air
        and char.action not in _CLIMB_ACTIONS
        and char.curr_seq_id in _GROUNDED_SEQS
        and in_cell
        and not floor_below_solid(level, char.room, char.curr_col, char.curr_row, broken_floors)
    ):
        return start_fall(char)

    return char
