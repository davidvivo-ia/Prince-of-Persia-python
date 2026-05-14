"""Definición de la campaña: 100 niveles en 4 actos.

Niveles 1-12: hand-crafted (slugs `.poplv` en
:mod:`pop2026.infrastructure.builtin_levels`).

Niveles 13-100: títulos derivados deterministamente del acto y del
índice. El layout se genera procedurálmente en
:mod:`pop2026.application.level_generator` y se carga via
:mod:`pop2026.application.level_source`.

Los nombres y los layouts hand-crafted son **diseño propio** inspirado
en el género clásico de plataformas-mazmorra; no copian ningún nivel
concreto del original.
"""

from __future__ import annotations

from dataclasses import dataclass

from pop2026.application.difficulty import ACT_THEMES, act_for_level

TOTAL_LEVELS: int = 100
"""Niveles totales de la campaña."""


@dataclass(frozen=True, slots=True)
class LevelInfo:
    """Metadatos para presentar un nivel."""

    slug: str
    title: str
    subtitle: str


# ---------------------------------------------------------------------------
# Niveles hand-crafted (1..12). Coinciden con `.poplv` empaquetados.
# ---------------------------------------------------------------------------

_HAND_CRAFTED: tuple[LevelInfo, ...] = (
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
    LevelInfo("13_shadow", "La Sombra", "Tu reflejo también empuña un sable."),
    LevelInfo("14_throne", "El Trono", "El visir te espera entre cortinas y placas."),
    LevelInfo("15_escape", "La Huida", "Última carrera. No mires atrás."),
)
"""Quince niveles narrativos hand-crafted. Acto I (parte 1) + cierre."""


# Subtítulos procedurales por acto. Frase corta y atmosférica.
_PROCEDURAL_SUBTITLES: dict[int, tuple[str, ...]] = {
    0: (
        "Otra galería sin nombre.",
        "Las antorchas ya no calientan.",
        "Una mano arrastró este moho.",
        "Hace siglos hubo aquí un grito.",
        "La piedra recuerda más que tú.",
    ),
    1: (
        "Donde duermen los olvidados.",
        "Las cadenas no se oxidan solas.",
        "Un guardia que no pestañea.",
        "Hay una llave en alguna parte.",
        "La sed es peor que la espada.",
    ),
    2: (
        "El mosaico aún brilla en algunos cuadros.",
        "Una corte invisible sigue mirándote.",
        "El visir tiene ojos en cada arco.",
        "Las cortinas se han movido solas.",
        "Aquí también se aprende a esperar.",
    ),
    3: (
        "La torre se inclina si la miras.",
        "Cada peldaño es una decisión.",
        "Hueles el final desde aquí.",
        "Alguien quema incienso en lo alto.",
        "El reloj de arena no se ha vuelto a girar.",
    ),
}


def _procedural_title(level_index: int) -> str:
    """Genera un título consistente para un nivel procedural."""
    act = act_for_level(level_index)
    theme = ACT_THEMES[act]
    return f"{theme} {level_index:02d}"


def _procedural_subtitle(level_index: int) -> str:
    """Subtítulo determinista a partir del índice."""
    act = act_for_level(level_index)
    pool = _PROCEDURAL_SUBTITLES[act]
    return pool[level_index % len(pool)]


def _build_campaign() -> tuple[LevelInfo, ...]:
    """Construye la tupla completa de 100 entradas."""
    entries: list[LevelInfo] = list(_HAND_CRAFTED)
    for idx in range(len(_HAND_CRAFTED) + 1, TOTAL_LEVELS + 1):
        entries.append(
            LevelInfo(
                slug=f"L{idx:03d}",
                title=_procedural_title(idx),
                subtitle=_procedural_subtitle(idx),
            )
        )
    return tuple(entries)


CAMPAIGN: tuple[LevelInfo, ...] = _build_campaign()
"""Cien niveles encadenados — la campaña completa de v3.0."""


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
