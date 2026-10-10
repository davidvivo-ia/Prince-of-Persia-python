"""Tick lógico canónico — orquesta toda la simulación a 12 FPS.

Orden por tick (replica `seg005.c::do_animations` de SDLPoP):

1. Procesa input del jugador → posible cambio de seq del kid.
2. Avanza secuencia de cada char (``play_seq``).
3. Aplica gravedad y posición (fall_accel + fall_speed).
4. Normaliza sub-tile → celda.
5. Cambio de sala si cruzó borde.
6. Detecta hang grab (SHIFT + condiciones).
7. Avanza estados de trampas (loose, chomper, gate).
8. Resuelve combate kid vs guards adyacentes.
9. Resuelve recogida de items (sword, potions).
10. Resuelve trampas letales (chomper letal, spike con caída).
11. Resuelve exit door (pasar de nivel).
12. Decrementa tiempo. Comprueba timeout / muerte.

Cada tick produce un nuevo ``Game`` inmutable.
"""

from __future__ import annotations

import functools
from dataclasses import replace

from pop2026canon.application.controller import Command, apply_input
from pop2026canon.domain.actions import Action, Direction, Seq, SwordStatus
from pop2026canon.domain.chars import Char, CharId
from pop2026canon.domain.combat import char_opp_dist, is_hostile, resolve_combat
from pop2026canon.domain.constants import TILE_SIZE_Y
from pop2026canon.domain.game import Game, GameStatus, TimeRemaining
from pop2026canon.domain.level import Level
from pop2026canon.domain.physics import Terrain, is_solid_at, step_physics
from pop2026canon.domain.tiles import Tile
from pop2026canon.domain.traps import (
    FALLING_TILE_ACCEL,
    FALLING_TILE_MAX_SPEED,
    FallingTile,
    LevelState,
    chomper_blood,
    chomper_is_lethal,
    chomper_stop,
    loose_press,
    loose_shake,
    spike_disable,
    spike_kills,
    spike_trigger,
    start_chompers,
    tick_chomper,
    tick_gate,
    tick_loose,
    tick_spike,
    trigger_gate_close,
    trigger_gate_open,
    trigger_gate_permanent,
)


def advance(game: Game, cmd: Command) -> Game:
    """Un tick lógico completo."""
    if not game.running:
        return game

    # 1. Input del jugador → posible cambio de seq del kid
    new_kid = apply_input(
        game.kid, cmd, Terrain(game.level, game.state.open_gates, game.state.fallen_floors)
    )
    new_kid = _kid_combat_timers(new_kid, game.others)

    # 1a. Canon control_standing: con espada, el kid desenvaina solo al
    #     ver a un guard que le ve (o se gira si lo tiene a la espalda).
    new_kid = _auto_engarde(new_kid, game)

    # 2-6. Física del kid (play_seq + gravity + collision + grab)
    open_gates = game.state.open_gates
    broken_floors = game.state.fallen_floors
    new_kid = step_physics(
        new_kid,
        game.level,
        shift_held=cmd.shift,
        has_feather=new_kid.float_ticks > 0,
        open_gates=open_gates,
        broken_floors=broken_floors,
    )
    if new_kid.float_ticks > 0:
        new_kid = replace(new_kid, float_ticks=new_kid.float_ticks - 1)

    # 2b. Física de otros chars (guards, shadow, ...)
    new_others = tuple(
        step_physics(
            c, game.level, shift_held=False, open_gates=open_gates, broken_floors=broken_floors
        )
        for c in game.others
    )

    # 2c. Contador de muerte: un char muerto (alive >= 0) suma un frame
    #     por tick; a los 30 el juego lo registra (LOST_DIED).
    if new_kid.alive >= 0:
        new_kid = replace(new_kid, alive=new_kid.alive + 1)
    new_others = tuple(replace(c, alive=c.alive + 1) if c.alive >= 0 else c for c in new_others)

    # 2d. Los guards vivos bloquean el paso (canon bump_into_opponent).
    new_kid = _block_kid_by_guards(game.kid, new_kid, new_others, game.level)

    # 2e. Canon follow_guard: el guard que perseguía al kid cruza a la
    #     sala vecina tras él.
    new_others = _follow_kid_between_rooms(game, new_kid, new_others)

    # 7. Trampas: botones, gates, losas sueltas, pinchos, cuchillas y las
    #    losas que están cayendo.
    new_state = _tick_traps(game, new_kid, new_others)
    new_kid, new_state, crushed_by_tile = _tick_falling_tiles(game, new_kid, new_state)

    # 7b. Eventos canon scripted: shadow, skeleton, vizier, princess, mouse
    interim = replace(game, kid=new_kid, others=new_others, state=new_state)
    interim = _trigger_special_chars(interim)

    # 7c. IA de guards (canon autocontrol_guard_active)
    from pop2026canon.domain.guard import step_guards_ai

    interim = step_guards_ai(interim)
    new_kid = interim.kid
    new_others = interim.others
    new_state = interim.state

    # 8. Combate kid vs enemigos (canon check_sword_hurting)
    new_kid, new_others = _resolve_room_combat(new_kid, new_others)

    # 9. Recogida de items (sword, potion, exit)
    # Los flags que han puesto los eventos scripted de este tick (sombra
    # fusionada, esqueleto despierto...) viajan en ``interim``, no en
    # ``game``: si se leyeran de ``game`` se perderían cada tick.
    new_kid, new_state, new_flags, status_override, bonus_ticks = _resolve_pickup(
        interim, new_kid, new_state
    )

    # 9b. Reunión con la princesa (L14) → victoria del juego completo
    if status_override is None:
        status_override = _check_princess_reunion(new_kid, new_others)

    # 10. Trampas letales (cuchillas, pinchos, gate que cierra) — kid y guards
    new_kid, new_state, killed_by_trap = _resolve_lethal_traps(game, new_kid, new_state)
    new_others, new_state = _resolve_lethal_traps_others(game, new_others, new_state)
    new_kid, crushed = _resolve_gate_crush(game, new_kid, new_state)
    killed_by_trap = killed_by_trap or crushed or crushed_by_tile

    # 10b. Canon died_on_button: morir sobre un botón lo deja accionado.
    new_state = _died_on_button(game, new_kid, new_state)

    # 11. Decremento tiempo + comprobación timeout
    new_time = _tick_time(game.time)
    if bonus_ticks:
        new_time = new_time.plus_ticks(bonus_ticks)

    # 12. Estado global
    new_status = _resolve_status(new_kid, new_time, status_override, killed_by_trap, game.status)

    return replace(
        game,
        kid=new_kid,
        others=new_others,
        state=new_state,
        time=new_time,
        flags=new_flags,
        status=new_status,
        tick_count=game.tick_count + 1,
    )


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------


