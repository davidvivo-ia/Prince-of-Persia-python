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

    # 2-6. Física del kid (play_seq + gravity + collision + grab)
    new_kid = step_physics(new_kid, game.level, shift_held=cmd.shift)

    # 2'. Física de otros chars (guards, shadow, ...)
    new_others = tuple(step_physics(c, game.level, shift_held=False) for c in game.others)

    # 7. Avanzar trampas de la sala actual
    new_state = _tick_traps(game, new_kid)

    # 7b. Eventos canon scripted: shadow, skeleton, vizier, princess, mouse
    interim = replace(game, kid=new_kid, others=new_others, state=new_state)
    interim = _trigger_special_chars(interim)
    new_kid = interim.kid
    new_others = interim.others
    new_state = interim.state

    # 8. Combate kid vs guards adyacentes (mismo room + mismo row + dist 1)
    new_kid, new_others = _resolve_room_combat(new_kid, new_others)

    # 9. Recogida de items (sword, potion, exit)
    new_kid, new_state, new_flags, status_override = _resolve_pickup(game, new_kid, new_state)

    # 10. Trampas letales (chomper closed, spike landing)
    new_kid, killed_by_trap = _resolve_lethal_traps(game, new_kid, new_state)

    # 11. Decremento tiempo + comprobación timeout
    new_time = _tick_time(game.time)

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
    """Detecta recogida de sword, potions, y exit door."""
    new_flags = game.flags
    new_state = state
    status_override = None

    if not (1 <= kid.room <= len(game.level.rooms)):
        return kid, new_state, new_flags, status_override

    room = game.level.room(kid.room)
    if not (0 <= kid.curr_col < 10 and 0 <= kid.curr_row < 3):
        return kid, new_state, new_flags, status_override

    tile, modifier = room.tile_at(kid.curr_col, kid.curr_row)
    coord = (kid.room, kid.curr_col, kid.curr_row)

    if tile is Tile.SWORD and not new_flags.sword_picked:
        from pop2026canon.domain.actions import SwordStatus

        new_flags = replace(new_flags, sword_picked=True)
        new_state = new_state.with_potion_consumed(coord)  # marca como recogido
        kid = replace(kid, sword=SwordStatus.DRAWN)

    elif tile is Tile.POTION and coord not in new_state.consumed_potions:
        from pop2026canon.domain.combat import heal, heal_max
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

    elif tile in (Tile.LEVEL_DOOR_LEFT, Tile.LEVEL_DOOR_RIGHT):
        status_override = GameStatus.WON_LEVEL

    return kid, new_state, new_flags, status_override


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

    if tile is Tile.SPIKE and spike_kills_on_land(kid.fall_y):
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
