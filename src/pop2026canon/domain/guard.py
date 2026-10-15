"""IA de los enemigos con espada (canon ``seg002.c``:
``autocontrol_guard_active`` y ``seg003.c``: ``check_can_guard_see_kid``).

Cada tick, el enemigo que comparte sala con el kid decide como en el
original, con distancias en píxeles (``char_opp_dist``) y las tablas de
probabilidad por skill (sobre 255):

- ¿Le ve? Misma fila sin muros entre medias → 2 ("y viene"); si por
  medio hay una losa suelta, cuchillas, una gate cerrada o un hueco →
  1 ("le ve pero no viene"); si no, 0.
- A menos de 12 px: se aparta (retrocede si miran al mismo lado, avanza
  si no). Entre 12 y 34: si el kid va armado, bloquea sus estocadas
  (``blockprob`` / ``impblockprob`` tras una parada), y cuando no está
  en refractario ataca (``strikeprob``, ``restrikeprob`` desde la
  parada) a 12-28 px o avanza (``advprob``) fuera de ese rango; si va
  desarmado, estocada directa. A 35 o más: si el kid viene corriendo o
  saltando hacia él, estocada preventiva; si no, avanza mientras haya
  suelo delante.
- Si deja de verle porque cayó de la fila, le sigue por el borde si
  es seguro (``guard_follows_kid_down``).

Las decisiones sólo arrancan secuencias desde los frames "en guardia"
(157/158/165/170/171) o de parada (150/161 → estocada tras parar): si
el guard está a mitad de una animación, la decisión se pierde — como en
el original.

Determinista: PRNG sembrado con (tick, índice, sala).
"""

from __future__ import annotations

import random
from dataclasses import replace

from pop2026canon.domain.actions import Action, Direction, Seq, SwordStatus
from pop2026canon.domain.chars import GUARD_SKILLS, Char
from pop2026canon.domain.combat import PARRY_FRAMES, READY_FRAMES, char_opp_dist, is_hostile
from pop2026canon.domain.game import Game
from pop2026canon.domain.level import Level
from pop2026canon.domain.tiles import Tile

INACTIVE_FRAME: int = 166
"""Frame del guard en reposo (``alertstand``)."""

_RUN_FRAMES = range(7, 15)
_RUN_JUMP_FRAMES = range(34, 44)
_FALL_CROUCH_FRAMES = range(102, 118)


def _seed_for(game: Game, guard_idx: int) -> int:
    return game.tick_count * 1009 + guard_idx * 17 + game.kid.room


def _skill(guard: Char):  # type: ignore[no-untyped-def]
    return GUARD_SKILLS[max(0, min(len(GUARD_SKILLS) - 1, guard.skill))]


# ---------------------------------------------------------------------------
# Línea de visión (canon check_can_guard_see_kid)
# ---------------------------------------------------------------------------


def can_guard_see_kid(level: Level, guard: Char, kid: Char, open_gates: frozenset) -> int:  # type: ignore[type-arg]
    """0: no le ve · 1: le ve pero no viene · 2: le ve y viene."""
    if kid.alive >= 0 or guard.alive >= 0:
        return 0
    if kid.room != guard.room or kid.curr_row != guard.curr_row:
        return 0
    if not (1 <= kid.room <= len(level.rooms)):
        return 0
    room = level.room(kid.room)
    left, right = sorted((kid.curr_col, guard.curr_col))
    left = max(0, left)
    right = min(9, right)
    if room.tile_at(left, kid.curr_row)[0] is Tile.CHOMPER:
        left += 1
    if right >= 0 and room.tile_at(right, kid.curr_row)[0] in (Tile.GATE, Tile.DOORTOP):
        right -= 1
    result = 2
    for col in range(left, right + 1):
        tile, modifier = room.tile_at(col, kid.curr_row)
        if tile in (Tile.WALL, Tile.DOORTOP_WITH_FLOOR, Tile.DOORTOP):
            return 0
        closed_gate = (
            tile is Tile.GATE and modifier < 7 and (kid.room, col, kid.curr_row) not in open_gates
        )
        if tile in (Tile.LOOSE, Tile.CHOMPER, Tile.EMPTY) or closed_gate:
            result = 1
    return result


# ---------------------------------------------------------------------------
# Decisión (canon autocontrol_guard_active)
# ---------------------------------------------------------------------------


