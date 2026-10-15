"""Skeleton — char inmortal del nivel 3.

Trigger: el kid pisa la columna específica del SKELETON_WAKE event.
A partir de ahí, el char `CharId.SKELETON` se mueve hacia el kid y
ataca. Su mortalidad se gestiona en :mod:`pop2026canon.domain.combat`
(`take_hp` con CharId.SKELETON → hp=1 + HURT, nunca muere).
"""

from __future__ import annotations

from dataclasses import replace

from pop2026canon.domain.actions import Action, Direction, Seq
from pop2026canon.domain.chars import Char, CharId
from pop2026canon.domain.game import Game
from pop2026canon.domain.level import EventKind


def trigger_skeleton_wake(game: Game) -> Game:
    """Evalúa el evento SKELETON_WAKE del nivel actual."""
    if game.flags.skeleton_woke:
        return game

    for event in game.level.events:
        if event.kind is not EventKind.SKELETON_WAKE:
            continue
        if game.kid.room != event.room:
            continue
        if game.kid.curr_col != event.col:
            continue
        # Spawn skeleton en la misma sala, al lado del kid
        spawn_col = max(0, min(9, event.col + 2))
        from pop2026canon.domain.actions import SwordStatus

        skel = Char(
            charid=CharId.SKELETON,
            room=event.room,
            curr_col=spawn_col,
            curr_row=game.kid.curr_row,
            direction=int(Direction.LEFT),
            curr_seq_id=int(Seq.ENGARDE),
            frame=158,
            action=Action.STAND,
            sword=SwordStatus.DRAWN,
            skill=2,
            hp_curr=3,
            hp_max=3,
        )
        new_flags = replace(game.flags, skeleton_woke=True)
        return replace(game, others=(*game.others, skel), flags=new_flags)
    return game


def step_skeleton_ai(game: Game) -> Game:
    """El esqueleto combate con la IA canon de guards (``guard.py``):
    aquí ya no hay nada que hacer. Se conserva por compatibilidad."""
    return game
