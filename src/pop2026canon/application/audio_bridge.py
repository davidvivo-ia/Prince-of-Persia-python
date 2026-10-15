"""Puente estado → sonido.

Compara dos ticks consecutivos (y los eventos visuales de ese tick) y
dispara los SFX, panoramizados según dónde ocurren en la sala. El
dominio sigue puro: aquí sólo se *escucha* lo que ya pasó.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from pop2026canon.domain.actions import Seq
from pop2026canon.domain.combat import is_hostile
from pop2026canon.domain.game import Game, GameStatus
from pop2026canon.domain.tiles import Tile
from pop2026canon.infrastructure.audio import (
    SND_CHOMP,
    SND_CLIMB,
    SND_DEATH,
    SND_DRINK,
    SND_FOOTSTEP,
    SND_GATE_CLOSE,
    SND_GATE_OPEN,
    SND_GRAB,
    SND_HIT_FLESH,
    SND_HURT,
    SND_JUMP,
    SND_LAND_HARD,
    SND_LAND_SOFT,
    SND_LOOSE_CRACK,
    SND_MIRROR_BREAK,
    SND_PARRY,
    SND_PICKUP_SWORD,
    SND_PLATE,
    SND_SHADOW_APPEAR,
    SND_SPIKE,
    SND_STRIKE,
    SND_TILE_CRASH,
    SND_VICTORY_FINAL,
    SND_VICTORY_LEVEL,
)

if TYPE_CHECKING:
    from pop2026canon.presentation.fx import FxEvent

# Compatibilidad: IDs que otros módulos importaban de aquí.
SND_LAND = SND_LAND_SOFT

_ROOM_PX = 640


class Player(Protocol):
    def play(self, sfx_id: int, pan: float = 0.0, volume: float = 1.0) -> None: ...


def _pan_px(x: float) -> float:
    return max(-0.8, min(0.8, (x / _ROOM_PX) * 2 - 1))


def _pan_col(col: int) -> float:
    return _pan_px(col * 64 + 32)


def _pan_char(col: int, x: int) -> float:
    return _pan_px(col * 64 + 10 + x * 3)


def play_transitions(
    player: Player, prev: Game, now: Game, events: list[FxEvent] | None = None
) -> None:
    """Dispara los SFX de este tick."""
    from pop2026canon.presentation.fx import FxKind

    pp, pn = prev.kid, now.kid
    kid_pan = _pan_char(pn.curr_col, pn.x)

    if pp.curr_seq_id != pn.curr_seq_id:
        s = pn.curr_seq_id
        if s in (int(Seq.RUN_JUMP), int(Seq.STANDING_JUMP), int(Seq.STANDING_JUMP_FORWARD)):
            player.play(SND_JUMP, kid_pan)
        elif s in (int(Seq.GRAB_LEDGE_MIDAIR), int(Seq.JUMP_UP_GRAB)):
            player.play(SND_GRAB, kid_pan)
        elif s in (int(Seq.CLIMB_UP), int(Seq.CLIMB_DOWN)):
            player.play(SND_CLIMB, kid_pan, 0.8)
        elif s in (int(Seq.STRIKE), int(Seq.BLOCK_TO_STRIKE)):
            player.play(SND_STRIKE, kid_pan)
        elif s == int(Seq.SOFT_LAND):
            player.play(SND_LAND_SOFT, kid_pan)
        elif s in (int(Seq.MED_LAND), int(Seq.HARD_LAND)):
            player.play(SND_LAND_HARD, kid_pan)
        elif s == int(Seq.SPIKED):
            player.play(SND_SPIKE, kid_pan)
        elif s in (int(Seq.STABBED_TO_DEATH), int(Seq.DYING)):
            player.play(SND_DEATH, kid_pan)

    # Estocadas de los enemigos visibles
    room = pn.room
    for i, c in enumerate(now.others):
        if c.room != room or i >= len(prev.others) or not is_hostile(c):
            continue
        p = prev.others[i]
        if p.curr_seq_id != c.curr_seq_id and c.curr_seq_id in (
            int(Seq.GUARD_STRIKE),
            int(Seq.BLOCK_TO_STRIKE),
        ):
            player.play(SND_STRIKE, _pan_char(c.curr_col, c.x), 0.8)

    for ev in events or ():
        pan = _pan_px(ev.x)
        k = ev.kind
        if k is FxKind.STEP:
            player.play(SND_FOOTSTEP, pan, 0.5)
        elif k is FxKind.HIT:
            player.play(SND_HIT_FLESH, pan)
            if ev.on_kid:
                player.play(SND_HURT, pan, 0.8)
        elif k is FxKind.PARRY:
            player.play(SND_PARRY, pan)
        elif k is FxKind.CRASH:
            player.play(SND_TILE_CRASH, pan)
        elif k is FxKind.CRUMBLE:
            player.play(SND_LOOSE_CRACK, pan)
        elif k is FxKind.GATE_SLAM:
            player.play(SND_GATE_CLOSE, pan)
        elif k is FxKind.SWORD:
            player.play(SND_PICKUP_SWORD, pan)
        elif k is FxKind.POTION:
            player.play(SND_DRINK, pan)
        elif k is FxKind.EXIT_OPEN:
            player.play(SND_GATE_OPEN, pan, 0.7)
        elif k is FxKind.BLOOD:
            player.play(SND_HIT_FLESH, pan)

    _trap_sounds(player, prev, now)

    if now.flags.shadow_initialized and not prev.flags.shadow_initialized:
        player.play(SND_SHADOW_APPEAR)
    if now.flags.shadow_fused and not prev.flags.shadow_fused:
        player.play(SND_MIRROR_BREAK)

    if prev.status is not now.status:
        if now.status is GameStatus.WON_LEVEL:
            player.play(SND_VICTORY_LEVEL)
        elif now.status is GameStatus.WON_GAME:
            player.play(SND_VICTORY_FINAL)


def _trap_sounds(player: Player, prev: Game, now: Game) -> None:
    """Mecanismos de la sala visible: cuchillas, pinchos, rejas, placas."""
    room_id = now.kid.room
    if not (1 <= room_id <= len(now.level.rooms)):
        return
    room = now.level.room(room_id)
    st_p, st_n = prev.state, now.state
    for r in range(3):
        for c in range(10):
            tile, _ = room.tile_at(c, r)
            coord = (room_id, c, r)
            if tile is Tile.CHOMPER:
                if (st_n.state_at(coord) & 0x7F) == 2 and (st_p.state_at(coord) & 0x7F) != 2:
                    player.play(SND_CHOMP, _pan_col(c), 0.8)
            elif tile is Tile.SPIKE:
                if st_p.state_at(coord) == 0 and st_n.state_at(coord) == 1:
                    player.play(SND_SPIKE, _pan_col(c), 0.7)
            elif tile is Tile.LOOSE:
                if st_p.state_at(coord) == 0 and st_n.state_at(coord) != 0:
                    player.play(SND_LOOSE_CRACK, _pan_col(c), 0.35)
            elif (
                tile is Tile.GATE
                and coord in st_n.opening_gates
                and coord not in st_p.opening_gates
            ):
                player.play(SND_GATE_OPEN, _pan_col(c), 0.8)
    k, pk = now.kid, prev.kid
    moved = (k.curr_col, k.curr_row) != (pk.curr_col, pk.curr_row)
    if (
        moved
        and 0 <= k.curr_row < 3
        and 0 <= k.curr_col < 10
        and room.tile_at(k.curr_col, k.curr_row)[0] in (Tile.OPENER, Tile.CLOSER)
    ):
        player.play(SND_PLATE, _pan_col(k.curr_col), 0.8)