def _decide(guard: Char, kid: Char, game: Game, see: int, rng: random.Random) -> set[str]:
    """Devuelve el conjunto de "teclas" que pulsa el guard este tick:
    ``forward``, ``backward``, ``up`` (parar), ``shift`` (estocada)."""
    moves: set[str] = set()
    skill = _skill(guard)
    frame = guard.frame
    if frame == INACTIVE_FRAME or frame < 150 or see == 1:
        return moves
    if see == 0:
        if guard.droppedout:
            moves |= _follow_kid_down(guard, kid, game)
        return moves

    d = char_opp_dist(guard, kid)
    if d >= 12 and kid.frame in _FALL_CROUCH_FRAMES and kid.action is Action.BUMPED:
        return moves
    if d < 35:
        if (guard.sword != SwordStatus.DRAWN and d < 8) or d < 12:
            moves.add("backward" if guard.direction == kid.direction else "forward")
            return moves
        # kid a la vista (12..34)
        if kid.sword == SwordStatus.DRAWN:
            if d < 10 or d >= 29:
                _guard_advance(guard, kid, skill, rng, moves)
            else:
                # bloquear la estocada que llega
                if kid.frame in (152, 153, 162):
                    prob = skill.prob_imp_block if guard.justblocked else skill.prob_block
                    if rng.random() < prob:
                        moves.add("up")
                if guard.refrac == 0:
                    if d < 12 or d >= 29:
                        _guard_advance(guard, kid, skill, rng, moves)
                    else:
                        _guard_strike(guard, kid, skill, rng, moves)
        elif guard.refrac == 0:
            moves.add("shift" if d < 29 else "forward")
        return moves
    # lejos (>= 35)
    if guard.refrac != 0:
        return moves
    if guard.direction != kid.direction:
        if kid.frame in _RUN_FRAMES:
            if d < 40:
                moves.add("shift")
            return moves
        if kid.frame in _RUN_JUMP_FRAMES:
            if d < 50:
                moves.add("shift")
            return moves
    moves |= _kid_far(guard, game)
    return moves


def _guard_advance(guard: Char, kid: Char, skill, rng: random.Random, moves: set[str]) -> None:  # type: ignore[no-untyped-def]
    # Canon: los guards de skill > 0 no avanzan mientras el kid está
    # en plena estocada.
    if (guard.skill == 0 or kid.strike_timer == 0) and rng.random() < skill.advance_chance:
        moves.add("forward")


def _guard_strike(guard: Char, kid: Char, skill, rng: random.Random, moves: set[str]) -> None:  # type: ignore[no-untyped-def]
    if kid.frame in (169, 151):
        return  # el kid empieza a parar / a atacar: no se lanza
    prob = skill.prob_strike_after_block if guard.frame in PARRY_FRAMES else skill.prob_strike
    if rng.random() < prob:
        moves.add("shift")


def _floor_ahead(game: Game, guard: Char, steps: int) -> bool:
    from pop2026canon.domain.physics import has_floor_at

    fwd = 1 if guard.direction == int(Direction.RIGHT) else -1
    col = guard.curr_col + fwd * steps
    if not (0 <= col < 10):
        return True  # la sala vecina lo resuelve la física
    return has_floor_at(game.level, guard.room, col, guard.curr_row, game.state.fallen_floors)


def _kid_far(guard: Char, game: Game) -> set[str]:
    if _floor_ahead(game, guard, 1) or _floor_ahead(game, guard, 2):
        return {"forward"}
    return {"backward"}


def _follow_kid_down(guard: Char, kid: Char, game: Game) -> set[str]:
    """Canon ``guard_follows_kid_down``: se tira por el borde tras el
    kid si no hay muro delante, el hueco está justo delante, abajo hay
    suelo (ni pinchos ni losa suelta) y el kid está una fila más abajo."""
    from pop2026canon.domain.physics import blocks_body_at, has_floor_at

    if kid.action in (Action.HANG_CLIMB, Action.HANG_STRAIGHT):
        return set()
    fwd = 1 if guard.direction == int(Direction.RIGHT) else -1
    col = guard.curr_col + fwd
    room = game.level.room(guard.room)
    safe = True
    if not (0 <= col < 10) or blocks_body_at(room, col, guard.curr_row, game.state.open_gates):
        safe = False
    elif not has_floor_at(game.level, guard.room, col, guard.curr_row, game.state.fallen_floors):
        below_row = guard.curr_row + 1
        if below_row > 2:
            safe = False
        else:
            below, _ = room.tile_at(col, below_row)
            if below in (Tile.SPIKE, Tile.LOOSE, Tile.WALL) or not has_floor_at(
                game.level, guard.room, col, below_row, game.state.fallen_floors
            ):
                safe = False
        if guard.curr_row + 1 != kid.curr_row:
            safe = False
    return {"forward"} if safe else {"backward"}


