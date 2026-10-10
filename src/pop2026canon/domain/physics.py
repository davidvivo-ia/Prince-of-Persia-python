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

from dataclasses import dataclass, replace

from pop2026canon.domain.actions import Action, Direction, Seq, SwordStatus
from pop2026canon.domain.chars import Char, CharId
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
    new_direction = char.direction

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
                direction=new_direction,
            )

        if act.kind is ActKind.DX:
            new_x += act.arg * _forward_sign(new_direction)
        elif act.kind is ActKind.FLIP:
            new_direction = (
                int(Direction.LEFT)
                if new_direction == int(Direction.RIGHT)
                else int(Direction.RIGHT)
            )
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

    Geometría canon: el char OCUPA la celda del suelo que pisa, así que
    muros y gates cerradas se evalúan en su propia celda. Los pilares
    (PILLAR, BIGPILLAR_*) son decorado en primer plano — se pasa por
    detrás. ``open_gates`` es el set dinámico de :class:`LevelState`.
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


def has_floor_at(
    level: Level,
    room_id: int,
    col: int,
    row: int,
    broken_floors: frozenset[tuple[int, int, int]] = frozenset(),
) -> bool:
    """¿La celda (col, row) es suelo (canon ``tile_is_floor``)? Un char
    de pie siempre está EN una celda de suelo; si deja de serlo, cae."""
    if not (1 <= room_id <= len(level.rooms)):
        return False
    if not (0 <= col < SCREEN_TILECOUNT_X and 0 <= row < SCREEN_TILECOUNT_Y):
        return False
    return is_solid_at(level.room(room_id), col, row, broken_floors)


# ---------------------------------------------------------------------------
# Celdas vecinas a través de salas (canon ``get_tile``: col fuera de rango
# → sala este/oeste; luego fila fuera de rango → sala norte/sur)
# ---------------------------------------------------------------------------


def resolve_cell(level: Level, room_id: int, col: int, row: int) -> tuple[int, int, int] | None:
    """Resuelve ``(col, row)`` relativos a ``room_id`` (pueden salirse de
    la sala en una celda) a ``(room, col, row)`` dentro de una sala real.
    ``None`` si no hay sala en esa dirección."""
    if not (1 <= room_id <= len(level.rooms)):
        return None
    room = level.room(room_id)
    if col < 0:
        room_id, col = room.link_w, col + SCREEN_TILECOUNT_X
    elif col >= SCREEN_TILECOUNT_X:
        room_id, col = room.link_e, col - SCREEN_TILECOUNT_X
    if not (1 <= room_id <= len(level.rooms)) or not (0 <= col < SCREEN_TILECOUNT_X):
        return None
    room = level.room(room_id)
    if row < 0:
        room_id, row = room.link_n, row + SCREEN_TILECOUNT_Y
    elif row >= SCREEN_TILECOUNT_Y:
        room_id, row = room.link_s, row - SCREEN_TILECOUNT_Y
    if not (1 <= room_id <= len(level.rooms)) or not (0 <= row < SCREEN_TILECOUNT_Y):
        return None
    return room_id, col, row


@dataclass(frozen=True, slots=True)
class Terrain:
    """Nivel + estado dinámico que determina qué celdas son suelo, aire o
    cornisa: gates abiertas (``LevelState.open_gates``) y losas sueltas
    ya caídas (``LevelState.fallen_floors``)."""

    level: Level
    open_gates: frozenset[tuple[int, int, int]] = frozenset()
    broken_floors: frozenset[tuple[int, int, int]] = frozenset()

    def cell(self, room_id: int, col: int, row: int) -> tuple[int, Tile, int] | None:
        """``(room, tile, modifier)`` de la celda resuelta, o ``None``."""
        cell = resolve_cell(self.level, room_id, col, row)
        if cell is None:
            return None
        rid, c, r = cell
        tile, modifier = self.level.room(rid).tile_at(c, r)
        return rid, tile, modifier

    def is_floor(self, room_id: int, col: int, row: int) -> bool:
        """Canon ``tile_is_floor`` con estado: una gate (abierta o
        cerrada) es suelo; una losa suelta caída no; un muro NO."""
        cell = resolve_cell(self.level, room_id, col, row)
        if cell is None:
            return False
        rid, c, r = cell
        room = self.level.room(rid)
        if room.tile_at(c, r)[0] is Tile.WALL:
            return False
        return is_solid_at(room, c, r, self.broken_floors)

    def is_closed_gate(self, room_id: int, col: int, row: int) -> bool:
        cell = resolve_cell(self.level, room_id, col, row)
        if cell is None:
            return False
        rid, c, r = cell
        return blocks_body_at(self.level.room(rid), c, r, self.open_gates) and (
            self.level.room(rid).tile_at(c, r)[0] is Tile.GATE
        )


