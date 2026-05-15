"""Modelo de `Level` — 24 salas + eventos especiales + start position."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from pop2026canon.domain.actions import Direction
from pop2026canon.domain.constants import ROOMCOUNT
from pop2026canon.domain.room import Room


class EventKind(IntEnum):
    """Tipos de evento scripted dentro de un nivel."""

    SKELETON_WAKE = 0
    """Esqueleto se levanta cuando el kid pisa una celda trigger (L3)."""

    SHADOW_MIRROR = 1
    """Shadow nace al cruzar el espejo (L4)."""

    SHADOW_STEAL = 2
    """Shadow roba la poción de la sala (L5)."""

    SHADOW_STEP = 3
    """Shadow salta cuando el kid está en frame_43 (L6)."""

    SHADOW_FUSION = 4
    """Shadow imita al kid; al tocarse, +HP (L12)."""

    VIZIER_INIT = 5
    """Spawn de Jaffar al entrar en la sala (L12)."""

    PRINCESS_REUNION = 6
    """Cinemática princesa (L14 ending)."""

    MOUSE_APPEAR = 7
    """Ratón que abre la última gate (L8)."""


@dataclass(frozen=True, slots=True)
class Event:
    """Trigger scripted del nivel."""

    kind: EventKind
    room: int
    """Sala en la que se dispara."""

    col: int = 0
    row: int = 0
    extra: int = 0
    """Datos adicionales (frame trigger para SHADOW_STEP, etc.)."""


@dataclass(frozen=True, slots=True)
class Level:
    """Nivel completo: 24 salas + start + eventos."""

    number: int
    """1..14."""

    name: str
    """Nombre canónico ("The Dungeon", "The Guards", etc.)."""

    rooms: tuple[Room, ...]
    """Hasta `ROOMCOUNT = 24` salas. rooms[0] es la sala 1."""

    start_room: int
    """Sala donde spawnea el kid (1..24)."""

    start_col: int
    start_row: int
    start_direction: int = int(Direction.RIGHT)

    events: tuple[Event, ...] = ()
    """Triggers scripted específicos del nivel."""

    def __post_init__(self) -> None:
        if not (1 <= self.number <= 14):
            raise ValueError(f"level number {self.number} fuera de [1, 14]")
        if len(self.rooms) > ROOMCOUNT:
            raise ValueError(f"level tiene {len(self.rooms)} salas, máx {ROOMCOUNT}")
        if not (1 <= self.start_room <= len(self.rooms)):
            raise ValueError(f"start_room {self.start_room} fuera de rango")

    def room(self, room_id: int) -> Room:
        """Devuelve la sala con id 1..N."""
        if not (1 <= room_id <= len(self.rooms)):
            raise IndexError(f"room {room_id} fuera de rango 1..{len(self.rooms)}")
        return self.rooms[room_id - 1]
