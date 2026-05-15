"""IA de los guards canónicos (`charid_2_guard`).

Cada guard actúa cada tick según un FSM simple:

- **Sin kid en sala**: idle (STAND).
- **Kid en misma sala, distinta row**: idle (no salta).
- **Kid en misma sala+row pero lejos (dist > 1)**: avanza un paso
  hacia el kid (canon: `advance_chance` por skill).
- **Kid adyacente (dist == 1) mirando hacia él**: ataca con `STRIKE`
  (canon: `prob_block` decide si bloquea antes; `prob_strike_after_block`
  decide contraataque).
- **Tras strike o block**: refractory_ticks de espera.

Es determinista: usa el tick_count del game + room_id como semilla del
PRNG para reproducibilidad.
"""

from __future__ import annotations

import random
from dataclasses import replace

from pop2026canon.domain.actions import Action, Direction, Seq, SwordStatus
from pop2026canon.domain.chars import GUARD_SKILLS, Char, CharId
from pop2026canon.domain.game import Game


def _seed_for(game: Game, guard_idx: int) -> int:
    """Semilla determinista por (tick, room, idx)."""
    return game.tick_count * 1009 + guard_idx * 17 + game.kid.room


def step_guards_ai(game: Game) -> Game:
    """Avanza la IA de cada guard en la sala del kid.

    Devuelve un nuevo Game con `others` actualizados.
    """
    new_others = list(game.others)
    for i, guard in enumerate(new_others):
        if guard.charid is not CharId.GUARD:
            continue
        if guard.alive >= 0:
            continue
        new_others[i] = _step_one_guard(guard, game, _seed_for(game, i))
    return replace(game, others=tuple(new_others))


def _step_one_guard(guard: Char, game: Game, seed: int) -> Char:
    """Decide la acción del guard este tick."""
    kid = game.kid
    # Sin kid en la misma sala: idle.
    if guard.room != kid.room:
        return guard
    # Kid muerto: idle.
    if kid.alive >= 0:
        return guard
    # Skill bounds.
    skill_idx = max(0, min(len(GUARD_SKILLS) - 1, guard.skill))
    skill = GUARD_SKILLS[skill_idx]
    rng = random.Random(seed)

    same_row = guard.curr_row == kid.curr_row
    dx = kid.curr_col - guard.curr_col

    # Si está en STRIKE en curso, deja que play_seq avance la animación.
    if guard.curr_seq_id == int(Seq.STRIKE):
        return guard

    if not same_row:
        # Mira al kid pero no actúa.
        return _face_kid(guard, dx)

    if dx == 0:
        # Mismo col: ataca o se queda.
        return _start_strike(guard, kid)
    if abs(dx) == 1:
        # Adyacente: gira hacia el kid; si mira hacia él, ataca según skill.
        guard = _face_kid(guard, dx)
        # Bloquea si el kid está atacando.
        if kid.curr_seq_id == int(Seq.STRIKE) and rng.random() < skill.prob_block:
            return _start_block(guard)
        # Ataca con probabilidad alta cuando adyacente.
        if rng.random() < (0.4 + 0.05 * skill_idx):
            return _start_strike(guard, kid)
        return guard
    # Más lejos: avanza un paso si la probabilidad lo permite.
    if rng.random() < skill.advance_chance:
        return _step_toward(guard, dx)
    return _face_kid(guard, dx)


def _face_kid(guard: Char, dx: int) -> Char:
    if dx == 0:
        return guard
    new_dir = int(Direction.RIGHT) if dx > 0 else int(Direction.LEFT)
    if guard.direction == new_dir:
        return guard
    return replace(guard, direction=new_dir)


def _step_toward(guard: Char, dx: int) -> Char:
    step = 1 if dx > 0 else -1
    new_col = max(0, min(9, guard.curr_col + step))
    return replace(
        guard,
        curr_col=new_col,
        direction=int(Direction.RIGHT) if dx > 0 else int(Direction.LEFT),
    )


def _start_strike(guard: Char, kid: Char) -> Char:
    # Sólo ataca si tiene espada (canon: los guards siempre la traen).
    if guard.sword != SwordStatus.DRAWN:
        return guard
    # Refractory: si acaba de atacar/bloquear, espera.
    if guard.repeat > 0:
        return replace(guard, repeat=guard.repeat - 1)
    dx = kid.curr_col - guard.curr_col
    new_dir = (
        guard.direction if dx == 0 else (int(Direction.RIGHT) if dx > 0 else int(Direction.LEFT))
    )
    # `repeat` se usa como cooldown contador: ticks antes del próximo strike.
    skill_idx = max(0, min(len(GUARD_SKILLS) - 1, guard.skill))
    cooldown = GUARD_SKILLS[skill_idx].refractory
    return replace(
        guard,
        direction=new_dir,
        action=Action.STAND,
        curr_seq_id=int(Seq.STRIKE),
        curr_seq_idx=0,
        frame=0,  # play_seq avanzará hasta 165 a su ritmo
        repeat=cooldown,
    )


def _start_block(guard: Char) -> Char:
    skill_idx = max(0, min(len(GUARD_SKILLS) - 1, guard.skill))
    cooldown = max(2, GUARD_SKILLS[skill_idx].refractory // 2)
    return replace(
        guard,
        action=Action.STAND,
        curr_seq_id=int(Seq.BLOCK_STRIKE),
        curr_seq_idx=0,
        frame=161,
        repeat=cooldown,
    )