def is_ledge_at(terrain: Terrain, room_id: int, col: int, row: int) -> bool:
    """¿La celda es una cornisa agarrable? Canon ``can_grab``: un tile de
    suelo (``tile_is_floor``) — un muro NO lo es. Una gate cerrada
    tampoco (canon: se trepa "hasta la gate cerrada" y se vuelve a bajar;
    aquí simplemente no se agarra). Puede estar en la sala vecina."""
    if terrain.is_closed_gate(room_id, col, row):
        return False
    return terrain.is_floor(room_id, col, row)


def is_air_at(terrain: Terrain, room_id: int, col: int, row: int) -> bool:
    """¿La celda está libre para el cuerpo / las manos? Ni muro, ni suelo,
    ni gate cerrada (canon: no se agarra "a través" de un muro ni de un
    suelo). Fuera del mapa cuenta como muro."""
    cell = terrain.cell(room_id, col, row)
    if cell is None:
        return False
    _, tile, _ = cell
    if tile is Tile.WALL:
        return False
    if terrain.is_closed_gate(room_id, col, row):
        return False
    if tile is Tile.GATE:
        return True  # gate abierta: se pasa por debajo
    return not terrain.is_floor(room_id, col, row)


# ---------------------------------------------------------------------------
# Hang grab (CHECK_GRAB canónico — exige SHIFT)
# ---------------------------------------------------------------------------


def can_grab(char: Char, terrain: Terrain, *, shift_held: bool) -> tuple[int, int] | None:
    """Detecta si el char puede engancharse a una cornisa.

    Geometría canon: el cuerpo está en la celda (col, row) — en el aire —
    y las manos alcanzan la cornisa en diagonal: (col+fwd, row-1) debe
    ser suelo, y la celda sobre el cuerpo (col, row-1) debe ser aire
    (si fuera suelo, el char tendría el techo encima). Vale tanto
    subiendo en un salto como cayendo. La cornisa puede estar en la sala
    vecina (norte / este / oeste).

    Devuelve ``(ledge_col, ledge_row)`` relativos a la sala del char, o
    ``None``.
    """
    if not shift_held:
        return None
    if char.action not in (Action.IN_FREEFALL, Action.IN_MIDAIR):
        return None
    if char.fall_y >= GRAB_FALL_Y_THRESHOLD:
        return None
    if char.alive >= 0:
        return None
    if not (0 <= char.curr_col < SCREEN_TILECOUNT_X and 0 <= char.curr_row < SCREEN_TILECOUNT_Y):
        return None

    forward_col = char.curr_col + _forward_sign(char.direction)
    ledge_row = char.curr_row - 1
    if not is_ledge_at(terrain, char.room, forward_col, ledge_row):
        return None
    if not is_air_at(terrain, char.room, char.curr_col, ledge_row):
        return None  # techo sobre la cabeza: no hay hueco para las manos
    # El cuerpo puede estar en una celda de suelo: es el salto-y-agarre
    # canon desde el piso de abajo (cuelga en su propia banda).
    return forward_col, ledge_row


def snap_to_hang(char: Char, ledge_col: int, ledge_row: int) -> Char:
    """Coloca el char colgando: el cuerpo se queda en su celda (bajo la
    cornisa, en el aire), manos arriba, mirando hacia la cornisa."""
    fwd = 1 if ledge_col > char.curr_col else -1
    return _hanging(
        replace(char, curr_row=ledge_row + 1),
        fwd,
        Seq.GRAB_LEDGE_MIDAIR,
    )