# ---------------------------------------------------------------------------
# Aplicar la decisión (canon control / swordfight para el guard)
# ---------------------------------------------------------------------------


def _start(char: Char, seq: Seq) -> Char:
    return replace(char, curr_seq_id=int(seq), curr_seq_idx=0, action=Action.STAND)


def _apply_moves(guard: Char, kid: Char, moves: set[str]) -> Char:
    frame = guard.frame
    if "shift" in moves:
        if frame in READY_FRAMES:
            return _start(guard, Seq.GUARD_STRIKE)
        if frame in PARRY_FRAMES:
            return _start(guard, Seq.BLOCK_TO_STRIKE)
    if "up" in moves:
        # Canon parry() para un guard: sólo desde la guardia y sólo si
        # el kid está en el frame 152 (la estocada ya lanzada).
        if frame in (158, 170, 171, 168, 165):
            if char_opp_dist(guard, kid) >= 32:
                return _start(guard, Seq.RETREAT)
            if kid.frame == 152:
                return _start(guard, Seq.BLOCK_STRIKE)
        elif frame == 167:
            return _start(guard, Seq.PARRY_AFTER_STRIKE)
    if "forward" in moves and frame in (158, 170, 171):
        return _start(guard, Seq.GUARD_ADVANCE)
    if "backward" in moves and frame in (158, 170, 171):
        return _start(guard, Seq.RETREAT)
    return guard


def _tick_timers(guard: Char) -> Char:
    if guard.refrac or guard.justblocked:
        return replace(
            guard,
            refrac=max(0, guard.refrac - 1),
            justblocked=max(0, guard.justblocked - 1),
        )
    return guard


def _face_kid(guard: Char, kid: Char) -> Char:
    """Un guard en reposo que ve al kid se pone en guardia mirándole."""
    new_dir = int(Direction.RIGHT) if kid.curr_col > guard.curr_col else int(Direction.LEFT)
    if kid.curr_col == guard.curr_col:
        new_dir = guard.direction
    return replace(guard, direction=new_dir, curr_seq_id=int(Seq.ENGARDE), curr_seq_idx=0)


def step_guards_ai(game: Game) -> Game:
    """Avanza la IA de cada enemigo armado de la sala del kid."""
    new_others = list(game.others)
    kid = game.kid
    for i, original in enumerate(new_others):
        if not is_hostile(original) or original.alive >= 0:
            continue
        guard = _tick_timers(original)
        if guard.room != kid.room:
            new_others[i] = guard
            continue
        see = can_guard_see_kid(game.level, guard, kid, game.state.open_gates)
        if guard.frame == INACTIVE_FRAME or guard.frame < 150:
            # Reposo: al ver al kid, en guardia (canon move_down_forw →
            # draw_sword). Si sigue sin verle, no hace nada.
            if see != 0 and guard.curr_seq_id not in (int(Seq.ENGARDE), int(Seq.DRAW_SWORD)):
                guard = _face_kid(guard, kid)
            new_others[i] = guard
            continue
        # Cuando el kid cae de la fila, el guard que le veía le sigue.
        if see == 0 and kid.curr_row == guard.curr_row + 1 and kid.alive < 0:
            guard = replace(guard, droppedout=True)
        elif see != 0:
            guard = replace(guard, droppedout=False)
        # Un guard en guardia encara al kid si le ve a su espalda.
        if see == 2 and char_opp_dist(guard, kid) < -4 and guard.frame in READY_FRAMES:
            guard = _start(guard, Seq.TURN_WITH_SWORD)
            new_others[i] = guard
            continue
        rng = random.Random(_seed_for(game, i))
        moves = _decide(guard, kid, game, see, rng)
        guard = _apply_moves(guard, kid, moves)
        if "backward" in moves and see == 0 and guard.droppedout:
            guard = replace(guard, droppedout=False)
        new_others[i] = guard
    return replace(game, others=tuple(new_others))
