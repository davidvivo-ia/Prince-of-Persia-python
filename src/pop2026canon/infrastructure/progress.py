"""Progreso del jugador: niveles desbloqueados, mejores tiempos y
medallas por nivel, persistidos en JSON junto a los ajustes.

Puro salvo ``load``/``save``. Un fichero corrupto o de otra versión no
rompe nada: se ignora lo que no se entiende.

Medallas por nivel (se conservan las conseguidas en cualquier intento):

- ``completed`` — cruzar la puerta de salida.
- ``flawless`` — sin morir ni rebobinar.
- ``swift`` — por debajo del tiempo de referencia del nivel.
- ``explorer`` — visitar todas las salas.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from pathlib import Path

from pop2026canon.application.stats import LevelStats

MEDALS: tuple[str, ...] = ("completed", "flawless", "swift", "explorer")

PAR_SECONDS: dict[int, int] = {
    1: 210,
    2: 220,
    3: 210,
    4: 220,
    5: 320,
    6: 300,
    7: 260,
    8: 160,
    9: 170,
    10: 180,
    11: 290,
    12: 380,
    13: 190,
    14: 60,
}
"""Tiempo de referencia (s) para la medalla ``swift``: unas 2,5 veces la
ruta óptima del bot."""

FINAL_LEVEL = 14


@dataclass(frozen=True, slots=True)
class LevelRecord:
    completed: bool = False
    best_ticks: int | None = None
    best_deaths: int | None = None
    medals: tuple[str, ...] = ()

    @property
    def best_clock(self) -> str:
        if self.best_ticks is None:
            return "--:--"
        s = self.best_ticks // 12
        return f"{s // 60:d}:{s % 60:02d}"


@dataclass(frozen=True, slots=True)
class Progress:
    unlocked: int = 1
    """Nivel más alto al que se puede saltar desde el menú."""
    levels: dict[int, LevelRecord] = field(default_factory=dict)
    campaigns_won: int = 0

    def record(self, level_number: int) -> LevelRecord:
        return self.levels.get(level_number, LevelRecord())

    @property
    def any_completed(self) -> bool:
        return any(r.completed for r in self.levels.values())

    @property
    def medal_count(self) -> int:
        return sum(len(r.medals) for r in self.levels.values())


def medals_for(stats: LevelStats, rooms_total: int) -> tuple[str, ...]:
    """Medallas que merece una partida del nivel recién terminado."""
    out = ["completed"]
    if stats.deaths == 0 and stats.rewound_ticks == 0:
        out.append("flawless")
    if stats.seconds <= PAR_SECONDS.get(stats.level, 300):
        out.append("swift")
    if rooms_total and len(stats.visited) >= rooms_total:
        out.append("explorer")
    return tuple(out)


def record_level(
    progress: Progress, stats: LevelStats, rooms_total: int
) -> tuple[Progress, tuple[str, ...], tuple[str, ...]]:
    """Registra un nivel completado. Devuelve ``(progreso, medallas de
    esta partida, medallas NUEVAS respecto a lo que ya tenía)``."""
    earned = medals_for(stats, rooms_total)
    old = progress.record(stats.level)
    new_medals = tuple(m for m in earned if m not in old.medals)
    best_ticks = stats.ticks if old.best_ticks is None else min(old.best_ticks, stats.ticks)
    best_deaths = stats.deaths if old.best_deaths is None else min(old.best_deaths, stats.deaths)
    rec = LevelRecord(
        completed=True,
        best_ticks=best_ticks,
        best_deaths=best_deaths,
        medals=tuple(m for m in MEDALS if m in old.medals or m in earned),
    )
    levels = dict(progress.levels)
    levels[stats.level] = rec
    unlocked = max(progress.unlocked, min(FINAL_LEVEL, stats.level + 1))
    return replace(progress, levels=levels, unlocked=unlocked), earned, new_medals


def record_campaign_won(progress: Progress) -> Progress:
    return replace(progress, campaigns_won=progress.campaigns_won + 1, unlocked=FINAL_LEVEL)


# ---------------------------------------------------------------------------
# Persistencia
# ---------------------------------------------------------------------------


def default_progress_path() -> Path:
    return Path.home() / ".local" / "share" / "pop2026canon" / "progress.json"


def to_json(progress: Progress) -> str:
    data = {
        "version": 1,
        "unlocked": progress.unlocked,
        "campaigns_won": progress.campaigns_won,
        "levels": {
            str(n): {
                "completed": r.completed,
                "best_ticks": r.best_ticks,
                "best_deaths": r.best_deaths,
                "medals": list(r.medals),
            }
            for n, r in sorted(progress.levels.items())
        },
    }
    return json.dumps(data, indent=2)


def from_json(text: str) -> Progress:
    try:
        raw = json.loads(text)
    except (ValueError, TypeError):
        return Progress()
    if not isinstance(raw, dict):
        return Progress()
    levels: dict[int, LevelRecord] = {}
    for key, val in (raw.get("levels") or {}).items():
        try:
            n = int(key)
        except (TypeError, ValueError):
            continue
        if not isinstance(val, dict) or not (1 <= n <= FINAL_LEVEL):
            continue
        ticks = val.get("best_ticks")
        deaths = val.get("best_deaths")
        medals = tuple(m for m in MEDALS if m in (val.get("medals") or ()))
        levels[n] = LevelRecord(
            completed=bool(val.get("completed", False)),
            best_ticks=int(ticks) if isinstance(ticks, int) else None,
            best_deaths=int(deaths) if isinstance(deaths, int) else None,
            medals=medals,
        )
    try:
        unlocked = int(raw.get("unlocked", 1))
    except (TypeError, ValueError):
        unlocked = 1
    unlocked = max(1, min(FINAL_LEVEL, unlocked))
    try:
        won = max(0, int(raw.get("campaigns_won", 0)))
    except (TypeError, ValueError):
        won = 0
    return Progress(unlocked=unlocked, levels=levels, campaigns_won=won)


def load(path: Path | None = None) -> Progress:
    p = path or default_progress_path()
    try:
        return from_json(p.read_text(encoding="utf-8"))
    except OSError:
        return Progress()


def save(progress: Progress, path: Path | None = None) -> None:
    p = path or default_progress_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(to_json(progress), encoding="utf-8")
