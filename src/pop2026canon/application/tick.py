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

from dataclasses import replace

from pop2026canon.application.controller import Command, apply_input
from pop2026canon.domain.actions import Action, Seq
from pop2026canon.domain.chars import Char, CharId
from pop2026canon.domain.combat import resolve_combat
from pop2026canon.domain.game import Game, GameStatus, TimeRemaining
from pop2026canon.domain.physics import step_physics
from pop2026canon.domain.tiles import Tile
from pop2026canon.domain.traps import (
    chomper_is_lethal,
    spike_kills_on_land,
    tick_chomper,
    tick_gate,
    tick_loose,
)


def advance(game: Game, cmd: Command) -> Game:
    """Un tick lógico completo."""
    if not game.running:
        return game

    # 1. Input del jugador → posible cambio de seq del kid
    new_kid = apply_input(game.kid, cmd)

    # 1b. Hang-shuffle: lateral colgado de cornisa
    if new_kid.action is Action.HANG_STRAIGHT and (cmd.left or cmd.right):
        from pop2026canon.domain.physics import hang_shuffle

        if 1 <= new_kid.room <= len(game.level.rooms):
            room_obj = game.level.room(new_kid.room)
            direction = 1 if cmd.right else -1
            new_kid = hang_shuffle(new_kid, room_obj, direction=direction)

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

    # 2'. Física de otros chars (guards, shadow, ...)
    new_others = tuple(
        step_physics(
            c, game.level, shift_held=False, open_gates=open_gates, broken_floors=broken_floors
        )
        for c in game.others
    )

    # 7. Avanzar trampas de la sala actual
    new_state = _tick_traps(game, new_kid)

    # 7b. Eventos canon scripted: shadow, skeleton, vizier, princess, mouse
    interim = replace(game, kid=new_kid, others=new_others, state=new_state)
    interim = _trigger_special_chars(interim)

    # 7c. IA de guards (acercarse al kid, ataque, bloqueo)
    from pop2026canon.domain.guard import step_guards_ai

    interim = step_guards_ai(interim)
    new_kid = interim.kid
    new_others = interim.others
    new_state = interim.state

    # 8. Combate kid vs guards adyacentes (mismo room + mismo row + dist 1)
    new_kid, new_others = _resolve_room_combat(new_kid, new_others)

    # 9. Recogida de items (sword, potion, exit)
    new_kid, new_state, new_flags, status_override, bonus_ticks = _resolve_pickup(
        game, new_kid, new_state
    )

    # 9b. Reunión con la princesa (L14) → victoria del juego completo
    if status_override is None:
        status_override = _check_princess_reunion(new_kid, new_others)

    # 10. Trampas letales (chomper closed, spike landing)
    new_kid, killed_by_trap = _resolve_lethal_traps(game, new_kid, new_state)

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


def _tick_traps(game: Game, kid: Char):  # type: ignore[no-untyped-def]
    """Avanza las trampas (loose en sala visible, chompers visibles, gates globales)."""
    new_state = game.state
    if not (1 <= kid.room <= len(game.level.rooms)):
        return new_state

    room = game.level.room(kid.room)

    # Loose floor: el kid está pisando si su celda + row+1 contiene loose
    kid_below = (kid.room, kid.curr_col, kid.curr_row + 1)
    if 0 <= kid.curr_row + 1 < 3 and 0 <= kid.curr_col < 10:
        tile_below, _ = room.tile_at(kid.curr_col, kid.curr_row + 1)
        if tile_below is Tile.LOOSE:
            new_state, _ = tick_loose(new_state, kid_below, kid_pressing=True)

    # Chompers: avanzan automáticamente cada tick (sólo sala visible — canon).
    for c in range(10):
        for r in range(3):
            tile, _ = room.tile_at(c, r)
            if tile is Tile.CHOMPER:
                new_state = tick_chomper(new_state, (kid.room, c, r))

    # Gates: ticken en TODAS las salas con doorlinks activos + sala visible.
    pressed_plates = _find_pressed_plates_global(game)

    # Exit doors: una plate vinculada a una LEVEL_DOOR la abre de forma
    # PERMANENTE (canon: la puerta de salida sube y se queda arriba).
    for link in game.level.doorlinks:
        if link.gate_coord in new_state.open_gates:
            continue
        if not any(p in pressed_plates for p in (link.plate_coord,)):
            continue
        gate_room_id, gate_col, gate_row = link.gate_coord
        if not (1 <= gate_room_id <= len(game.level.rooms)):
            continue
        target_tile, _ = game.level.room(gate_room_id).tile_at(gate_col, gate_row)
        if target_tile in (Tile.LEVEL_DOOR_LEFT, Tile.LEVEL_DOOR_RIGHT):
            new_state = new_state.with_gate_open(link.gate_coord)
    rooms_to_tick = {kid.room}
    for link in game.level.doorlinks:
        if link.plate_coord in pressed_plates or link.gate_coord in new_state.open_gates:
            rooms_to_tick.add(link.gate_room)
    for room_id in rooms_to_tick:
        if not (1 <= room_id <= len(game.level.rooms)):
            continue
        gate_room = game.level.room(room_id)
        for c in range(10):
            for r in range(3):
                tile, _ = gate_room.tile_at(c, r)
                if tile is not Tile.GATE:
                    continue
                gate_coord = (room_id, c, r)
                linked_plates = game.level.plates_for_gate(gate_coord)
                if linked_plates:
                    is_pressed = any(p in pressed_plates for p in linked_plates)
                else:
                    # Sin link explícito → sólo trigger scripted la abre.
                    is_pressed = gate_coord in new_state.open_gates
                new_state = tick_gate(new_state, gate_coord, plate_pressed=is_pressed)

    return new_state


