"""Princess + Mouse — chars de la cinemática final."""

from __future__ import annotations

from dataclasses import replace

from pop2026canon.domain.actions import Action, Direction, Seq
from pop2026canon.domain.chars import Char, CharId
from pop2026canon.domain.game import Game
from pop2026canon.domain.level import EventKind
from pop2026canon.domain.tiles import Tile


def trigger_princess_reunion(game: Game) -> Game:
    """L14: spawn princesa al entrar al nivel."""
    if game.find_char(CharId.PRINCESS) is not None:
        return game

    for event in game.level.events:
        if event.kind is EventKind.PRINCESS_REUNION:
            princess = Char(
                charid=CharId.PRINCESS,
                room=event.room,
                curr_col=7,
                curr_row=1,
                direction=int(Direction.LEFT),
                curr_seq_id=int(Seq.STAND),
                action=Action.STAND,
                hp_curr=1,
                hp_max=1,
            )
            return replace(game, others=(*game.others, princess))
    return game


def trigger_mouse_appear(game: Game) -> Game:
    """L8: ratón aparece para abrir gate.

    Cuando el ratón entra a la sala, fuerza la apertura de TODAS las gates
    de esa sala que no tienen plate vinculada (canon: la gate "del mouse"
    es la del fondo de la sala 24).
    """
    if game.flags.mouse_appeared:
        return game

    for event in game.level.events:
        if event.kind is not EventKind.MOUSE_APPEAR:
            continue
        if game.kid.room != event.room:
            continue
        mouse = Char(
            charid=CharId.MOUSE,
            room=event.room,
            curr_col=0,
            curr_row=game.kid.curr_row,
            direction=int(Direction.RIGHT),
            curr_seq_id=int(Seq.RUN),
            action=Action.RUN_JUMP,
            hp_curr=1,
            hp_max=1,
        )
        new_flags = replace(game.flags, mouse_appeared=True)
        # Marca todas las gates de la sala que no tengan plate vinculada
        # como abiertas — el mouse las activa físicamente.
        new_state = game.state
        room = game.level.room(event.room)
        for c in range(10):
            for r in range(3):
                tile, _ = room.tile_at(c, r)
                if tile is not Tile.GATE:
                    continue
                gate_coord = (event.room, c, r)
                if game.level.plates_for_gate(gate_coord):
                    continue
                new_state = new_state.with_state(gate_coord, 7).with_gate_open(gate_coord)
        return replace(game, others=(*game.others, mouse), flags=new_flags, state=new_state)
    return game
