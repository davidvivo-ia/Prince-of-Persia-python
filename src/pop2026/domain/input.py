"""Comandos del jugador. Independientes del dispositivo de entrada."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class PlayerCommand(IntEnum):
    """Acciones que el jugador puede pedir en un tick.

    ``NONE`` es ausencia de comando (mantenerse). El sistema de input de
    la capa de presentación traduce teclas a este enum.
    """

    NONE = 0
    LEFT = 1
    RIGHT = 2
    UP = 3
    DOWN = 4
    JUMP = 5
    STRIKE = 6
    PARRY = 7
    LUNGE = 8


@dataclass(frozen=True, slots=True)
class InputFrame:
    """Frame de entrada decodificado de la presentación al dominio."""

    command: PlayerCommand = PlayerCommand.NONE
    walk_modifier: bool = False
    """Si ``True``, ``LEFT``/``RIGHT`` resulta en paso de andar (preciso)."""

    jump_held: bool = False
    """Si ``True``, la tecla de salto sigue pulsada (para *variable jump*)."""

    jump_pressed: bool = False
    """``True`` si JUMP se pulsó este tick — canal independiente de ``command``.

    Permite combinar dirección y salto en el mismo tick (running jump),
    sin sacrificar el momento horizontal a un ``cmd=JUMP``.
    """
