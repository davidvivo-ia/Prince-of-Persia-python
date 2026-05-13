"""Launcher para Windows/macOS/Linux sin necesidad de ``uv``.

Uso::

    python persia.py                 # juega
    python persia.py --demo --seed 42
    python persia.py --help

Si las dependencias no están instaladas, el script lo detecta e indica
qué hacer (``pip install -e .`` o ``pip install -r requirements.txt``).
"""

from __future__ import annotations

import sys
from pathlib import Path


def _ensure_src_on_path() -> None:
    """Añade ``src/`` al ``sys.path`` para correr sin instalar el paquete."""
    here = Path(__file__).resolve().parent
    src = here / "src"
    if src.is_dir() and str(src) not in sys.path:
        sys.path.insert(0, str(src))


def _hint_missing(pkg: str, exc: BaseException) -> None:
    print(f"[pop2026] Falta la dependencia '{pkg}': {exc}", file=sys.stderr)
    print("", file=sys.stderr)
    print("Instala las dependencias con uno de estos comandos:", file=sys.stderr)
    print("    python -m pip install -e .", file=sys.stderr)
    print("    python -m pip install -r requirements.txt", file=sys.stderr)
    print("", file=sys.stderr)
    print(
        "También puedes usar 'uv sync' si tienes uv: https://docs.astral.sh/uv/",
        file=sys.stderr,
    )


_MIN_PYTHON = (3, 13)


def main() -> int:
    # Comprobamos en runtime: ruff sabe que el código corre en 3.13+,
    # pero queremos un mensaje amable si alguien lo lanza con 3.11/3.12.
    if sys.version_info < _MIN_PYTHON:
        print(
            f"[pop2026] Requiere Python {_MIN_PYTHON[0]}.{_MIN_PYTHON[1]}+ "
            f"(tienes {sys.version.split()[0]}).",
            file=sys.stderr,
        )
        return 2

    _ensure_src_on_path()
    try:
        from pop2026.presentation.cli import app
    except ModuleNotFoundError as exc:
        _hint_missing(exc.name or "?", exc)
        return 1
    try:
        app()
    except SystemExit as exc:
        return int(exc.code or 0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
