"""Tipografía de la interfaz.

La fuente por defecto de pygame no tiene flechas ni símbolos, así que
se busca una fuente del sistema que los tenga (DejaVu, Noto, Segoe UI,
Arial...). Si no hay ninguna, ``render`` sustituye los símbolos por
palabras para que nunca salga un recuadro vacío.
"""

from __future__ import annotations

import functools
import itertools

import pygame

from pop2026canon.presentation.layout import px

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
    de pygame a tamaño de diseño (se multiplica por la escala HD; las
    fuentes del sistema se reducen un poco para casar).

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
    real = px(size)
    f = (
        pygame.font.Font(None, real)
        if path is None
        else pygame.font.Font(path, max(8, int(real * 0.72)))
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


_SERIFS = (
    "palatinolinotype",
    "bookantiqua",
    "georgia",
    "dejavuserif",
    "liberationserif",
    "freeserif",
    "timesnewroman",
)


@functools.lru_cache(maxsize=1)
def _serif_path() -> str | None:
    for name in _SERIFS:
        path = pygame.font.match_font(name, bold=True) or pygame.font.match_font(name)
        if path:
            return path
    return None


_TITLE_CACHE: dict[int, pygame.font.Font] = {}


def title_font(size: int) -> pygame.font.Font:
    """Fuente con serifa para títulos (cae a la de interfaz en negrita)."""
    f = _TITLE_CACHE.get(size)
    if f is not None and _alive(f):
        return f
    if f is not None:
        _TITLE_CACHE.clear()
    if not pygame.font.get_init():
        pygame.font.init()
    path = _serif_path()
    if path is None:
        return font(size, True)
    f = pygame.font.Font(path, max(8, int(px(size) * 0.72)))
    _TITLE_CACHE[size] = f
    return f


@functools.lru_cache(maxsize=48)
def _gold_cached(text: str, size: int, glow: int, top: tuple[int, int, int]) -> pygame.Surface:
    f = title_font(size)
    mask = f.render(safe(text), True, (255, 255, 255))
    w, h = mask.get_size()
    pad = px(glow) * 2 + px(4)
    out = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
    # Halo cálido difuminado
    if glow:
        halo = pygame.Surface(out.get_size(), pygame.SRCALPHA)
        tinted = f.render(safe(text), True, (255, 170, 60))
        halo.blit(tinted, (pad, pad))
        halo = pygame.transform.box_blur(halo, px(glow))
        halo = pygame.transform.box_blur(halo, px(glow))
        out.blit(halo, (0, 0))
        out.blit(halo, (0, 0))
    # Sombra/relieve inferior
    deep = f.render(safe(text), True, (70, 34, 8))
    out.blit(deep, (pad + px(2), pad + px(3)))
    # Relleno con degradado vertical metálico (claro arriba, banda brillante, oscuro abajo)
    grad = pygame.Surface((w, h), pygame.SRCALPHA)
    stops = ((0.0, top), (0.45, (240, 190, 80)), (0.55, (190, 120, 30)), (1.0, (250, 210, 120)))
    for y in range(h):
        k = y / max(1, h - 1)
        for (k0, c0), (k1, c1) in itertools.pairwise(stops):
            if k0 <= k <= k1:
                u = (k - k0) / (k1 - k0)
                col = tuple(int(c0[i] + (c1[i] - c0[i]) * u) for i in range(3))
                break
        pygame.draw.line(grad, (*col, 255), (0, y), (w, y))
    grad.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    out.blit(grad, (pad, pad))
    # Filo claro superior
    edge = f.render(safe(text), True, (255, 250, 220))
    edge.set_alpha(90)
    out.blit(edge, (pad - 1, pad - 1))
    out.blit(grad, (pad, pad))
    return out


def gold_title(
    text: str, size: int, *, glow: int = 6, top: tuple[int, int, int] = (255, 244, 200)
) -> pygame.Surface:
    """Texto de título en oro metálico con halo (cacheado)."""
    return _gold_cached(text, size, glow, top)
