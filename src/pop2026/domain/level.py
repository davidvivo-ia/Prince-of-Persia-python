"""Nivel: grid de tiles + estado dinámico (gates, suelos rotos…).

``Level`` es la **estructura inmutable** (lo que se carga desde el
fichero). ``LevelState`` es el **estado dinámico** del nivel durante una
partida: qué gates están abiertas, qué suelos sueltos ya cayeron, qué
pociones se bebieron. Ambos son frozen dataclasses; cada paso del juego
produce un ``LevelState`` nuevo.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Self

from pop2026.domain.errors import LevelLoadError
from pop2026.domain.geometry import Position
from pop2026.domain.tiles import CHAR_TO_TILE, Tile


@dataclass(frozen=True, slots=True)
class Level:
    """Estructura inmutable del nivel."""

    name: str
    grid: tuple[tuple[Tile, ...], ...]
    """Filas por columnas de tiles."""

    prince_spawn: Position
    guard_spawns: tuple[tuple[Position, int], ...]
    """Lista de (posición, skill 1..2) para los guardias."""

    @property
    def rows(self) -> int:
        """Filas del nivel."""
        return len(self.grid)

    @property
    def cols(self) -> int:
        """Columnas del nivel."""
        return len(self.grid[0]) if self.grid else 0

    def tile_at(self, pos: Position) -> Tile:
        """Tile estático en ``pos``. Fuera de mapa devuelve ``FLOOR``."""
        if pos.row < 0 or pos.row >= self.rows:
            return Tile.FLOOR
        if pos.col < 0 or pos.col >= self.cols:
            return Tile.FLOOR
        return self.grid[pos.row][pos.col]

    @classmethod
    def parse(cls, source: str, *, name: str = "level") -> Self:
        """Parsea un texto ``.poplv`` a ``Level``.

        Líneas en blanco al inicio/fin se ignoran. La primera línea no
        vacía determina la anchura: el resto debe coincidir.
        """
        lines = [ln.rstrip() for ln in source.splitlines() if ln.strip()]
        if not lines:
            raise LevelLoadError("Nivel vacío.")
        width = max(len(ln) for ln in lines)
        # pad líneas con '.' (empty) para uniformar
        padded = [ln.ljust(width, ".") for ln in lines]
        rows: list[tuple[Tile, ...]] = []
        prince_spawn: Position | None = None
        guards: list[tuple[Position, int]] = []
        for r, line in enumerate(padded):
            row_tiles: list[Tile] = []
            for c, ch in enumerate(line):
                tile = CHAR_TO_TILE.get(ch)
                if tile is None:
                    raise LevelLoadError(f"Carácter desconocido {ch!r} en {r},{c}")
                if tile is Tile.SPAWN_PRINCE:
                    prince_spawn = Position(r, c)
                    row_tiles.append(Tile.EMPTY)
                elif tile is Tile.SPAWN_GUARD:
                    guards.append((Position(r, c), 1))
                    row_tiles.append(Tile.EMPTY)
                elif tile is Tile.SPAWN_BOSS:
                    guards.append((Position(r, c), 2))
                    row_tiles.append(Tile.EMPTY)
                else:
                    row_tiles.append(tile)
            rows.append(tuple(row_tiles))
        if prince_spawn is None:
            raise LevelLoadError("Falta spawn de príncipe ('@').")
        return cls(
            name=name,
            grid=tuple(rows),
            prince_spawn=prince_spawn,
            guard_spawns=tuple(guards),
        )


@dataclass(frozen=True, slots=True)
class LevelState:
    """Estado dinámico del nivel durante la partida."""

    open_gates: frozenset[Position] = field(default_factory=frozenset)
    """Posiciones de gates abiertas en este momento."""

    fallen_floors: frozenset[Position] = field(default_factory=frozenset)
    """Loose-floors que ya cayeron (ahora se comportan como EMPTY)."""

    consumed_potions: frozenset[Position] = field(default_factory=frozenset)
    """Pociones bebidas, ya no son visibles ni reactivas."""

    pressed_plates: frozenset[Position] = field(default_factory=frozenset)
    """Placas pisadas en el tick anterior."""

    def with_open(self, pos: Position) -> LevelState:
        """Devuelve un nuevo estado con ``pos`` añadida a gates abiertas."""
        return replace(self, open_gates=self.open_gates | {pos})

    def with_floor_fallen(self, pos: Position) -> LevelState:
        """Marca un loose-floor como caído."""
        return replace(self, fallen_floors=self.fallen_floors | {pos})

    def with_potion_consumed(self, pos: Position) -> LevelState:
        """Marca una poción como consumida."""
        return replace(self, consumed_potions=self.consumed_potions | {pos})

    def with_pressed(self, plates: frozenset[Position]) -> LevelState:
        """Recalcula el set de placas pisadas en este tick."""
        return replace(self, pressed_plates=plates)


def effective_tile(level: Level, state: LevelState, pos: Position) -> Tile:
    """Devuelve el tile efectivo (considerando el estado dinámico)."""
    raw = level.tile_at(pos)
    if raw is Tile.GATE and pos in state.open_gates:
        return Tile.EMPTY
    if raw is Tile.LOOSE_FLOOR and pos in state.fallen_floors:
        return Tile.EMPTY
    if raw in (Tile.POTION_HEAL, Tile.POTION_POISON) and pos in state.consumed_potions:
        return Tile.EMPTY
    return raw