def _hanging(char: Char, fwd: int, seq: Seq) -> Char:
    """Estado colgado en la celda actual del char, cornisa en (col+fwd,
    row-1). La secuencia ``seq`` anima el agarre y desemboca en el idle
    colgado (``HANG_STRAIGHT``); mientras dura no se acepta input.

    Canon ``check_grab``: ``Char.y = y_land[curr_row + 1]`` — colgado, los
    pies quedan a la altura del suelo de la fila del cuerpo (el char mide
    una fila; las manos en la cornisa). Por eso descolgarse "resta un
    piso" a la caída."""
    return replace(
        char,
        x=TILE_SIZE_X - 3 if fwd > 0 else 2,
        y=FEET_Y,
        direction=int(Direction.RIGHT) if fwd > 0 else int(Direction.LEFT),
        action=Action.HANG_CLIMB,
        fall_x=0,
        fall_y=0,
        fall_dist=0,
        curr_seq_id=int(seq),
        curr_seq_idx=0,
    )


def _body_cell(terrain: Terrain, room_id: int, col: int, row: int) -> tuple[int, int, int] | None:
    """Celda donde queda el cuerpo colgado (puede ser la sala vecina); un
    muro no vale."""
    cell = terrain.cell(room_id, col, row)
    if cell is None or cell[1] is Tile.WALL:
        return None
    return resolve_cell(terrain.level, room_id, col, row)


def jump_up(char: Char, terrain: Terrain) -> Char | None:
    """↑ de pie (canon ``check_jump_up``): si hay una cornisa al alcance,
    el char salta y se agarra; si no, ``None`` (salto vertical normal).

    1. Cornisa delante-arriba (col+fwd, row-1) con aire encima del char:
       se agarra y cuelga en su propia celda.
    2. Suelo justo encima (col, row-1) con aire detrás-arriba: se agarra
       a su borde trasero — el cuerpo pasa a la celda de detrás (puede
       ser la sala vecina) colgando sobre el vacío o sobre el piso de
       atrás. Es el gesto canon para trepar un pozo de cornisas de
       espaldas al hueco.
    """
    fwd = _forward_sign(char.direction)
    col, row, rid = char.curr_col, char.curr_row, char.room
    if is_ledge_at(terrain, rid, col + fwd, row - 1) and is_air_at(terrain, rid, col, row - 1):
        return _hanging(char, fwd, Seq.JUMP_UP_GRAB)
    if is_ledge_at(terrain, rid, col, row - 1) and is_air_at(terrain, rid, col - fwd, row - 1):
        body = _body_cell(terrain, rid, col - fwd, row)
        if body is None:
            return None
        brid, bcol, brow = body
        return _hanging(
            replace(char, room=brid, curr_col=bcol, curr_row=brow), fwd, Seq.JUMP_UP_GRAB
        )
    return None


def climb_down(char: Char, terrain: Terrain) -> Char | None:
    """↓ de pie de espaldas a un borde (canon ``down_pressed``): el char se
    descuelga de la celda que pisa y queda colgado con el cuerpo en la
    celda de detrás, una fila más abajo (puede ser la sala sur). ``None``
    si no hay borde detrás (→ agacharse)."""
    fwd = _forward_sign(char.direction)
    col, row, rid = char.curr_col, char.curr_row, char.room
    if not is_ledge_at(terrain, rid, col, row):
        return None
    if not is_air_at(terrain, rid, col - fwd, row):
        return None
    body = _body_cell(terrain, rid, col - fwd, row + 1)
    if body is None:
        return None
    brid, bcol, brow = body
    return _hanging(replace(char, room=brid, curr_col=bcol, curr_row=brow), fwd, Seq.CLIMB_DOWN)


def climb_up_target(char: Char) -> tuple[int, int]:
    """Celda de pie tras trepar desde colgado: la cornisa (col+fwd, row-1)."""
    return char.curr_col + _forward_sign(char.direction), char.curr_row - 1


# ---------------------------------------------------------------------------
# Step físico completo (orden canónico por tick)
# ---------------------------------------------------------------------------


