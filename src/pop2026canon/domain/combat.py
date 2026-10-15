"""Combate a espada canónico (``seg002.c``: ``check_hurting``,
``hurt_by_sword``, ``check_sword_hurt``).

El original no razona en celdas sino en píxeles: la estocada hiere en
el frame 154 ("poking") si el rival está a entre 12 (8 si va desarmado)
y 28 px por delante; en los frames 153-154 la estocada puede ser PARADA
si el rival tiene la espada en posición de parada (frames 150 / 161),
y entonces es el atacante quien retrocede (seq 69). Un rival desarmado
muere de una estocada; armado pierde 1 HP y se tambalea (seq 74).

La distancia es ``char_opp_dist``: ``opp.x - char.x`` en el sentido
hacia el que mira ``char`` (+13 si se miran de frente). Las unidades
coinciden con las del original (``TILE_SIZEX`` = 14 por celda).
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from pop2026canon.domain.actions import Action, Direction, Seq, SwordStatus
from pop2026canon.domain.chars import GUARD_SKILLS, Char, CharId
from pop2026canon.domain.constants import TILE_SIZE_X

STRIKE_REACH: int = 29
"""Canon: la estocada alcanza a menos de 29 px."""

MIN_HURT_RANGE_ARMED: int = 12
MIN_HURT_RANGE_UNARMED: int = 8
"""Canon ``check_hurting``: demasiado cerca no se hiere (la hoja pasa)."""

POKE_FRAME: int = 154
"""Frame en el que la punta alcanza al rival."""

HIT_FRAMES: frozenset[int] = frozenset({153, 154})
"""Frames del atacante en los que la estocada puede herir o ser parada."""

PARRY_FRAMES: frozenset[int] = frozenset({150, 161})
"""Frames del rival con la espada en posición de parada."""

READY_FRAMES: frozenset[int] = frozenset({157, 158, 165, 170, 171})
"""Frames desde los que se puede atacar / parar / avanzar (canon
``sword_strike`` / ``parry`` / ``forward_with_sword``)."""

HOSTILE: frozenset[CharId] = frozenset(
    {CharId.GUARD, CharId.GUARD_VARIANT, CharId.SKELETON, CharId.VIZIER, CharId.SHADOW}
)
"""Chars que combaten contra el kid (la sombra sólo cuando desenvaina)."""


def is_hostile(char: Char) -> bool:
    if char.charid is CharId.SHADOW:
        return char.sword == SwordStatus.DRAWN
    return char.charid in HOSTILE


def abs_x(char: Char) -> int:
    """x absoluta dentro de la sala (14 unidades por celda)."""
    return char.curr_col * TILE_SIZE_X + char.x


def char_opp_dist(char: Char, opp: Char) -> int:
    """Canon ``char_opp_dist``: > 0 si ``opp`` está delante de ``char``,
    < 0 si está detrás; 999 si no comparten sala."""
    if char.room != opp.room:
        return 999
    distance = abs_x(opp) - abs_x(char)
    if char.direction == int(Direction.LEFT):
        distance = -distance
    if distance >= 0 and char.direction != opp.direction:
        distance += 13
    return distance


# ---------------------------------------------------------------------------
# Daño
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class HitResult:
    """Resultado de aplicar daño a un char."""

    char: Char
    """Char con HP actualizado y posible seq de muerte."""

    killed: bool
    """``True`` si este hit lo dejó sin HP."""


def _dead_by_sword(char: Char) -> Char:
    return replace(
        char,
        hp_curr=0,
        alive=0,
        action=Action.HURT,
        curr_seq_id=int(Seq.STABBED_TO_DEATH),
        curr_seq_idx=0,
        fall_x=0,
        fall_y=0,
    )


def take_hp(char: Char, amount: int = 1) -> HitResult:
    """Resta ``amount`` HP (canon ``take_hp``). Si llega a 0 el char
    muere (seq de desplome). El esqueleto es inmortal: se queda en 1."""
    if char.alive >= 0:
        return HitResult(char=char, killed=False)
    new_hp = max(0, char.hp_curr - amount)
    if new_hp == 0:
        if char.charid is CharId.SKELETON:
            return HitResult(char=replace(char, hp_curr=1), killed=False)
        return HitResult(char=_dead_by_sword(char), killed=True)
    return HitResult(char=replace(char, hp_curr=new_hp), killed=False)


def hurt_by_sword(victim: Char) -> Char:
    """Canon ``hurt_by_sword``: desarmado muere; armado pierde 1 HP y se
    tambalea (seq 74) — o muere si era su último HP. Si es un guard,
    entra en refractario (``refractimer[skill]``)."""
    if victim.alive >= 0:
        return victim
    if victim.sword != SwordStatus.DRAWN:
        return _dead_by_sword(victim)
    if victim.charid is CharId.SKELETON:
        staggered = victim
    else:
        result = take_hp(victim, 1)
        if result.killed:
            return result.char
        staggered = result.char
    refrac = staggered.refrac
    if staggered.charid is not CharId.KID:
        skill = max(0, min(len(GUARD_SKILLS) - 1, staggered.skill))
        refrac = GUARD_SKILLS[skill].refractory
    return replace(
        staggered,
        action=Action.STAND,
        curr_seq_id=int(Seq.HIT_BY_SWORD),
        curr_seq_idx=0,
        fall_x=0,
        fall_y=0,
        refrac=refrac,
    )


def heal(char: Char, amount: int = 1) -> Char:
    """Cura ``amount`` HP hasta el máximo del char."""
    return replace(char, hp_curr=min(char.hp_max, char.hp_curr + amount))


def heal_max(char: Char) -> Char:
    """Sube max HP +1 y rellena la vida (canon: poción azul grande).
    El máximo absoluto es ``MAX_HITP_ALLOWED`` (10)."""
    from pop2026canon.domain.constants import MAX_HITP_ALLOWED

    new_max = min(MAX_HITP_ALLOWED, char.hp_max + 1)
    return replace(char, hp_max=new_max, hp_curr=new_max)


# ---------------------------------------------------------------------------
# Detección de impacto (canon check_hurting)
# ---------------------------------------------------------------------------


def is_in_strike_window(char: Char) -> bool:
    """``True`` si el char está en un frame en el que su estocada cuenta."""
    return char.frame in HIT_FRAMES


def is_in_block_window(char: Char) -> bool:
    """``True`` si el char tiene la espada en posición de parada."""
    return char.frame in PARRY_FRAMES


def can_strike(attacker: Char, target: Char) -> bool:
    """¿Está ``target`` al alcance de la estocada de ``attacker``? (misma
    sala y fila, delante, entre el mínimo y 28 px)."""
    if attacker.sword != SwordStatus.DRAWN:
        return False
    if attacker.room != target.room or attacker.curr_row != target.curr_row:
        return False
    d = char_opp_dist(attacker, target)
    min_range = (
        MIN_HURT_RANGE_ARMED if target.sword == SwordStatus.DRAWN else MIN_HURT_RANGE_UNARMED
    )
    return min_range <= d < STRIKE_REACH


@dataclass(frozen=True, slots=True)
class HurtCheck:
    attacker: Char
    opp: Char
    hurt: bool = False
    parried: bool = False


def check_hurting(attacker: Char, opp: Char) -> HurtCheck:
    """Canon ``check_hurting`` para un atacante y su rival.

    - Sin espada, otra fila u otra sala, o fuera de los frames 153/154:
      nada.
    - Rival parando (150/161) a menos de 29 px: la estocada es parada —
      el atacante retrocede (seq 69) y el rival queda en 161; si el
      atacante es un guard, ``justblocked = 4`` (su siguiente bloqueo
      usa ``impblockprob``).
    - Frame 154 y rival entre el mínimo y 28 px: el rival es herido.
    """
    if attacker.sword != SwordStatus.DRAWN or attacker.alive >= 0 or opp.alive >= 0:
        return HurtCheck(attacker, opp)
    if attacker.room != opp.room or attacker.curr_row != opp.curr_row:
        return HurtCheck(attacker, opp)
    if attacker.frame not in HIT_FRAMES:
        return HurtCheck(attacker, opp)
    d = char_opp_dist(attacker, opp)
    if 0 <= d < STRIKE_REACH and opp.frame in PARRY_FRAMES:
        new_attacker = replace(
            attacker, curr_seq_id=int(Seq.ATTACK_PARRIED), curr_seq_idx=0, action=Action.STAND
        )
        if attacker.charid is not CharId.KID:
            # Canon: al guard cuya estocada acaban de parar le cuesta
            # bloquear la réplica (impblockprob durante 4 ticks). Es la
            # ventana para vencer al visir: parar y contraatacar.
            new_attacker = replace(new_attacker, justblocked=4)
        new_opp = replace(opp, frame=161)
        return HurtCheck(new_attacker, new_opp, parried=True)
    if attacker.frame == POKE_FRAME:
        min_range = (
            MIN_HURT_RANGE_ARMED if opp.sword == SwordStatus.DRAWN else MIN_HURT_RANGE_UNARMED
        )
        if min_range <= d < STRIKE_REACH:
            return HurtCheck(attacker, hurt_by_sword(opp), hurt=True)
    return HurtCheck(attacker, opp)


@dataclass(frozen=True, slots=True)
class CombatResolution:
    """Resultado de aplicar un tick de combate entre kid y un enemigo."""

    kid: Char
    guard: Char
    kid_hit: bool = False
    guard_hit: bool = False
    kid_parried: bool = False
    """La estocada del kid fue parada."""
    guard_parried: bool = False
    """La estocada del guard fue parada."""


def resolve_combat(kid: Char, guard: Char) -> CombatResolution:
    """Un tick de intercambio de espadas (canon ``check_sword_hurting`` +
    ``check_sword_hurt``): ambas estocadas se evalúan sobre los frames
    de ESTE tick; si las dos conectan a la vez, sólo cuenta la del kid
    (el original anula el golpe recibido por el kid cuando el enemigo
    también ha sido alcanzado)."""
    by_guard = check_hurting(guard, kid)
    by_kid = check_hurting(kid, guard)
    new_kid, new_guard = kid, guard
    kid_hit = guard_hit = False
    # Paradas: afectan al atacante (recoil) y al que para (frame 161).
    if by_guard.parried:
        new_guard = replace(
            new_guard,
            curr_seq_id=by_guard.attacker.curr_seq_id,
            curr_seq_idx=0,
            action=Action.STAND,
            justblocked=by_guard.attacker.justblocked,
        )
        new_kid = replace(new_kid, frame=161)
    if by_kid.parried:
        new_kid = replace(new_kid, curr_seq_id=by_kid.attacker.curr_seq_id, curr_seq_idx=0)
        new_guard = replace(new_guard, frame=161)
    # Heridas (canon check_sword_hurt): el guard herido tiene prioridad.
    if by_kid.hurt:
        new_guard = hurt_by_sword(new_guard)
        guard_hit = True
    elif by_guard.hurt:
        new_kid = hurt_by_sword(new_kid)
        kid_hit = True
    return CombatResolution(
        kid=new_kid,
        guard=new_guard,
        kid_hit=kid_hit,
        guard_hit=guard_hit,
        kid_parried=by_kid.parried,
        guard_parried=by_guard.parried,
    )