def _trigger_special_chars(game: Game) -> Game:
    """Dispara los eventos canon scripted del nivel actual."""
    from pop2026canon.domain.princess import trigger_mouse_appear, trigger_princess_reunion
    from pop2026canon.domain.shadow import trigger_shadow_encounters
    from pop2026canon.domain.skeleton import step_skeleton_ai, trigger_skeleton_wake
    from pop2026canon.domain.vizier import trigger_vizier_spawn

    game = trigger_skeleton_wake(game)
    game = step_skeleton_ai(game)
    game = trigger_shadow_encounters(game)
    game = trigger_vizier_spawn(game)
    game = trigger_mouse_appear(game)
    game = trigger_princess_reunion(game)
    return game


def _tick_traps(game: Game, kid: Char, others: tuple[Char, ...]) -> LevelState:
    """Avanza las trampas del nivel (canon ``do_trobs`` + ``check_press``
    + ``check_spike_below`` + ``start_chompers``)."""
    new_state = game.state
    level = game.level

    # Losas sueltas: pisarlas (con los pies en el suelo) o golpearlas
    # desde abajo saltando arranca su cuenta atrás.
    for actor in (kid, *others):
        if actor.alive >= 0 or not (1 <= actor.room <= len(level.rooms)):
            continue
        if not (0 <= actor.curr_col < 10 and 0 <= actor.curr_row < 3):
            continue
        room = level.room(actor.room)
        cell = (actor.room, actor.curr_col, actor.curr_row)
        if _grounded(actor) and room.tile_at(actor.curr_col, actor.curr_row)[0] is Tile.LOOSE:
            new_state = loose_press(new_state, cell)
        elif (
            actor.charid is CharId.KID
            and actor.action is Action.IN_MIDAIR
            and actor.curr_seq_id == int(Seq.STANDING_JUMP)
            and actor.curr_row > 0
            and actor.y <= 32
            and room.tile_at(actor.curr_col, actor.curr_row - 1)[0] is Tile.LOOSE
        ):
            # Canon: saltar con la cabeza contra una losa suelta la suelta.
            above = (actor.room, actor.curr_col, actor.curr_row - 1)
            new_state = loose_press(new_state, above)
    for coord, value in tuple(new_state.tile_states):
        rid, c, r = coord
        if not (1 <= rid <= len(level.rooms)):
            continue
        if level.room(rid).tile_at(c, r)[0] is Tile.LOOSE and value != 0:
            new_state, _ = tick_loose(new_state, coord)

    # Pinchos: el kid, por encima o al lado, los hace salir; luego animan.
    new_state = _trigger_spikes_below(game, kid, new_state)
    for coord, _value in tuple(new_state.tile_states):
        rid, c, r = coord
        if not (1 <= rid <= len(level.rooms)):
            continue
        if level.room(rid).tile_at(c, r)[0] is Tile.SPIKE:
            new_state = tick_spike(new_state, coord)

    # Cuchillas: arrancan al llegar el kid a su fila; se paran al irse.
    new_state = _manage_chompers(game, kid, new_state)

    # Botones (canon check_press + do_trigger_list): cada plate pisada
    # dispara sus doorlinks — OPENER abre, CLOSER cierra. Una plate
    # vinculada a una LEVEL_DOOR la abre de forma PERMANENTE.
    pressed_plates = _find_pressed_plates_global(replace(game, kid=kid, others=others))
    for link in level.doorlinks:
        kind = pressed_plates.get(link.plate_coord)
        if kind is None:
            continue
        new_state = _trigger_link(level, new_state, link.gate_coord, kind)

    # Gates: animan en TODAS las salas (canon: los trobs siguen aunque la
    # sala no esté en pantalla). Una gate sin plate vinculada sólo la abre
    # un evento scripted (ratón de L8): el evento la mete en open_gates y
    # aquí se convierte en una apertura normal.
    for gate_coord in _gate_coords(level):
        if (
            gate_coord in new_state.open_gates
            and new_state.state_at(gate_coord) == 0
            and gate_coord not in new_state.opening_gates
            and gate_coord not in new_state.permanent_gates
        ):
            new_state = trigger_gate_open(new_state, gate_coord)
        new_state = tick_gate(new_state, gate_coord)

    return new_state