def _find_pressed_plates_global(game: Game) -> set[tuple[int, int, int]]:
    """Devuelve plates pisadas este tick en CUALQUIER sala (canon: el
    estado de una plate persiste mientras tenga peso encima, independientemente
    de la sala visible)."""
    pressed: set[tuple[int, int, int]] = set()
    actors = [game.kid, *game.others]
    for actor in actors:
        if not (1 <= actor.room <= len(game.level.rooms)):
            continue
        if actor.alive >= 0:
            continue
        if not (0 <= actor.curr_col < 10 and 0 <= actor.curr_row < 3):
            continue
        room = game.level.room(actor.room)
        tile, _ = room.tile_at(actor.curr_col, actor.curr_row)
        if tile is Tile.OPENER:
            pressed.add((actor.room, actor.curr_col, actor.curr_row))
        elif actor.curr_row + 1 < 3:
            # Semántica canon: la plate es un tile-suelo — el actor
            # está una fila por encima de ella.
            below, _ = room.tile_at(actor.curr_col, actor.curr_row + 1)
            if below is Tile.OPENER:
                pressed.add((actor.room, actor.curr_col, actor.curr_row + 1))
    return pressed


def _resolve_room_combat(kid: Char, others: tuple[Char, ...]) -> tuple[Char, tuple[Char, ...]]:
    """Resuelve combate entre kid y guards adyacentes."""
    new_kid = kid
    new_others_list = list(others)
    for i, guard in enumerate(new_others_list):
        if guard.charid is not CharId.GUARD:
            continue
        result = resolve_combat(new_kid, guard)
        new_kid = result.kid
        new_others_list[i] = result.guard
    return new_kid, tuple(new_others_list)


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
        kid = replace(kid, sword=SwordStatus.DRAWN)

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


def _resolve_lethal_traps(game: Game, kid: Char, state) -> tuple[Char, bool]:  # type: ignore[no-untyped-def]
    """Aplica daño/muerte por chomper o spike."""
    if not (1 <= kid.room <= len(game.level.rooms)):
        return kid, False
    if kid.alive >= 0:
        return kid, False

    room = game.level.room(kid.room)
    if not (0 <= kid.curr_col < 10 and 0 <= kid.curr_row < 3):
        return kid, False

    tile, _ = room.tile_at(kid.curr_col, kid.curr_row)
    coord = (kid.room, kid.curr_col, kid.curr_row)
    # Semántica canon: trampas como tiles-suelo (kid una fila encima).
    if tile not in (Tile.CHOMPER, Tile.SPIKE) and kid.curr_row + 1 < 3:
        below_tile, _ = room.tile_at(kid.curr_col, kid.curr_row + 1)
        if below_tile in (Tile.CHOMPER, Tile.SPIKE):
            tile = below_tile
            coord = (kid.room, kid.curr_col, kid.curr_row + 1)

    if tile is Tile.CHOMPER and chomper_is_lethal(state, coord):
        kid = replace(
            kid,
            hp_curr=0,
            alive=0,
            action=Action.HURT,
            curr_seq_id=int(Seq.CHOMPED),
            curr_seq_idx=0,
        )
        return kid, True

    if tile is Tile.SPIKE and spike_kills_on_land(max(kid.fall_y, kid.landed_fall_y)):
        kid = replace(
            kid,
            hp_curr=0,
            alive=0,
            action=Action.HURT,
            curr_seq_id=int(Seq.SPIKED),
            curr_seq_idx=0,
        )
        return kid, True

    return kid, False


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
