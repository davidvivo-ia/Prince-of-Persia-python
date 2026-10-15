"""Modelo de `Room` — sala de 10x3 tiles con links N/S/E/W."""

from __future__ import annotations

from dataclasses import dataclass

from pop2026canon.domain.chars import GuardSpawn
from pop2026canon.domain.constants import ROOM_TILES, SCREEN_TILECOUNT_X, SCREEN_TILECOUNT_Y
from pop2026canon.domain.tiles import Tile, decode_tile


@dataclass(frozen=True, slots=True)
class Room:
    """Sala individual de un nivel.

    Coincide 1-a-1 con la fila del array `fg[720]`/`bg[720]` y los
    `roomlinks[24]` de SDLPoP.
    """

    id: int
    """1..24. 0 reservado para "no room" (links a un 0 = pared cerrada)."""

    fg: tuple[int, ...]
    """30 bytes — `tile + modifier`. Usar :func:`decode_tile` para abrir."""

    bg: tuple[int, ...]
    """30 bytes — overlays / modifiers extra."""

    link_n: int = 0
    """Sala al norte. 0 = no salida."""

    link_s: int = 0
    """Sala al sur. 0 = caída a la muerte si action freefall."""

    link_e: int = 0
    """Sala al este."""

    link_w: int = 0
    """Sala al oeste."""

    guards: tuple[GuardSpawn, ...] = ()
    """Guards que spawnean en esta sala."""

    def __post_init__(self) -> None:
        if len(self.fg) != ROOM_TILES:
            raise ValueError(f"fg debe tener {ROOM_TILES} bytes (10x3), no {len(self.fg)}")
        if len(self.bg) != ROOM_TILES:
            raise ValueError(f"bg debe tener {ROOM_TILES} bytes (10x3), no {len(self.bg)}")

    def tile_at(self, col: int, row: int) -> tuple[Tile, int]:
        """Devuelve ``(tile, modifier)`` en la celda."""
        if not (0 <= col < SCREEN_TILECOUNT_X and 0 <= row < SCREEN_TILECOUNT_Y):
            raise IndexError(f"({row}, {col}) fuera de sala 10x3")
        byte = self.fg[row * SCREEN_TILECOUNT_X + col]
        return decode_tile(byte)


def empty_room(room_id: int) -> Room:
    """Sala vacía (todo EMPTY)."""
    zero = (0,) * ROOM_TILES
    return Room(id=room_id, fg=zero, bg=zero)


def floor_room(room_id: int, *, ceiling: bool = True) -> Room:
    """Sala con suelo en la fila 2 (la inferior).

    Útil como base para construir salas-corredor.
    """
    fg = [int(Tile.EMPTY)] * ROOM_TILES
    # Fila 2 = suelo
    for c in range(SCREEN_TILECOUNT_X):
        fg[2 * SCREEN_TILECOUNT_X + c] = int(Tile.FLOOR)
    if ceiling:
        # Fila 0 = techo decorativo (FLOOR como pared superior)
        for c in range(SCREEN_TILECOUNT_X):
            fg[c] = int(Tile.FLOOR)
    return Room(id=room_id, fg=tuple(fg), bg=(0,) * ROOM_TILES)
