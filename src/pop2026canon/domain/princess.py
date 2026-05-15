"""Princess + Mouse — chars de la cinemática final."""

from __future__ import annotations

from dataclasses import replace

from pop2026canon.domain.actions import Action, Direction, Seq
from pop2026canon.domain.chars import Char, CharId
from pop2026canon.domain.game import Game
from pop2026canon.domain.level import EventKind


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
    """L8: ratón aparece para abrir gate."""
    if game.flags.mouse_appeared:
        return game

    for event in game.level.events:
        if event.kind is EventKind.MOUSE_APPEAR:
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
            return replace(game, others=(*game.others, mouse), flags=new_flags)
    return game