def _trigger_link(
    level: Level, state: LevelState, gate_coord: tuple[int, int, int], kind: Tile
) -> LevelState:
    """Canon ``trigger_1``: acciona el destino de un doorlink según el
    tipo de botón (OPENER abre, CLOSER cierra, DEBRIS abre para siempre)."""
    gate_room_id, gate_col, gate_row = gate_coord
    if not (1 <= gate_room_id <= len(level.rooms)):
        return state
    target_tile, _ = level.room(gate_room_id).tile_at(gate_col, gate_row)
    if target_tile in (Tile.LEVEL_DOOR_LEFT, Tile.LEVEL_DOOR_RIGHT):
        if kind in (Tile.OPENER, Tile.DEBRIS):
            return state.with_gate_open(gate_coord)
        return state
    if target_tile is not Tile.GATE:
        return state
    if kind is Tile.OPENER:
        return trigger_gate_open(state, gate_coord)
    if kind is Tile.DEBRIS:
        return trigger_gate_permanent(state, gate_coord)
    return trigger_gate_close(state, gate_coord)


def _trigger_spikes_below(game: Game, kid: Char, state: LevelState) -> LevelState:
    """Canon ``check_spike_below``: desde cada columna que ocupa el kid,
    baja por el aire hasta el primer suelo; si son pinchos, salen."""
    if kid.alive >= 0 or not (1 <= kid.room <= len(game.level.rooms)):
        return state
    if not (0 <= kid.curr_col < 10 and 0 <= kid.curr_row < 3):
        return state
    room = game.level.room(kid.room)
    cols = {kid.curr_col}
    # La caja de colisión del kid asoma a la celda vecina cerca del borde.
    if kid.x >= 10 and kid.curr_col < 9:
        cols.add(kid.curr_col + 1)
    if kid.x <= 3 and kid.curr_col > 0:
        cols.add(kid.curr_col - 1)
    for col in cols:
        row = kid.curr_row
        while row < 3:
            tile, _ = room.tile_at(col, row)
            if tile is Tile.SPIKE:
                state = spike_trigger(state, (kid.room, col, row))
                break
            if is_solid_at(room, col, row, state.fallen_floors):
                break
            row += 1
    return state


def _manage_chompers(game: Game, kid: Char, state: LevelState) -> LevelState:
    """Canon ``start_chompers`` (al aterrizar, empezar a caer, cambiar de
    sala o de fila) y la parada al irse el kid de la fila; entre medias
    las cuchillas activas ciclan."""
    level = game.level
    prev = game.kid
    moved = (prev.room, prev.curr_row) != (kid.room, kid.curr_row)
    moved = moved or abs(prev.curr_col - kid.curr_col) > 1 or game.tick_count == 0
    landed = kid.landed_fall_y > 0 and prev.landed_fall_y == 0
    started_fall = kid.action is Action.IN_FREEFALL and prev.action is not Action.IN_FREEFALL
    if (
        (moved or landed or started_fall)
        and 1 <= kid.room <= len(level.rooms)
        and 0 <= kid.curr_row < 3
    ):
        room = level.room(kid.room)
        cols = [c for c in range(10) if room.tile_at(c, kid.curr_row)[0] is Tile.CHOMPER]
        state = start_chompers(state, kid.room, kid.curr_row, cols)
    for coord, value in tuple(state.tile_states):
        rid, c, r = coord
        if not (1 <= rid <= len(level.rooms)):
            continue
        if level.room(rid).tile_at(c, r)[0] is not Tile.CHOMPER or (value & 0x7F) == 0:
            continue
        state = tick_chomper(state, coord)
        kid_gone = rid != kid.room or r != kid.curr_row or (kid.alive >= 0 and not value & 0x80)
        if kid_gone:
            state = chomper_stop(state, coord)
    return state


