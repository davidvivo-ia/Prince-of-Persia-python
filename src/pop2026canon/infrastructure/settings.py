"""Ajustes del jugador, persistidos en JSON junto a la partida guardada.

Todo lo que un juego de 2026 deja configurar: volúmenes, pantalla,
filtros, accesibilidad y el *modo de juego*:

- ``modern`` (por defecto): reglas canon de 1989 más las ayudas de hoy
  — rebobinar con las Arenas del Tiempo y reaparecer en la entrada de
  la sala al morir.
- ``classic``: exactamente las reglas de 1989 (morir reinicia el nivel,
  sin rebobinado).

Un fichero corrupto o de una versión anterior no rompe el juego: los
campos desconocidos se ignoran y los que faltan toman su valor por
defecto.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields, replace
from pathlib import Path
from typing import Any

GAME_MODES: tuple[str, ...] = ("modern", "classic")
SCALE_MODES: tuple[str, ...] = ("pixel", "smooth")
DIFFICULTIES: tuple[str, ...] = ("normal", "hard")
LANGUAGES: tuple[str, ...] = ("es", "en")


@dataclass(frozen=True, slots=True)
class Settings:
    """Preferencias del jugador (inmutables; ``with_`` devuelve copias)."""

    master_volume: float = 0.8
    sfx_volume: float = 0.9
    music_volume: float = 0.55
    fullscreen: bool = False
    window_scale: int = 2
    """Ventana inicial: múltiplo de 640x426 (2 = el lienzo HD a 1:1)."""
    scale_mode: str = "smooth"
    """``smooth``: escala filtrada que llena la pantalla; ``pixel``: sólo
    factores enteros (nítido, con bandas)."""
    crt_filter: bool = False
    screen_shake: bool = True
    flashes: bool = True
    """Accesibilidad: destellos de pantalla al recibir daño."""
    lighting: bool = True
    particles: bool = True
    bloom: bool = True
    """Resplandor de llamas, pociones y chispas (post-proceso)."""
    game_mode: str = "modern"
    difficulty: str = "normal"
    """``hard``: guardias dos puntos más diestros y 45 minutos de reloj."""
    language: str = "es"
    hints: bool = True
    """Pistas contextuales para los verbos del original."""
    always_show_timer: bool = False
    seen_hints: tuple[str, ...] = ()
    """Pistas ya mostradas (cada una sale una sola vez)."""

    @property
    def modern(self) -> bool:
        return self.game_mode == "modern"

    @property
    def hard(self) -> bool:
        return self.difficulty == "hard"

    def with_(self, **changes: Any) -> Settings:
        return replace(self, **changes).validated()

    def validated(self) -> Settings:
        """Recorta cada campo a su rango válido."""

        def vol(v: float) -> float:
            return round(min(1.0, max(0.0, float(v))), 2)

        return replace(
            self,
            master_volume=vol(self.master_volume),
            sfx_volume=vol(self.sfx_volume),
            music_volume=vol(self.music_volume),
            window_scale=int(min(4, max(1, int(self.window_scale)))),
            scale_mode=self.scale_mode if self.scale_mode in SCALE_MODES else "smooth",
            game_mode=self.game_mode if self.game_mode in GAME_MODES else "modern",
            difficulty=self.difficulty if self.difficulty in DIFFICULTIES else "normal",
            language=self.language if self.language in LANGUAGES else "es",
            seen_hints=tuple(dict.fromkeys(str(h) for h in self.seen_hints)),
        )

    @property
    def effective_sfx(self) -> float:
        return self.master_volume * self.sfx_volume

    @property
    def effective_music(self) -> float:
        return self.master_volume * self.music_volume


def default_settings_path() -> Path:
    """Junto a la partida guardada (XDG data dir)."""
    return Path.home() / ".local" / "share" / "pop2026canon" / "settings.json"


def to_json(settings: Settings) -> str:
    data = asdict(settings)
    data["seen_hints"] = list(settings.seen_hints)
    return json.dumps(data, indent=2, ensure_ascii=False)


def from_json(text: str) -> Settings:
    """Lee ajustes tolerando ficheros parciales, viejos o corruptos."""
    try:
        raw = json.loads(text)
    except (ValueError, TypeError):
        return Settings()
    if not isinstance(raw, dict):
        return Settings()
    defaults = Settings()
    kwargs: dict[str, Any] = {}
    for f in fields(Settings):
        if f.name not in raw:
            continue
        value = raw[f.name]
        current = getattr(defaults, f.name)
        try:
            if isinstance(current, bool):
                kwargs[f.name] = bool(value)
            elif isinstance(current, int):
                kwargs[f.name] = int(value)
            elif isinstance(current, float):
                kwargs[f.name] = float(value)
            elif isinstance(current, tuple):
                kwargs[f.name] = tuple(str(v) for v in value)
            else:
                kwargs[f.name] = str(value)
        except (TypeError, ValueError):
            continue
    return Settings(**kwargs).validated()


def load(path: Path | None = None) -> Settings:
    p = path or default_settings_path()
    try:
        return from_json(p.read_text(encoding="utf-8"))
    except OSError:
        return Settings()


def save(settings: Settings, path: Path | None = None) -> None:
    p = path or default_settings_path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(to_json(settings), encoding="utf-8")
    except OSError:
        pass  # sin disco escribible el juego sigue con los ajustes en memoria
