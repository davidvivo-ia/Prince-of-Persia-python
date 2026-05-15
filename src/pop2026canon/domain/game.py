"""Game aggregate — estado completo del juego en un tick.

Composición de kid + level + chars secundarios + level_state +
time. Inmutable como todo el dominio.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import IntEnum

from pop2026canon.domain.chars import Char, CharId
from pop2026canon.domain.constants import START_HITP, START_MINUTES_LEFT, START_TICKS_LEFT
from pop2026canon.domain.level import Level
from pop2026canon.domain.traps import LevelState


class GameStatus(IntEnum):
    """Estado global del juego."""

    PLAYING = 0
    WON_LEVEL = 1  # pasó el nivel, espera transición
    WON_GAME = 2  # completó los 14 niveles
    LOST_DIED = 3
    LOST_TIMEOUT = 4  # 60 min agotados → princesa muere


@dataclass(frozen=True, slots=True)
class TimeRemaining:
    """Tiempo restante in-game. Sólo se ve si el jugador pulsa la tecla
    de tiempo (canon TAB) o tras beber poción de tiempo.
    """

    minutes: int = START_MINUTES_LEFT
    ticks: int = START_TICKS_LEFT

    def is_zero(self) -> bool:
        return self.minutes == 0 and self.ticks == 0


@dataclass(frozen=True, slots=True)
class GameFlags:
    """Bits de estado global no específico de char/level."""

    sword_picked: bool = False
    """``True`` tras recoger la espada en L1."""

    shadow_initialized: bool = False
    """``True`` tras el primer encuentro con el shadow (L4 mirror)."""

    shadow_stole_potion: bool = False
    """``True`` tras el robo del shadow en L5."""

    shadow_fused: bool = False
    """``True`` tras la fusión en L12 — +HP máximo."""

    skeleton_woke: bool = False
    """``True`` tras despertar al esqueleto en L3."""

    mouse_appeared: bool = False
    """``True`` cuando el ratón ya cumplió su rol en L8."""


@dataclass(frozen=True, slots=True)
class Game:
    """Estado completo del juego en un tick.

    Aggregate root del dominio. Cada llamada a ``tick.advance(game,
    cmd)`` produce un nuevo ``Game`` inmutable.
    """

    level: Level
    """Nivel actual."""

    kid: Char
    """Personaje principal."""

    others: tuple[Char, ...] = ()
    """Otros chars activos (guards, shadow, princess, vizier, mouse)."""

    state: LevelState = LevelState()  # noqa: RUF009
    """Estado dinámico del nivel (trampas, gates, potions consumidas)."""

    time: TimeRemaining = TimeRemaining()
    """Tiempo restante in-game."""

    flags: GameFlags = GameFlags()
    """Bits de progreso global."""

    status: GameStatus = GameStatus.PLAYING

    tick_count: int = 0
    """Ticks lógicos transcurridos desde el inicio del nivel."""

    @property
    def running(self) -> bool:
        return self.status is GameStatus.PLAYING

    def replace_kid(self, kid: Char) -> Game:
        return replace(self, kid=kid)

    def replace_state(self, state: LevelState) -> Game:
        return replace(self, state=state)

    def find_char(self, charid: CharId) -> Char | None:
        """Busca un char secundario por ID. ``None`` si no existe."""
        for c in self.others:
            if c.charid is charid:
                return c
        return None


def new_game(level: Level, *, starting_hp: int = START_HITP) -> Game:
    """Construye un Game listo para jugar desde un Level."""
    from pop2026canon.domain.actions import Seq

    kid = Char(
        charid=CharId.KID,
        room=level.start_room,
        curr_col=level.start_col,
        curr_row=level.start_row,
        direction=level.start_direction,
        hp_curr=starting_hp,
        hp_max=starting_hp,
        curr_seq_id=int(Seq.STAND),
    )

    # Instanciar guards de cada room
    guard_list: list[Char] = []
    for room in level.rooms:
        for spawn in room.guards:
            from pop2026canon.domain.levels_canon import guard_hp_for_level

            hp = guard_hp_for_level(level.number)
            if hp == 0:
                continue
            from pop2026canon.domain.actions import SwordStatus

            guard_list.append(
                Char(
                    charid=CharId.GUARD,
                    room=room.id,
                    curr_col=spawn.col,
                    curr_row=spawn.row,
                    direction=spawn.direction,
                    hp_curr=hp,
                    hp_max=hp,
                    curr_seq_id=int(Seq.STAND),
                    sword=SwordStatus.DRAWN,
                    skill=spawn.skill,
                )
            )

    return Game(
        level=level,
        kid=kid,
        others=tuple(guard_list),
    )
