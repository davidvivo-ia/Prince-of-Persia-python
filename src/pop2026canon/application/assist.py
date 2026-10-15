"""Ayudas del *modo moderno* — opcionales, encima de las reglas canon.

- **Arenas del Tiempo** (homenaje a *The Sands of Time*, 2003): el
  dominio es inmutable, así que cada tick es una foto completa del
  juego. Se guardan los últimos segundos y, manteniendo el botón de
  rebobinar, se recorren hacia atrás. Rebobinar gasta arena; jugar la
  recarga despacio. Funciona también durante la animación de muerte:
  puedes deshacer el salto que te mató.
- **Punto de control por sala**: al entrar en una sala con los pies en
  el suelo se guarda una foto; morir te devuelve ahí con la vida llena
  y el reloj donde estaba (canon: el tiempo nunca se devuelve al morir).

En *modo clásico* nada de esto se usa: morir reinicia el nivel, como
en 1989.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace

from pop2026canon.domain.actions import Action
from pop2026canon.domain.game import Game, GameStatus

LOGIC_FPS = 12

HISTORY_SECONDS = 8
"""Cuánto pasado se recuerda."""

SAND_MAX = LOGIC_FPS * 6
"""Arena llena = 6 segundos de rebobinado."""

SAND_REFILL_EVERY = 4
"""Ticks de juego normal por cada tick de arena recuperado (la arena
vacía se llena en ~24 s)."""


class TimeRewind:
    """Historial de ``Game`` + medidor de arena."""

    def __init__(self, *, sand: int = SAND_MAX) -> None:
        self._history: deque[Game] = deque(maxlen=HISTORY_SECONDS * LOGIC_FPS)
        self.sand = sand
        self._refill_counter = 0

    def reset(self) -> None:
        """Nivel nuevo: el pasado anterior ya no existe (la arena se queda)."""
        self._history.clear()

    def record(self, game: Game) -> None:
        """Guarda el estado ANTERIOR a un tick normal y recarga arena."""
        self._history.append(game)
        self._refill_counter += 1
        if self._refill_counter >= SAND_REFILL_EVERY:
            self._refill_counter = 0
            self.sand = min(SAND_MAX, self.sand + 1)

    @property
    def can_rewind(self) -> bool:
        return self.sand > 0 and bool(self._history)

    @property
    def history_len(self) -> int:
        return len(self._history)

    @property
    def sand_fraction(self) -> float:
        return self.sand / SAND_MAX

    def step_back(self) -> Game | None:
        """Un tick hacia atrás (gasta un grano). ``None`` si no se puede."""
        if not self.can_rewind:
            return None
        self.sand -= 1
        return self._history.pop()


def is_safe_checkpoint(game: Game) -> bool:
    """¿Es buen sitio para reaparecer? Vivo, de pie y jugando."""
    kid = game.kid
    return (
        game.status is GameStatus.PLAYING
        and kid.alive < 0
        and kid.action is Action.STAND
        and kid.hp_curr > 0
    )


@dataclass
class RoomCheckpoint:
    """Foto del juego al entrar (de pie) en la sala actual."""

    snapshot: Game | None = None
    room: int = 0

    def observe(self, game: Game) -> None:
        """Llamar tras cada tick: fija el checkpoint al pisar sala nueva."""
        if game.kid.room != self.room and is_safe_checkpoint(game):
            self.snapshot = game
            self.room = game.kid.room

    def reset(self, game: Game) -> None:
        """Inicio de nivel: el checkpoint es el spawn."""
        self.snapshot = game
        self.room = game.kid.room

    def respawn(self, dead: Game) -> Game | None:
        """Juego tras morir: la foto de la sala, con vida llena y el reloj
        del momento de la muerte. ``None`` si no hay foto."""
        if self.snapshot is None:
            return None
        snap = self.snapshot
        hp_max = max(snap.kid.hp_max, dead.kid.hp_max)
        kid = replace(snap.kid, hp_curr=hp_max, hp_max=hp_max)
        return replace(snap, kid=kid, time=dead.time, status=GameStatus.PLAYING)
