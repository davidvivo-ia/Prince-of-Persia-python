"""Tipografía de la interfaz.

La fuente por defecto de pygame no tiene flechas ni símbolos, así que
se busca una fuente del sistema que los tenga (DejaVu, Noto, Segoe UI,
Arial...). Si no hay ninguna, ``render`` sustituye los símbolos por
palabras para que nunca salga un recuadro vacío.
"""

from __future__ import annotations

import functools

import pygame

_CANDIDATES = (
    "dejavusans",
    "notosans",
    "segoeui",
    "segoeuisymbol",
    "arial",
    "liberationsans",
    "freesans",
    "helvetica",
)

_FALLBACK_TEXT = {
    "←": "IZQ",
    "→": "DER",
    "↑": "ARRIBA",
    "↓": "ABAJO",
    "✓": "(ok)",
    "\u2039": "<",
    "\u203a": ">",
    "·": "-",
}


def _has_glyphs(f: pygame.font.Font) -> bool:
    try:
        missing = f.metrics("￿")[0]
        return all(f.metrics(ch)[0] != missing for ch in "←↑✓\u2039")
    except (pygame.error, TypeError, IndexError):
        return False


@functools.lru_cache(maxsize=1)
def _best_name() -> str | None:
    for name in _CANDIDATES:
        path = pygame.font.match_font(name)
        if not path:
            continue
        try:
            if _has_glyphs(pygame.font.Font(path, 16)):
                return path
        except (pygame.error, OSError):
            continue
    return None


_CACHE: dict[tuple[int, bool], pygame.font.Font] = {}


def _alive(f: pygame.font.Font) -> bool:
    try:
        f.size("a")
    except pygame.error:
        return False
    return True


def font(size: int, bold: bool = False) -> pygame.font.Font:
    """Fuente de interfaz. ``size`` en la escala de la fuente por defecto
    de pygame (las fuentes del sistema se reducen un poco para casar).

    Cacheada; si pygame se reinició (las fuentes viejas quedan inválidas)
    la caché se rehace."""
    key = (size, bold)
    f = _CACHE.get(key)
    if f is not None and _alive(f):
        return f
    if f is not None:
        _CACHE.clear()
    if not pygame.font.get_init():
        pygame.font.init()
    path = _best_name()
    f = (
        pygame.font.Font(None, size)
        if path is None
        else pygame.font.Font(path, max(8, int(size * 0.72)))
    )
    f.set_bold(bold)
    _CACHE[key] = f
    return f


@functools.lru_cache(maxsize=1)
def has_symbols() -> bool:
    return _best_name() is not None


def safe(text: str) -> str:
    if has_symbols():
        return text
    for k, v in _FALLBACK_TEXT.items():
        text = text.replace(k, v)
    return text


def render(
    text: str, size: int, color: tuple[int, int, int], *, bold: bool = False
) -> pygame.Surface:
    return font(size, bold).render(safe(text), True, color)
