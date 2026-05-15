"""Vizier (Jaffar) — char final del nivel 12.

CharId.VIZIER con HP=6 (tbl_guard_hp[13]). Se comporta como un guard
de skill máximo (11). Spawneado por VIZIER_INIT event.
"""

from __future__ import annotations

from dataclasses import replace

from pop2026canon.domain.actions import Action, Direction, Seq
from pop2026canon.domain.chars import Char, CharId
from pop2026canon.domain.constants import TBL_GUARD_HP
from pop2026canon.domain.game import Game
from pop2026canon.domain.level import EventKind


def trigger_vizier_spawn(game: Game) -> Game:
    """Evalúa el evento VIZIER_INIT del nivel actual."""
    if game.find_char(CharId.VIZIER) is not None:
        return game

    for event in game.level.events:
        if event.kind is not EventKind.VIZIER_INIT:
            continue
        if game.kid.room != event.room:
            continue
        # Spawn Vizier — char especial con HP máximo del nivel
        hp = TBL_GUARD_HP[min(13, game.level.number - 1)]
        vizier = Char(
            charid=CharId.VIZIER,
            room=event.room,
            curr_col=6,
            curr_row=game.kid.curr_row,
            direction=int(Direction.LEFT),
            curr_seq_id=int(Seq.STAND),
            action=Action.STAND,
            hp_curr=hp,
            hp_max=hp,
        )
        return replace(game, others=(*game.others, vizier))
    return game
