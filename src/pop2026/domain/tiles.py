"""Tipos de tile y helpers."""

from __future__ import annotations

from enum import IntEnum


class Tile(IntEnum):
    """Tile estático del nivel.

    ``EMPTY`` es aire (caes). ``FLOOR`` es suelo sólido (puedes pisar y
    caminar encima). ``LOOSE_FLOOR`` se rompe al pisarlo. ``SPIKES`` mata
    al caer encima. ``GATE`` bloquea paso a menos que esté abierta.
    ``PRESSURE`` es placa que abre la gate más próxima. ``POTION_HEAL``
    cura. ``POTION_POISON`` daña. ``EXIT`` completa el nivel.

    ``SPAWN_*`` son marcadores; al cargar el nivel se reemplazan por
    ``EMPTY`` y se registran como spawn-points.
    """

    EMPTY = 0
    FLOOR = 1
    LOOSE_FLOOR = 2
    SPIKES = 3
    GATE = 4
    PRESSURE = 5
    POTION_HEAL = 6
    POTION_POISON = 7
    EXIT = 8
    SPAWN_PRINCE = 9
    SPAWN_GUARD = 10
    SPAWN_BOSS = 11
    SWORD = 12


SOLID: frozenset[Tile] = frozenset({Tile.FLOOR, Tile.LOOSE_FLOOR, Tile.GATE})
"""Tiles sobre los que un actor puede pararse (de pie)."""

WALKABLE_OVER: frozenset[Tile] = frozenset(
    {
        Tile.EMPTY,
        Tile.PRESSURE,
        Tile.POTION_HEAL,
        Tile.POTION_POISON,
        Tile.EXIT,
        Tile.SWORD,
        Tile.SPIKES,  # se puede entrar; las spikes matan si pisas con caída
    }
)
"""Tiles que un actor puede ocupar (su torso)."""


CHAR_TO_TILE: dict[str, Tile] = {
    ".": Tile.EMPTY,
    "#": Tile.FLOOR,
    "=": Tile.LOOSE_FLOOR,
    "^": Tile.SPIKES,
    "|": Tile.GATE,
    "_": Tile.PRESSURE,
    "+": Tile.POTION_HEAL,
    "-": Tile.POTION_POISON,
    ">": Tile.EXIT,
    "S": Tile.SWORD,
    "@": Tile.SPAWN_PRINCE,
    "g": Tile.SPAWN_GUARD,
    "G": Tile.SPAWN_BOSS,
}
"""Mapeo carácter → Tile para el formato ``.poplv``."""


TILE_TO_CHAR: dict[Tile, str] = {v: k for k, v in CHAR_TO_TILE.items()}
