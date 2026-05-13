"""Definición de la campaña: 12 niveles con título narrativo.

Cada entrada es ``(slug, título mostrado)``. El ``slug`` se resuelve
contra :mod:`pop2026.infrastructure.builtin_levels` por
:func:`pop2026.infrastructure.levels.load_builtin`.

Los nombres y los layouts son **diseño propio** inspirado en el género
clásico de plataformas-mazmorra; no copian ningún nivel concreto del
original.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LevelInfo:
    """Metadatos para presentar un nivel."""

    slug: str
    title: str
    subtitle: str


CAMPAIGN: tuple[LevelInfo, ...] = (
    LevelInfo("01_cell", "La Celda", "Despierta. Camina hacia la luz."),
    LevelInfo("02_sword", "El Sable", "Una hoja olvidada en la piedra."),
    LevelInfo("03_guard", "El Guardia", "El primer hierro contra el tuyo."),
    LevelInfo("04_traps", "Pinchos y Poción", "El suelo te quiere y no te quiere."),
    LevelInfo("05_plate", "La Placa", "Pisa donde nadie pisa."),
    LevelInfo("06_loose", "Ladrillos Sueltos", "Lo que parece firme."),
    LevelInfo("07_duo", "Dos Hierros", "Una hoja a cada lado."),
    LevelInfo("08_climb", "La Cornisa", "Sube. La salida está arriba."),
    LevelInfo("09_maze", "Reja y Trampa", "Las puertas se eligen una sola vez."),
    LevelInfo("10_patrol", "La Patrulla", "Tres centinelas en un pasillo largo."),
    LevelInfo("11_spikes", "Camino de Pinchos", "Cada paso, una decisión."),
    LevelInfo("12_jaffar", "El Visir", "Una hora ha pasado. Termina."),
)
"""Doce niveles encadenados — la campaña completa de v1.0."""


def total_levels() -> int:
    """Número de niveles de la campaña."""
    return len(CAMPAIGN)


def get(index: int) -> LevelInfo:
    """Devuelve el ``LevelInfo`` del nivel 1-indexado.

    Args:
        index: 1..len(CAMPAIGN).
    """
    if index < 1 or index > len(CAMPAIGN):
        raise IndexError(f"Nivel {index} fuera de rango 1..{len(CAMPAIGN)}")
    return CAMPAIGN[index - 1]
