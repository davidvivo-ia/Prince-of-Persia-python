"""Bridge — detecta transiciones entre Games consecutivos y dispara SFX.

Centraliza la lógica de "qué sonido toca este tick" comparando el
estado previo y el actual. Mantiene el dominio puro y permite mute
total con un solo flag.
"""

from __future__ import annotations

from pop2026canon.domain.actions import Action, Seq, SwordStatus
from pop2026canon.domain.game import Game, GameStatus
from pop2026canon.infrastructure.audio import Beeper

# IDs de SFX en `infrastructure.audio`
SND_FOOTSTEP = 1
SND_JUMP = 2
SND_LAND_SOFT = 3
SND_LAND_HARD = 4
SND_GRAB = 5
SND_CLIMB = 6
SND_STRIKE = 7
SND_DEATH = 8
SND_DRINK = 9
SND_SPIKE = 10
SND_CHOMP = 11
SND_LOOSE_CRACK = 12
SND_HURT = 20
SND_CLASH = 21
SND_PARRY = 22
SND_GATE_OPEN = 23
SND_GATE_CLOSE = 24
SND_PLATE = 25
SND_PICKUP_SWORD = 26
SND_VICTORY_LEVEL = 27
SND_VICTORY_FINAL = 28
SND_MIRROR_BREAK = 29
SND_SHADOW_APPEAR = 30


def play_transitions(beeper: Beeper, prev: Game, now: Game) -> None:
    """Compara dos frames consecutivos y dispara los SFX correspondientes."""
    pp, pn = prev.kid, now.kid

    # Transiciones de acción/secuencia
    if pp.curr_seq_id != pn.curr_seq_id:
        if pn.curr_seq_id == int(Seq.RUN_JUMP) or pn.curr_seq_id == int(Seq.STANDING_JUMP):
            beeper.play(SND_JUMP)
        elif pn.curr_seq_id == int(Seq.GRAB_LEDGE_MIDAIR):
            beeper.play(SND_GRAB)
        elif pn.curr_seq_id == int(Seq.CLIMB_UP):
            beeper.play(SND_CLIMB)
        elif pn.curr_seq_id == int(Seq.STRIKE):
            beeper.play(SND_STRIKE)
        elif pn.curr_seq_id == int(Seq.SOFT_LAND):
            beeper.play(SND_LAND_SOFT)
        elif pn.curr_seq_id == int(Seq.SPIKED):
            beeper.play(SND_SPIKE)
        elif pn.curr_seq_id == int(Seq.CHOMPED):
            beeper.play(SND_CHOMP)
        elif pn.curr_seq_id in (int(Seq.DYING), int(Seq.STABBED_TO_DEATH)):
            beeper.play(SND_DEATH)
        elif pn.curr_seq_id == int(Seq.DRINK):
            beeper.play(SND_DRINK)

    # Daño recibido (HP bajó sin cambio de seq)
    if pn.hp_curr < pp.hp_curr and pn.action is Action.HURT:
        beeper.play(SND_HURT)

    # Espada recogida
    if (
        pp.sword == SwordStatus.SHEATHED
        and pn.sword == SwordStatus.DRAWN
        and not prev.flags.sword_picked
    ):
        beeper.play(SND_PICKUP_SWORD)

    # Gate abierta / cerrada (cambio en set)
    if len(now.state.open_gates) > len(prev.state.open_gates):
        beeper.play(SND_GATE_OPEN)
    elif len(now.state.open_gates) < len(prev.state.open_gates):
        beeper.play(SND_GATE_CLOSE)

    # Loose floor cae
    if len(now.state.fallen_floors) > len(prev.state.fallen_floors):
        beeper.play(SND_LOOSE_CRACK)

    # Shadow events
    if now.flags.shadow_initialized and not prev.flags.shadow_initialized:
        beeper.play(SND_SHADOW_APPEAR)
    if now.flags.shadow_fused and not prev.flags.shadow_fused:
        beeper.play(SND_MIRROR_BREAK)

    # Game status transitions
    if prev.status is not now.status:
        if now.status is GameStatus.WON_LEVEL:
            beeper.play(SND_VICTORY_LEVEL)
        elif now.status is GameStatus.WON_GAME:
            beeper.play(SND_VICTORY_FINAL)
        elif now.status is GameStatus.LOST_DIED:
            beeper.play(SND_DEATH)
