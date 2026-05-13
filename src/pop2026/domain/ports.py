"""Puertos (Protocols) que la infraestructura implementa.

Definidos aquí para que el dominio sea independiente. La inyección la
hace la *composition root* en :mod:`pop2026.presentation.app`.
"""

from __future__ import annotations

from typing import Protocol


class Rng(Protocol):
    """RNG determinista inyectable. Ver ADR 0003 para implementación."""

    def next_byte(self) -> int:
        """Devuelve un byte 0..255."""
        ...  # pragma: no cover

    def coin(self, prob: float) -> bool:
        """Sale ``True`` con probabilidad ``prob`` (en [0, 1])."""
        ...  # pragma: no cover

    def randrange(self, n: int) -> int:
        """Entero uniforme en ``[0, n)``."""
        ...  # pragma: no cover