# Secuencias de locomoción "con los pies en el suelo" — si la celda del
# char deja de ser suelo durante una de ellas, cae. Las secuencias
# aéreas (STANDING_JUMP, RUN_JUMP, FALL...) gestionan su propia caída.
_GROUNDED_SEQS: frozenset[int] = frozenset(
    {
        int(Seq.STAND),
        int(Seq.START_RUN),
        int(Seq.RUN),
        int(Seq.STOP_RUN),
        int(Seq.STEP),
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

# Acciones exentas de colisión y gravedad: colgado / trepando.
_CLIMB_ACTIONS: frozenset[Action] = frozenset({Action.HANG_STRAIGHT, Action.HANG_CLIMB})

FEET_Y: int = TILE_SIZE_Y - 1
"""``y`` de un char de pie: los pies en el borde inferior de su celda
(canon: la superficie del suelo es el borde inferior de la fila)."""


def start_fall(char: Char) -> Char:
    """La celda dejó de ser suelo: inicia caída libre."""
    return replace(
        char,
        action=Action.IN_FREEFALL,
        curr_seq_id=int(Seq.FALL),
        curr_seq_idx=0,
        fall_x=0,
        fall_y=0,
        fall_dist=0,
    )


def _land(char: Char) -> Char:
    """Aterrizaje EN la celda actual (que es suelo): soft / med (-1 HP) /
    mortal según la distancia de caída acumulada.

    Canon POP1: 1 piso es seguro, 2 pisos cuestan 1 HP, 3 pisos matan.
    Con la poción FLOAT activa el aterrizaje siempre es suave.
    """
    dist = char.fall_dist
    landed = replace(
        char,
        y=FEET_Y,
        fall_x=0,
        fall_y=0,
        fall_dist=0,
        landed_fall_y=char.fall_y,
    )
    is_enemy = char.charid is not CharId.KID and char.charid is not CharId.PRINCESS
    if char.float_ticks > 0 or dist < LAND_MED_FALL_DIST:
        if is_enemy and char.sword == SwordStatus.DRAWN:
            # Canon seq 63: el guard aterriza y sigue en guardia.
            return replace(
                landed,
                action=Action.STAND,
                curr_seq_id=int(Seq.ENGARDE),
                curr_seq_idx=0,
            )
        return replace(
            landed,
            action=Action.STAND,
            curr_seq_id=int(Seq.SOFT_LAND),
            curr_seq_idx=0,
        )
    if is_enemy and char.charid is not CharId.SHADOW:
        # Canon land(): un guard muere en cualquier caída que no sea suave.
        dist = LAND_DEAD_FALL_DIST
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


def _finish_climb(char: Char, snapshot: Char, level: Level) -> Char:
    """CLIMB_UP terminó: el char se pone de pie EN la cornisa (col+fwd,
    row-1 respecto a donde colgaba). Si la cornisa está en la sala norte
    (row -1), cambia de sala."""
    tcol, trow = climb_up_target(snapshot)
    cell = resolve_cell(level, snapshot.room, tcol, trow)
    if cell is None:
        return char
    room_id, tcol, trow = cell
    return replace(
        char,
        room=room_id,
        curr_col=tcol,
        curr_row=trow,
        x=TILE_SIZE_X // 2,
        y=FEET_Y,
        action=Action.STAND,
        fall_x=0,
        fall_y=0,
        fall_dist=0,
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
    """Un tick completo de física para un char (geometría canon POP1).

    El char OCUPA la celda del suelo que pisa; ``y`` es la altura de los
    pies dentro de la fila (0 arriba, ``FEET_Y`` = de pie en el suelo).

    1. ``play_seq`` — avanza la secuencia (aplica dx/dy).
    2. ``fall_accel`` / ``fall_speed`` — gravedad en caída libre.
    3. ``normalize_to_cell`` + ``cross_border``.
    4. Fin de trepada → de pie en la cornisa.
    5. Head-bump: subir contra el suelo del piso de arriba aplana el arco.
    6. Colisión horizontal — muro / gate cerrada en la celda: en tierra
       revierte + BUMP; en el aire corta el vuelo y cae recto.
    7. Aterrizaje — en caída libre dentro de una celda de suelo se
       aterriza EN ella; bajo la última fila sin sala al sur, abismo.
    8. ``can_grab`` — engancha cornisa si SHIFT + condiciones.
    9. Walk-off — locomoción de suelo en una celda que no es suelo → cae.
    """
    snapshot = char
    char = replace(char, landed_fall_y=0) if char.landed_fall_y else char
    char = play_seq(char)
    char = fall_accel(char, has_feather=has_feather)
    char = fall_speed(char)

    # 3a. Suelo bajo los pies ANTES de normalizar: un char en el aire cuya
    #     celda es suelo no puede bajar de FEET_Y (la superficie). Si está
    #     cayendo, aterriza aquí; si vuela (salto), se desliza a ras de
    #     suelo hasta que la secuencia termine o pase sobre un hueco.
    if (
        char.action in (Action.IN_FREEFALL, Action.IN_MIDAIR)
        and char.alive < 0
        and char.y > FEET_Y
        and 1 <= char.room <= len(level.rooms)
    ):
        # La columna puede haber cambiado este tick (dx): sondea la celda
        # ya normalizada en X, con la fila todavía sin bajar.
        probe = normalize_to_cell(replace(char, y=FEET_Y))
        if (
            0 <= probe.curr_col < SCREEN_TILECOUNT_X
            and 0 <= probe.curr_row < SCREEN_TILECOUNT_Y
            and is_solid_at(level.room(char.room), probe.curr_col, probe.curr_row, broken_floors)
        ):
            char = probe  # x normalizada, y = FEET_Y
            if char.action is Action.IN_FREEFALL:
                return _land(char)

    char = normalize_to_cell(char)
    char = cross_border(char, level)

    if not (1 <= char.room <= len(level.rooms)):
        return char
    room = level.room(char.room)

    # 4. Trepada completada (la secuencia saltó a STAND): a la cornisa.
    if snapshot.action is Action.HANG_CLIMB and char.action is Action.STAND:
        return _finish_climb(char, snapshot, level)
    if char.action in _CLIMB_ACTIONS:
        return char  # colgado / trepando: sin gravedad ni colisiones

    in_air = char.action in (Action.IN_FREEFALL, Action.IN_MIDAIR)
    in_cell = 0 <= char.curr_row < SCREEN_TILECOUNT_Y and 0 <= char.curr_col < SCREEN_TILECOUNT_X

    # 5. Head-bump: subiendo contra una celda de suelo (el piso de arriba).
    if (
        char.action is Action.IN_MIDAIR
        and char.alive < 0
        and char.room == snapshot.room
        and char.curr_row < snapshot.curr_row
        and in_cell
        and is_solid_at(room, char.curr_col, char.curr_row, broken_floors)
    ):
        char = replace(char, curr_row=snapshot.curr_row, y=0)

    # 6. Colisión horizontal.
    if (
        in_cell
        and blocks_body_at(room, char.curr_col, char.curr_row, open_gates)
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

    # 7. Aterrizaje: en caída libre, con los pies en la superficie de una
    #    celda de suelo (la superficie es el borde INFERIOR de la celda:
    #    el char atraviesa la banda hasta llegar a ella; la sonda 3a
    #    cubre el caso de rebasarla dentro del tick).
    if char.action is Action.IN_FREEFALL and char.alive < 0:
        if (
            in_cell
            and char.y >= FEET_Y
            and is_solid_at(room, char.curr_col, char.curr_row, broken_floors)
        ):
            return _land(char)
        if char.curr_row >= SCREEN_TILECOUNT_Y:
            return _die_in_abyss(char)

    # 8. Hang grab
    ledge = can_grab(char, Terrain(level, open_gates, broken_floors), shift_held=shift_held)
    if ledge is not None:
        return snap_to_hang(char, *ledge)

    # 9. Walk-off / asiento: locomoción de suelo.
    if char.alive < 0 and not in_air and char.curr_seq_id in _GROUNDED_SEQS and in_cell:
        if not is_solid_at(room, char.curr_col, char.curr_row, broken_floors):
            return start_fall(char)
        if char.y != FEET_Y:
            char = replace(char, y=FEET_Y)

    return char
