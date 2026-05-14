"""Persistencia simple de partida en JSON (XDG)."""

from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from pop2026.domain.errors import SaveCorruptedError

SAVE_VERSION: int = 1
"""Versión actual del schema. Cambiar al modificar campos."""


class SaveGame(BaseModel):
    """Snapshot persistible del estado de partida."""

    version: int = Field(default=SAVE_VERSION)
    level: int = Field(ge=1, le=100)
    hp: int = Field(ge=0, le=99)
    max_hp: int = Field(ge=1, le=99)
    time_left_ms: int = Field(ge=0)
    rng_seed: int = Field(ge=0, le=0xFF)


def default_path() -> Path:
    """Ruta XDG para el fichero de guardado."""
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return base / "pop2026" / "save.json"


def save(state: SaveGame, path: Path | None = None) -> Path:
    """Escribe la partida en JSON. Crea directorios si faltan."""
    target = path or default_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(state.model_dump_json(indent=2), encoding="utf-8")
    return target


def load(path: Path | None = None) -> SaveGame | None:
    """Lee la partida si existe; ``None`` si no hay fichero.

    Raises:
        SaveCorruptedError: si el JSON está mal formado o no valida.
    """
    target = path or default_path()
    if not target.exists():
        return None
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
        return SaveGame.model_validate(raw)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise SaveCorruptedError(f"Guardado corrupto en {target}: {exc}") from exc
