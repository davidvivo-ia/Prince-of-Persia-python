"""Carga de niveles ``.poplv`` desde el paquete y desde disco."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

from pop2026.domain.errors import LevelLoadError
from pop2026.domain.level import Level

BUILTIN_PACKAGE = "pop2026.infrastructure.builtin_levels"


def load_builtin(name: str) -> Level:
    """Carga un nivel built-in por nombre (sin extensión).

    Args:
        name: ``"01_dungeon"``, ``"02_corridor"``…

    Returns:
        ``Level`` parseado.

    Raises:
        LevelLoadError: si el fichero no existe o falla el parseo.
    """
    try:
        text = (
            resources.files(BUILTIN_PACKAGE).joinpath(f"{name}.poplv").read_text(encoding="utf-8")
        )
    except FileNotFoundError as exc:
        raise LevelLoadError(f"Nivel built-in '{name}' no encontrado.") from exc
    return Level.parse(text, name=name)


def load_from_file(path: Path) -> Level:
    """Carga un nivel desde un fichero externo."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise LevelLoadError(f"No se pudo leer {path}: {exc}") from exc
    return Level.parse(text, name=path.stem)


def list_builtin() -> list[str]:
    """Lista los nombres de niveles built-in disponibles, ordenados."""
    names = [
        p.name.removesuffix(".poplv")
        for p in resources.files(BUILTIN_PACKAGE).iterdir()
        if p.name.endswith(".poplv")
    ]
    return sorted(names)
