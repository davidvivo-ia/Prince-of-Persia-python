"""Implementación de :class:`pop2026.domain.ports.Rng` con LFSR-8.

LFSR de 8 bits con polinomio ``0xB8`` (taps 8, 6, 5, 4). Período 255.
Suficiente para nuestro uso (≪1000 llamadas por partida) y portátil
entre versiones de Python.
"""

from __future__ import annotations


class LfsrRng:
    """RNG determinista LFSR-8.

    Seeds 1..255 producen ciclos distintos. Seed 0 se sanea a 1 (estado
    ``0`` quedaría atrapado en sí mismo).
    """

    __slots__ = ("_state",)

    def __init__(self, seed: int = 42) -> None:
        s = seed & 0xFF
        self._state = s if s != 0 else 1

    def next_byte(self) -> int:
        """Devuelve el siguiente byte 0..255."""
        s = self._state
        # taps en bits 0, 2, 3, 4 → equivalente a polinomio 0xB8
        bit = ((s >> 0) ^ (s >> 2) ^ (s >> 3) ^ (s >> 4)) & 1
        s = ((s >> 1) | (bit << 7)) & 0xFF
        if s == 0:
            s = 1
        self._state = s
        return s

    def coin(self, prob: float) -> bool:
        """``True`` con probabilidad ``prob`` (en [0, 1])."""
        return self.next_byte() < int(prob * 256)

    def randrange(self, n: int) -> int:
        """Entero uniforme en ``[0, n)``."""
        return self.next_byte() % max(1, n)
