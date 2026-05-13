"""Entrypoint del paquete. ``python -m pop2026`` y ``pop2026`` lo invocan."""

from __future__ import annotations


def main() -> None:
    """Lanza la CLI Typer."""
    from pop2026.presentation.cli import app

    app()


if __name__ == "__main__":
    main()
