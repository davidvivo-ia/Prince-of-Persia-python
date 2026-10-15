"""Estadísticas de partida por nivel (pantalla de nivel completado,
mapa de salas exploradas)."""

from __future__ import annotations

from dataclasses import dataclass, field

from pop2026canon.domain.combat import is_hostile
from pop2026canon.domain.game import Game
from pop2026canon.domain.tiles import Tile


@dataclass
class LevelStats:
    level: int
    ticks: int = 0
    deaths: int = 0
    guards_defeated: int = 0
    potions: int = 0
    rewound_ticks: int = 0
    visited: set[int] = field(default_factory=set)

    def start(self, game: Game) -> None:
        self.visited.add(game.kid.room)

    def observe(self, prev: Game, now: Game) -> None:
        """Llamar tras cada tick normal (no durante el rebobinado)."""
        self.ticks += 1
        self.visited.add(now.kid.room)
        prev_alive = {i for i, c in enumerate(prev.others) if c.alive < 0}
        for i, c in enumerate(now.others):
            if i in prev_alive and c.alive >= 0 and is_hostile(c):
                self.guards_defeated += 1
        new_items = now.state.consumed_potions - prev.state.consumed_potions
        for rid, col, row in new_items:
            if (
                1 <= rid <= len(now.level.rooms)
                and now.level.room(rid).tile_at(col, row)[0] is Tile.POTION
            ):
                self.potions += 1

    @property
    def seconds(self) -> int:
        return self.ticks // 12

    @property
    def clock(self) -> str:
        return f"{self.seconds // 60:d}:{self.seconds % 60:02d}"
