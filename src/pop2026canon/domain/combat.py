"""Sistema de combate cuerpo a cuerpo canónico.

Reglas canon (verificadas en `docs/audit.md §4`):

- HP: ``take_hp(char, amount)`` resta y dispara DYING si llega a 0.
- Strike: el char en ventana ``STRIKE_WINDOW`` (frames 165-167) hace
  daño al rival si:
  - Está en la sala y fila adyacente
  - El rival NO está en ``BLOCK_WINDOW`` (frames 161-164)
- Skeleton (``charid_4_skeleton``): inmortal — con hp=0 vuelve a hp=1
  y entra en estado HURT.
- Vizier (``charid_6_vizier``): char especial con HP=6 (último entry
  de ``tbl_guard_hp``).

Las ventanas son de :data:`pop2026canon.domain.seqtbl.STRIKE_WINDOW` /
``BLOCK_WINDOW``.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from pop2026canon.domain.actions import Action, Seq
from pop2026canon.domain.chars import Char, CharId
from pop2026canon.domain.seqtbl import BLOCK_WINDOW, STRIKE_WINDOW


@dataclass(frozen=True, slots=True)
class HitResult:
    """Resultado de aplicar daño a un char."""

    char: Char
    """Char con HP actualizado y posible seq DYING."""

    killed: bool
    """``True`` si este hit lo dejó sin HP."""


def take_hp(char: Char, amount: int = 1) -> HitResult:
    """Aplica ``amount`` puntos de daño al char.

    Canon:
    - HP normal baja `amount`. Si llega a 0:
      - Char normal (kid/guard/vizier/princess): inicia seq DYING y
        marca ``alive >= 0``.
      - Skeleton (``CharId.SKELETON``): inmortal — restablece a hp=1
        con animación HURT.

    Args:
        char: Personaje atacado.
        amount: Puntos de HP a restar (default 1).

    Returns:
        ``HitResult`` con el nuevo char y flag ``killed``.
    """
    if char.alive >= 0:
        return HitResult(char=char, killed=False)

    new_hp = max(0, char.hp_curr - amount)

    if new_hp == 0:
        if char.charid is CharId.SKELETON:
            # Inmortal: vuelve a HP=1 con estado HURT
            return HitResult(
                char=replace(
                    char,
                    hp_curr=1,
                    action=Action.HURT,
                    curr_seq_id=int(Seq.STAND),
                    curr_seq_idx=0,
                ),
                killed=False,
            )
        # Muerte real: action DYING + alive=0
        return HitResult(
            char=replace(
                char,
                hp_curr=0,
                action=Action.HURT,
                alive=0,
                curr_seq_id=int(Seq.STABBED_TO_DEATH),
                curr_seq_idx=0,
            ),
            killed=True,
        )

    return HitResult(
        char=replace(
            char,
            hp_curr=new_hp,
            action=Action.HURT,
        ),
        killed=False,
    )


def heal(char: Char, amount: int = 1) -> Char:
    """Cura ``amount`` HP hasta el máximo del char."""
    new_hp = min(char.hp_max, char.hp_curr + amount)
    return replace(char, hp_curr=new_hp)


def heal_max(char: Char) -> Char:
    """Sube max HP +1 y rellena la vida (canon: poción azul grande)."""
    return replace(char, hp_max=char.hp_max + 1, hp_curr=char.hp_max + 1)


# ---------------------------------------------------------------------------
# Detección de ventanas de combate
# ---------------------------------------------------------------------------


def is_in_strike_window(char: Char) -> bool:
    """``True`` si el frame actual del char está en la ventana de impacto."""
    return char.frame in STRIKE_WINDOW


def is_in_block_window(char: Char) -> bool:
    """``True`` si el frame actual del char está en la ventana de bloqueo."""
    return char.frame in BLOCK_WINDOW


# ---------------------------------------------------------------------------
# Adyacencia (chars en mismo room + fila + distancia 1 col)
# ---------------------------------------------------------------------------


def can_strike(attacker: Char, target: Char) -> bool:
    """``True`` si ``attacker`` está en posición para alcanzar ``target``
    con su sable.

    - Misma sala
    - Misma fila
    - Distancia horizontal exactamente 1 col (canon strike reach)
    - Attacker mira hacia el target
    """
    if attacker.room != target.room:
        return False
    if attacker.curr_row != target.curr_row:
        return False
    dist = target.curr_col - attacker.curr_col
    if abs(dist) != 1:
        return False
    # El attacker debe mirar hacia el target
    if dist > 0 and attacker.direction != 0:
        # direction 0 (RIGHT) y target a la derecha
        return False
    if dist < 0 and attacker.direction != -1:
        return False
    # Las condiciones canon son simétricas — facing correcto
    return (dist > 0 and attacker.direction == 0) or (dist < 0 and attacker.direction == -1)


# ---------------------------------------------------------------------------
# Resolución de combate
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CombatResolution:
    """Resultado de aplicar un tick de combate entre kid y guard."""

    kid: Char
    guard: Char
    kid_hit: bool = False
    """``True`` si el kid recibió un golpe."""
    guard_hit: bool = False
    """``True`` si el guard recibió un golpe."""


def resolve_combat(kid: Char, guard: Char) -> CombatResolution:
    """Resuelve un tick de intercambio de espadas.

    Regla canónica:
    1. Si ``kid`` está en STRIKE_WINDOW y `can_strike(kid, guard)`:
       - Si guard NO está en BLOCK_WINDOW → guard sufre `take_hp(1)`.
    2. Si ``guard`` está en STRIKE_WINDOW y `can_strike(guard, kid)`:
       - Si kid NO está en BLOCK_WINDOW → kid sufre `take_hp(1)`.
    """
    new_kid = kid
    new_guard = guard
    kid_hit = False
    guard_hit = False

    # Kid ataca
    if (
        is_in_strike_window(new_kid)
        and can_strike(new_kid, new_guard)
        and not is_in_block_window(new_guard)
    ):
        result = take_hp(new_guard, 1)
        new_guard = result.char
        guard_hit = True

    # Guard ataca
    if (
        is_in_strike_window(new_guard)
        and can_strike(new_guard, new_kid)
        and not is_in_block_window(new_kid)
    ):
        result = take_hp(new_kid, 1)
        new_kid = result.char
        kid_hit = True

    return CombatResolution(
        kid=new_kid,
        guard=new_guard,
        kid_hit=kid_hit,
        guard_hit=guard_hit,
    )
