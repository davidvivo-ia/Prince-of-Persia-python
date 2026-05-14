"""Curva de dificultad para los 100 niveles.

Diseño:

- 4 actos de 25 niveles. ``act ∈ [0, 3]``.
- Dentro de cada acto la dificultad sube de forma monótona suave.
- Al cambiar de acto hay un escalón hacia arriba.
- El nivel ``local_index == 24`` (último de cada acto) es boss.
- El acto 4 es el más punitivo en todas las métricas.

Las métricas son **objetivos** del generador, no garantías estrictas:
si el generador no encuentra layout válido, puede relajar alguna.
"""

from __future__ import annotations

from dataclasses import dataclass

ACT_THEMES: tuple[str, ...] = ("Mazmorra", "Prisión", "Palacio", "Torre")
"""Nombre temático por acto, en español."""


def act_for_level(level_index: int) -> int:
    """Devuelve el índice de acto (0..3) para un nivel 1..100."""
    if level_index < 1 or level_index > 100:
        raise ValueError(f"level_index fuera de rango 1..100: {level_index}")
    return (level_index - 1) // 25


def local_index_for_level(level_index: int) -> int:
    """Posición del nivel dentro de su acto (0..24)."""
    if level_index < 1 or level_index > 100:
        raise ValueError(f"level_index fuera de rango 1..100: {level_index}")
    return (level_index - 1) % 25


@dataclass(frozen=True, slots=True)
class DifficultyParams:
    """Parámetros que el generador procedural usa para componer un nivel."""

    act: int
    local_index: int
    gap_prob: float
    """Probabilidad por celda de suelo de tener un hueco (0..1)."""

    spike_prob: float
    """Probabilidad por celda de aire de tener pinchos (0..1)."""

    loose_prob: float
    """Probabilidad por celda de suelo de ser ``LOOSE_FLOOR``."""

    guard_count: int
    """Número de guardias normales a colocar."""

    skeleton_count: int
    """Número de esqueletos a colocar."""

    multi_room_prob: float
    """Probabilidad de generar el nivel a 40 celdas (dos salas)."""

    boss_flag: bool
    """``True`` si el nivel debe contener un guardia jefe."""

    time_limit_seconds: int
    """Tiempo del nivel en segundos."""

    @property
    def time_limit_ticks(self) -> int:
        """Tiempo en ticks (60/s)."""
        return self.time_limit_seconds * 60


def params_for(level_index: int) -> DifficultyParams:
    """Calcula los parámetros para el nivel ``level_index`` (1..100)."""
    act = act_for_level(level_index)
    local = local_index_for_level(level_index)

    # Progresión local dentro del acto: 0..1
    local_t = local / 24.0

    # Bases por acto (escalón al cambiar de acto).
    base_gap = (0.04, 0.08, 0.12, 0.16)[act]
    base_spike = (0.03, 0.05, 0.07, 0.10)[act]
    base_loose = (0.02, 0.04, 0.06, 0.08)[act]
    base_guards = (0, 1, 1, 2)[act]
    multi_room_chance = (0.0, 0.10, 0.40, 0.65)[act]
    base_time = (90, 75, 60, 50)[act]

    # Modulación local: la última mitad del acto añade un poco de cada cosa.
    gap_prob = min(0.40, base_gap + 0.03 * local_t)
    spike_prob = min(0.30, base_spike + 0.04 * local_t)
    loose_prob = min(0.30, base_loose + 0.04 * local_t)

    # Guardias adicionales hacia el final del acto.
    extra_guard = local // 8  # 0,1,2,3 según local 0..24
    guard_count = base_guards + extra_guard

    # Esqueleto solo aparece en el acto 4 (act == 3) a partir del local 12.
    skeleton_count = 1 if act == 3 and local >= 12 else 0

    # Multi-room: rampa lineal local sobre la base del acto.
    multi_room_prob = min(0.95, multi_room_chance + 0.30 * local_t)

    boss_flag = local == 24

    # Boss roba algo de tiempo y suma un guardia.
    if boss_flag:
        guard_count += 1
        time_limit = max(35, base_time - 10)
    else:
        time_limit = base_time

    return DifficultyParams(
        act=act,
        local_index=local,
        gap_prob=gap_prob,
        spike_prob=spike_prob,
        loose_prob=loose_prob,
        guard_count=guard_count,
        skeleton_count=skeleton_count,
        multi_room_prob=multi_room_prob,
        boss_flag=boss_flag,
        time_limit_seconds=time_limit,
    )
