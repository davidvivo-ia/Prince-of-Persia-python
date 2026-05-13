"""Jerarquía de excepciones del dominio."""

from __future__ import annotations


class PopError(Exception):
    """Raíz de toda excepción del juego."""


class InvalidActionTransitionError(PopError):
    """Se intentó transicionar a una acción incompatible con el estado actual."""


class LevelLoadError(PopError):
    """El nivel no puede ser parseado o es inconsistente."""


class SaveCorruptedError(PopError):
    """El fichero de guardado existe pero no se puede leer."""
