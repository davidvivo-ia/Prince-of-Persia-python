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
        skel = Char(
            charid=CharId.SKELETON,
            room=event.room,
            curr_col=spawn_col,
            curr_row=game.kid.curr_row,
            direction=int(Direction.LEFT),
            curr_seq_id=int(Seq.STAND),
            action=Action.STAND,
            hp_curr=3,
            hp_max=3,
        )
        new_flags = replace(game.flags, skeleton_woke=True)
        return replace(game, others=(*game.others, skel), flags=new_flags)
    return game


def step_skeleton_ai(game: Game) -> Game:
    """Cada tick: skeleton avanza hacia el kid y ataca si adyacente."""
    skel = game.find_char(CharId.SKELETON)
    if skel is None or skel.room != game.kid.room:
        return game

    dx = game.kid.curr_col - skel.curr_col
    if dx == 0:
        # Mismo col: ataca
        return _set_skeleton_seq(game, Seq.STRIKE)
    # Avanza
    new_dir = int(Direction.RIGHT) if dx > 0 else int(Direction.LEFT)
    new_col = skel.curr_col + (1 if dx > 0 else -1)
    new_col = max(0, min(9, new_col))
    new_skel = replace(skel, curr_col=new_col, direction=new_dir)
    new_others = tuple(new_skel if c.charid is CharId.SKELETON else c for c in game.others)
    return replace(game, others=new_others)


def _set_skeleton_seq(game: Game, seq: Seq) -> Game:
    skel = game.find_char(CharId.SKELETON)
    if skel is None:
        return game
    new_skel = replace(skel, curr_seq_id=int(seq), curr_seq_idx=0)
    new_others = tuple(new_skel if c.charid is CharId.SKELETON else c for c in game.others)
    return replace(game, others=new_others)
