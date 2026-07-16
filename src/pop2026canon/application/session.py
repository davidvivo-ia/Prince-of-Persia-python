"""Sesión de campaña — los 14 niveles como una partida continua.

Replica la estructura del juego original:

- El **reloj de 60 minutos** es global: sigue corriendo al pasar de
  nivel y NO se reinicia al morir. Morir cuesta tiempo, no "vidas".
- El **hp_max** conseguido con pociones grandes persiste entre niveles
  (y entre muertes: reapareces con la vida llena, pero conservas el
  máximo ganado).
- Morir reinicia el nivel actual desde su spawn (trampas y gates
  incluidas).
- Completar el nivel 13 lleva al 14 (la cámara de la princesa);
  alcanzarla gana el juego.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from pop2026canon.domain.game import Game, GameStatus, TimeRemaining, new_game
from pop2026canon.domain.levels_canon import CANON_LEVELS

FINAL_LEVEL = 14


@dataclass(frozen=True, slots=True)
class Session:
    """Estado de la campaña por encima del ``Game`` del nivel actual.

    ``levels`` permite jugar con otro set de 14 niveles — p.ej. los
    originales cargados de un LEVELS.DAT propio (ver
    :mod:`pop2026canon.infrastructure.levels_dat`).
    """

    level_number: int = 1
    hp_max: int = 3
    time: TimeRemaining = TimeRemaining()  # noqa: RUF009 — inmutable
    deaths: int = 0
    levels: tuple = CANON_LEVELS  # type: ignore[type-arg]

    def start_game(self) -> Game:
        """Construye el ``Game`` del nivel actual con el estado heredado."""
        level = self.levels[self.level_number - 1]
        game = new_game(level, starting_hp=self.hp_max)
        return replace(game, time=self.time)

    def after_tick(self, game: Game) -> Session:
        """Sincroniza el estado persistente tras cada tick (reloj, hp_max)."""
        return replace(self, time=game.time, hp_max=max(self.hp_max, game.kid.hp_max))

    def on_level_won(self, game: Game) -> Session:
        """El kid cruzó la exit door: avanza al siguiente nivel."""
        return replace(
            self,
            level_number=min(FINAL_LEVEL, self.level_number + 1),
            hp_max=max(self.hp_max, game.kid.hp_max),
            time=game.time,
        )

    def on_death(self, game: Game) -> Session:
        """El kid murió: mismo nivel, reloj donde estaba (canon)."""
        return replace(
            self,
            hp_max=max(self.hp_max, game.kid.hp_max),
            time=game.time,
            deaths=self.deaths + 1,
        )

    @property
    def campaign_complete(self) -> bool:
        return self.level_number > FINAL_LEVEL

    @property
    def out_of_time(self) -> bool:
        return self.time.is_zero()


def resolve_transition(session: Session, game: Game) -> tuple[Session, Game | None, str]:
    """Decide qué pasa cuando el ``Game`` del nivel deja de correr.

    Devuelve ``(nueva_session, nuevo_game | None, fase)``:

    - ``("card", game)`` — pasó de nivel: mostrar card y jugar el nuevo.
    - ``("respawn", game)`` — murió: reintentar el nivel.
    - ``("victory", None)`` — alcanzó a la princesa: fin del juego.
    - ``("timeout", None)`` — reloj a cero: derrota definitiva.
    """
    if game.status is GameStatus.WON_GAME:
        return session, None, "victory"
    if game.status is GameStatus.WON_LEVEL:
        new_session = session.on_level_won(game)
        return new_session, new_session.start_game(), "card"
    if game.status is GameStatus.LOST_TIMEOUT:
        return session, None, "timeout"
    if game.status is GameStatus.LOST_DIED:
        if game.time.is_zero():
            return session, None, "timeout"
        new_session = session.on_death(game)
        return new_session, new_session.start_game(), "respawn"
    return session, None, "victory"