def _tick_falling_tiles(game: Game, kid: Char, state: LevelState) -> tuple[Char, LevelState, bool]:
    """Canon ``do_mobs`` / ``move_loose``: cada losa en caída acelera,
    arrastra las losas sueltas que atraviesa, golpea al kid si le cae
    encima y se estrella contra el primer suelo (escombros, sacudida de
    la fila, botones)."""
    if not state.falling_tiles:
        return kid, state, False
    level = game.level
    remaining: list[FallingTile] = []
    spawned: list[FallingTile] = []
    crushed = False
    for falling in state.falling_tiles:
        mob = falling
        speed = min(FALLING_TILE_MAX_SPEED, mob.speed + FALLING_TILE_ACCEL)
        mob = replace(mob, speed=speed, y=mob.y + speed)
        # ¿Le cae encima al kid? (canon check_loose_fall_on_kid)
        if (
            not mob.hit_kid
            and kid.alive < 0
            and kid.room == mob.room
            and kid.curr_col == mob.col
            and mob.row == kid.curr_row
            and mob.y < kid.y
            and kid.y - 30 < mob.y
        ):
            mob = replace(mob, hit_kid=True)
            kid, died = _fell_on_your_head(kid)
            crushed = crushed or died
        if mob.y < TILE_SIZE_Y:
            remaining.append(mob)
            continue
        # Llegó al borde inferior de su fila: ¿qué hay en la celda?
        if not (1 <= mob.room <= len(level.rooms)):
            continue  # cayó fuera del mapa
        room = level.room(mob.room)
        tile, _ = room.tile_at(mob.col, mob.row)
        coord = (mob.room, mob.col, mob.row)
        if tile is Tile.LOOSE and coord not in state.fallen_floors:
            # Arrastra la losa que atraviesa (canon loose_fall).
            state = state.with_floor_fallen(coord).with_state(coord, 0)
            spawned.append(
                FallingTile(room=mob.room, col=mob.col, row=mob.row, y=6, speed=speed // 2)
            )
        if tile is Tile.EMPTY or tile is Tile.LOOSE or coord in state.fallen_floors:
            # Sigue cayendo: fila siguiente (o sala de abajo).
            row = mob.row + 1
            rid = mob.room
            if row >= 3:
                rid, row = room.link_s, 0
                if not (1 <= rid <= len(level.rooms)):
                    continue
            remaining.append(replace(mob, room=rid, row=row, y=mob.y - TILE_SIZE_Y))
            continue
        # Se estrella (canon do_knock + loose_land).
        for c in range(10):
            if room.tile_at(c, mob.row)[0] is Tile.LOOSE:
                state = loose_shake(state, (mob.room, c, mob.row))
        state = _loose_land(level, state, coord, tile)
    return kid, replace(state, falling_tiles=tuple(remaining + spawned)), crushed


def _loose_land(
    level: Level, state: LevelState, coord: tuple[int, int, int], tile: Tile
) -> LevelState:
    """Canon ``loose_land``: escombros sobre suelo, pinchos, pociones o
    antorchas; un OPENER queda accionado para siempre; un CLOSER se
    acciona."""
    if tile is Tile.OPENER:
        state = state.with_debris(coord)
        for link in level.doorlinks:
            if link.plate_coord == coord:
                state = _trigger_link(level, state, link.gate_coord, Tile.DEBRIS)
        return state
    if tile is Tile.CLOSER:
        for link in level.doorlinks:
            if link.plate_coord == coord:
                state = _trigger_link(level, state, link.gate_coord, Tile.CLOSER)
        return state
    if tile in (
        Tile.FLOOR,
        Tile.SPIKE,
        Tile.POTION,
        Tile.TORCH,
        Tile.TORCH_WITH_DEBRIS,
        Tile.DEBRIS,
    ):
        state = state.with_debris(coord)
        if tile is Tile.POTION:
            state = state.with_potion_consumed(coord)
    return state


def _fell_on_your_head(kid: Char) -> tuple[Char, bool]:
    """Canon ``fell_on_your_head``: una losa en la cabeza quita 1 HP (y
    derriba al kid); corriendo o colgado no le alcanza."""
    if kid.frame in range(5, 15) or kid.action in (
        Action.HANG_CLIMB,
        Action.HANG_STRAIGHT,
        Action.IN_MIDAIR,
        Action.IN_FREEFALL,
    ):
        return kid, False
    new_hp = kid.hp_curr - 1
    if new_hp <= 0:
        return (
            replace(
                kid,
                hp_curr=0,
                alive=0,
                action=Action.HURT,
                curr_seq_id=int(Seq.CRUSHED),
                curr_seq_idx=0,
                fall_x=0,
                fall_y=0,
            ),
            True,
        )
    return (
        replace(
            kid,
            hp_curr=new_hp,
            action=Action.STAND,
            curr_seq_id=int(Seq.LOOSE_FLOOR_FELL_ON_KID),
            curr_seq_idx=0,
        ),
        False,
    )


def _resolve_gate_crush(game: Game, kid: Char, state: LevelState) -> tuple[Char, bool]:
    """Canon: una gate que baja sobre el kid lo aplasta. Si el kid está
    EN la celda de una gate que ha dejado de ser franqueable, muere."""
    if kid.alive >= 0 or not (1 <= kid.room <= len(game.level.rooms)):
        return kid, False
    if not (0 <= kid.curr_col < 10 and 0 <= kid.curr_row < 3):
        return kid, False
    coord = (kid.room, kid.curr_col, kid.curr_row)
    tile, modifier = game.level.room(kid.room).tile_at(kid.curr_col, kid.curr_row)
    if tile is not Tile.GATE or modifier >= 7 or coord in state.open_gates:
        return kid, False
    return (
        replace(
            kid,
            hp_curr=0,
            alive=0,
            action=Action.HURT,
            curr_seq_id=int(Seq.CRUSHED),
            curr_seq_idx=0,
            fall_x=0,
            fall_y=0,
        ),
        True,
    )


def _find_pressed_plates_global(game: Game) -> dict[tuple[int, int, int], Tile]:
    """Botones pisados este tick en CUALQUIER sala → tipo (OPENER /
    CLOSER). Canon: el estado de una plate persiste mientras tenga peso
    encima, independientemente de la sala visible."""
    pressed: dict[tuple[int, int, int], Tile] = {}
    actors = [game.kid, *game.others]
    for actor in actors:
        if not (1 <= actor.room <= len(game.level.rooms)):
            continue
        if actor.alive >= 0:
            continue
        if not (0 <= actor.curr_col < 10 and 0 <= actor.curr_row < 3):
            continue
        if not _grounded(actor):
            continue  # canon check_press: sólo con los pies en el suelo
        room = game.level.room(actor.room)
        tile, _ = room.tile_at(actor.curr_col, actor.curr_row)
        coord = (actor.room, actor.curr_col, actor.curr_row)
        if tile in (Tile.OPENER, Tile.CLOSER) and coord not in game.state.debris_cells:
            pressed[coord] = tile
    return pressed


_AIRBORNE: frozenset[Action] = frozenset(
    {Action.IN_MIDAIR, Action.IN_FREEFALL, Action.HANG_STRAIGHT, Action.HANG_CLIMB}
)


def _grounded(actor: Char) -> bool:
    """¿Pisa el suelo de su celda? Saltando por encima de un botón o de
    una losa suelta no se activan (canon: ``check_press`` sólo en frames
    con los pies en el suelo)."""
    return actor.action not in _AIRBORNE


@functools.lru_cache(maxsize=32)
def _gate_coords(level: Level) -> tuple[tuple[int, int, int], ...]:
    """Coordenadas de todas las gates del nivel (cacheado por nivel)."""
    out: list[tuple[int, int, int]] = []
    for room in level.rooms:
        for r in range(3):
            for c in range(10):
                if room.tile_at(c, r)[0] is Tile.GATE:
                    out.append((room.id, c, r))
    return tuple(out)


def _kid_combat_timers(kid: Char, others: tuple[Char, ...]) -> Char:
    """Canon ``kid_sword_strike`` (15 ticks tras lanzar una estocada) y
    el adelanto de la parada: si el kid acaba de empezar a parar y el
    enemigo ya está en el frame 153, la parada se adelanta un frame para
    llegar a tiempo (canon ``parry`` → ``play_seq``)."""
    timer = max(0, kid.strike_timer - 1)
    if kid.curr_seq_id in (int(Seq.STRIKE), int(Seq.BLOCK_TO_STRIKE)) and kid.curr_seq_idx == 0:
        timer = 15
    if (
        kid.curr_seq_id == int(Seq.BLOCK_STRIKE)
        and kid.curr_seq_idx == 0
        and any(
            is_hostile(c) and c.alive < 0 and c.room == kid.room and c.frame == 153 for c in others
        )
    ):
        kid = replace(kid, curr_seq_idx=2)
    if timer != kid.strike_timer:
        kid = replace(kid, strike_timer=timer)
    return kid


def _auto_engarde(kid: Char, game: Game) -> Char:
    """Canon ``control_standing``: con espada y de pie, si un enemigo le
    ve (2) a entre -10 y 89 px, el kid desenvaina; si lo tiene detrás
    (< -6) se gira hacia él."""
    from pop2026canon.domain.guard import can_guard_see_kid

    if (
        not kid.has_sword
        or kid.alive >= 0
        or kid.action is not Action.STAND
        or kid.curr_seq_id not in (int(Seq.STAND), int(Seq.STOP_RUN))
    ):
        return kid
    for c in game.others:
        if not is_hostile(c) or c.alive >= 0 or c.room != kid.room:
            continue
        if can_guard_see_kid(game.level, c, kid, game.state.open_gates) < 2:
            continue
        distance = char_opp_dist(kid, c)
        if not (-10 <= distance < 90):
            continue
        if distance < -6:
            new_dir = 0 if c.curr_col > kid.curr_col else -1
            return replace(kid, direction=new_dir, curr_seq_id=int(Seq.TURN), curr_seq_idx=0)
        if kid.sword != SwordStatus.DRAWN:
            return replace(
                kid, sword=SwordStatus.DRAWN, curr_seq_id=int(Seq.DRAW_SWORD), curr_seq_idx=0
            )
        return kid
    return kid


def _block_kid_by_guards(prev_kid: Char, kid: Char, others: tuple[Char, ...], level) -> Char:  # type: ignore[no-untyped-def]
    """Si el kid acabó en la celda de un guard vivo viniendo por su misma
    fila, revierte su posición a la del tick anterior (conserva la
    secuencia/acción: el choque se resuelve en combate).

    Excepción: si la celda previa es un chomper, no se revierte — el
    guard no puede usarse como pared para empujar al kid a las
    cuchillas; comparten celda y el combate decide."""
    if kid.alive >= 0:
        return kid
    if (
        1 <= prev_kid.room <= len(level.rooms)
        and 0 <= prev_kid.curr_col < 10
        and 0 <= prev_kid.curr_row < 3
    ):
        prev_tile, _ = level.room(prev_kid.room).tile_at(prev_kid.curr_col, prev_kid.curr_row)
        if prev_tile is Tile.CHOMPER:
            return kid
    for other in others:
        if other.charid is not CharId.GUARD or other.alive >= 0:
            continue
        if (
            kid.room == other.room
            and kid.curr_row == other.curr_row
            and kid.curr_col == other.curr_col
            and prev_kid.room == other.room
            and prev_kid.curr_row == other.curr_row
        ):
            return replace(
                kid,
                room=prev_kid.room,
                curr_col=prev_kid.curr_col,
                curr_row=prev_kid.curr_row,
                x=prev_kid.x,
                y=prev_kid.y,
            )
    return kid


def _resolve_room_combat(kid: Char, others: tuple[Char, ...]) -> tuple[Char, tuple[Char, ...]]:
    """Canon ``check_sword_hurting``: cada enemigo armado de la sala
    intercambia estocadas con el kid (primero hiere el enemigo)."""
    new_kid = kid
    new_others_list = list(others)
    for i, enemy in enumerate(new_others_list):
        if not is_hostile(enemy) or enemy.alive >= 0 or enemy.room != new_kid.room:
            continue
        result = resolve_combat(new_kid, enemy)
        new_kid = result.kid
        new_others_list[i] = result.guard
    return new_kid, tuple(new_others_list)


def _follow_kid_between_rooms(game: Game, kid: Char, others: tuple[Char, ...]) -> tuple[Char, ...]:
    """Canon ``follow_guard``: si el kid sale por un lado de la sala y un
    enemigo en guardia le veía de cerca, cruza tras él y entra por el
    borde de la nueva sala."""
    prev = game.kid
    if kid.room == prev.room or kid.alive >= 0:
        return others
    if not (1 <= prev.room <= len(game.level.rooms)):
        return others
    old_room = game.level.room(prev.room)
    if kid.room == old_room.link_e:
        entry_col, entry_x = 0, 1
    elif kid.room == old_room.link_w:
        entry_col, entry_x = 9, 12
    else:
        return others
    from pop2026canon.domain.guard import can_guard_see_kid

    new_others = list(others)
    for i, enemy in enumerate(new_others):
        if not is_hostile(enemy) or enemy.alive >= 0 or enemy.room != prev.room:
            continue
        if enemy.frame < 150 or enemy.frame == 166:
            continue  # en reposo: no persigue
        if can_guard_see_kid(game.level, enemy, prev, game.state.open_gates) != 2:
            continue
        if abs(char_opp_dist(enemy, prev)) >= 4 * 14:
            continue
        new_others[i] = replace(
            enemy,
            room=kid.room,
            curr_col=entry_col,
            x=entry_x,
            curr_row=kid.curr_row,
            direction=int(Direction.RIGHT) if entry_col == 0 else int(Direction.LEFT),
        )
    return tuple(new_others)


def _resolve_pickup(game: Game, kid: Char, state):  # type: ignore[no-untyped-def]
    """Detecta recogida de sword, potions, y exit door.

    Devuelve además ``bonus_ticks`` (poción TIME: +30s al reloj).
    """
    new_flags = game.flags
    new_state = state
    status_override = None
    bonus_ticks = 0

    if not (1 <= kid.room <= len(game.level.rooms)):
        return kid, new_state, new_flags, status_override, bonus_ticks

    room = game.level.room(kid.room)
    if not (0 <= kid.curr_col < 10 and 0 <= kid.curr_row < 3):
        return kid, new_state, new_flags, status_override, bonus_ticks

    tile, modifier = room.tile_at(kid.curr_col, kid.curr_row)
    coord = (kid.room, kid.curr_col, kid.curr_row)
    # Semántica dual: en los niveles canon los items son tiles-suelo —
    # el kid queda una fila POR ENCIMA de ellos. Si la celda propia no
    # tiene item, mira la de debajo.
    if (
        tile
        not in (
            Tile.SWORD,
            Tile.POTION,
            Tile.LEVEL_DOOR_LEFT,
            Tile.LEVEL_DOOR_RIGHT,
        )
        and kid.curr_row + 1 < 3
    ):
        below_tile, below_mod = room.tile_at(kid.curr_col, kid.curr_row + 1)
        if below_tile in (
            Tile.SWORD,
            Tile.POTION,
            Tile.LEVEL_DOOR_LEFT,
            Tile.LEVEL_DOOR_RIGHT,
        ):
            tile, modifier = below_tile, below_mod
            coord = (kid.room, kid.curr_col, kid.curr_row + 1)

    if tile is Tile.SWORD and not new_flags.sword_picked:
        from pop2026canon.domain.actions import SwordStatus

        new_flags = replace(new_flags, sword_picked=True)
        new_state = new_state.with_potion_consumed(coord)  # marca como recogido
        kid = replace(kid, sword=SwordStatus.DRAWN, has_sword=True)

    elif tile is Tile.POTION and coord not in new_state.consumed_potions:
        from pop2026canon.domain.combat import heal, heal_max
        from pop2026canon.domain.constants import FEATHER_FALL_TICKS
        from pop2026canon.domain.tiles import PotionType

        new_state = new_state.with_potion_consumed(coord)
        ptype = PotionType(modifier) if modifier <= 6 else PotionType.HEAL
        if ptype is PotionType.HEAL:
            kid = heal(kid, 1)
        elif ptype is PotionType.MAX_HP:
            kid = heal_max(kid)
        elif ptype is PotionType.POISON:
            from pop2026canon.domain.combat import take_hp as _take

            kid = _take(kid, 1).char
        elif ptype is PotionType.FLOAT:
            kid = replace(kid, float_ticks=FEATHER_FALL_TICKS)
        elif ptype is PotionType.TIME:
            bonus_ticks = 360  # +30 segundos

    elif tile in (Tile.LEVEL_DOOR_LEFT, Tile.LEVEL_DOOR_RIGHT) and _exit_door_open(
        game, kid, new_state
    ):
        status_override = GameStatus.WON_LEVEL

    return kid, new_state, new_flags, status_override, bonus_ticks


def _exit_door_open(game: Game, kid: Char, state) -> bool:  # type: ignore[no-untyped-def]
    """¿La level door que toca el kid es una salida transitable?

    Canon POP1: los niveles tienen DOS level doors — la de entrada (en
    la sala de spawn, cerrada a tu espalda) y la de salida, que hay que
    ABRIR pisando su plate. Reglas:

    - Puerta con doorlink (plate asociada): sólo gana si está abierta.
    - Puerta sin doorlink fuera de la sala de spawn: salida siempre
      abierta (niveles fan-recreation).
    - Puerta sin doorlink en la sala de spawn: es la entrada — no gana.
    """
    # Las dos mitades de la puerta comparten estado: revisa la celda
    # tocada, sus vecinas horizontales y la fila de debajo (semántica
    # canon: la puerta es un tile-suelo).
    candidates = [
        (kid.room, kid.curr_col + dc, kid.curr_row + dr) for dc in (0, -1, 1) for dr in (0, 1)
    ]
    has_link = False
    for coord in candidates:
        if game.level.plates_for_gate(coord):
            has_link = True
            if coord in state.open_gates:
                return True
    if has_link:
        return False
    return kid.room != game.level.start_room


def _check_princess_reunion(kid: Char, others: tuple[Char, ...]) -> GameStatus | None:
    """L14: alcanzar a la princesa (misma sala, adyacente) gana el juego."""
    for c in others:
        if c.charid is not CharId.PRINCESS:
            continue
        if (
            kid.room == c.room
            and kid.curr_row == c.curr_row
            and abs(kid.curr_col - c.curr_col) <= 1
        ):
            return GameStatus.WON_GAME
    return None


def _spiked(char: Char) -> Char:
    return replace(
        char,
        hp_curr=0,
        alive=0,
        action=Action.HURT,
        curr_seq_id=int(Seq.SPIKED),
        curr_seq_idx=0,
        fall_x=0,
        fall_y=0,
    )


def _chomped(char: Char) -> Char:
    return replace(
        char,
        hp_curr=0,
        alive=0,
        action=Action.HURT,
        curr_seq_id=int(Seq.CHOMPED),
        curr_seq_idx=0,
        fall_x=0,
        fall_y=0,
    )


def _is_running(char: Char) -> bool:
    """Canon check_spiked: corriendo (frames 7..14) o arrancando un salto
    con carrerilla (34..39)."""
    return char.frame in range(7, 15) or char.frame in range(34, 40)


def _resolve_lethal_traps(
    game: Game, kid: Char, state: LevelState
) -> tuple[Char, LevelState, bool]:
    """Canon ``check_chomped_kid`` / ``check_spiked`` / ``land``."""
    if not (1 <= kid.room <= len(game.level.rooms)) or kid.alive >= 0:
        return kid, state, False
    room = game.level.room(kid.room)
    if not (0 <= kid.curr_col < 10 and 0 <= kid.curr_row < 3):
        return kid, state, False
    tile, _ = room.tile_at(kid.curr_col, kid.curr_row)
    coord = (kid.room, kid.curr_col, kid.curr_row)

    if tile is Tile.CHOMPER and chomper_is_lethal(state, coord) and _grounded(kid):
        return _chomped(kid), chomper_blood(state, coord), True

    if tile is Tile.SPIKE and _grounded(kid):
        landing = kid.landed_fall_y > 0
        if spike_kills(state, coord, running=_is_running(kid), landing=landing):
            return _spiked(kid), spike_disable(state, coord), True

    return kid, state, False


def _resolve_lethal_traps_others(
    game: Game, others: tuple[Char, ...], state: LevelState
) -> tuple[tuple[Char, ...], LevelState]:
    """Los guards también mueren en cuchillas y pinchos (canon)."""
    new_others = list(others)
    for i, c in enumerate(new_others):
        if c.alive >= 0 or not (1 <= c.room <= len(game.level.rooms)):
            continue
        if not (0 <= c.curr_col < 10 and 0 <= c.curr_row < 3):
            continue
        tile, _ = game.level.room(c.room).tile_at(c.curr_col, c.curr_row)
        coord = (c.room, c.curr_col, c.curr_row)
        if tile is Tile.CHOMPER and chomper_is_lethal(state, coord) and _grounded(c):
            new_others[i] = _chomped(c)
            state = chomper_blood(state, coord)
        elif tile is Tile.SPIKE and _grounded(c) and c.landed_fall_y > 0:
            if spike_kills(state, coord, running=False, landing=True):
                new_others[i] = _spiked(c)
                state = spike_disable(state, coord)
    return tuple(new_others), state


def _died_on_button(game: Game, kid: Char, state: LevelState) -> LevelState:
    """Canon ``died_on_button``: un kid que muere sobre un OPENER lo deja
    accionado para siempre (escombros); sobre un CLOSER, lo acciona."""
    if kid.alive != 0 or not (1 <= kid.room <= len(game.level.rooms)):
        return state
    if not (0 <= kid.curr_col < 10 and 0 <= kid.curr_row < 3):
        return state
    tile, _ = game.level.room(kid.room).tile_at(kid.curr_col, kid.curr_row)
    coord = (kid.room, kid.curr_col, kid.curr_row)
    if tile is Tile.OPENER and coord not in state.debris_cells:
        return _loose_land(game.level, state, coord, Tile.OPENER)
    if tile is Tile.CLOSER:
        return _loose_land(game.level, state, coord, Tile.CLOSER)
    return state


def _tick_time(time: TimeRemaining) -> TimeRemaining:
    """Decrementa 1 tick lógico del tiempo."""
    if time.is_zero():
        return time
    if time.ticks > 0:
        return TimeRemaining(minutes=time.minutes, ticks=time.ticks - 1)
    if time.minutes > 0:
        return TimeRemaining(minutes=time.minutes - 1, ticks=719)
    return time


def _resolve_status(
    kid: Char,
    time: TimeRemaining,
    status_override: GameStatus | None,
    killed_by_trap: bool,
    current: GameStatus,
) -> GameStatus:
    """Decide el estado global tras este tick."""
    if status_override is not None:
        return status_override
    if killed_by_trap or kid.alive >= 30:  # 30 frames muerto
        return GameStatus.LOST_DIED
    if time.is_zero():
        return GameStatus.LOST_TIMEOUT
    return current
