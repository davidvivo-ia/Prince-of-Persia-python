"""Menús navegables con teclado o mando: principal, pausa, opciones y
controles.

La lógica (``Menu.handle``) es pura y está testeada: recibe una
``UiAction`` y los ajustes actuales y devuelve los ajustes nuevos y,
si se eligió una opción, su clave. El dibujo va aparte.
"""

from __future__ import annotations

import functools
import math
from collections.abc import Callable
from dataclasses import dataclass, field

import pygame

from pop2026canon.infrastructure.settings import Settings
from pop2026canon.presentation import fonts
from pop2026canon.presentation.input_device import UiAction
from pop2026canon.presentation.layout import px
from pop2026canon.presentation.palette import PALETTE


@dataclass(frozen=True, slots=True)
class MenuItem:
    key: str
    label: str
    kind: str = "action"
    """``action`` | ``toggle`` | ``slider`` | ``choice``."""
    choices: tuple[tuple[object, str], ...] = ()
    """Para ``choice``: pares (valor, etiqueta)."""
    hint: str = ""


@dataclass
class Menu:
    title: str
    items: list[MenuItem]
    index: int = 0
    subtitle: str = ""
    on_back: str | None = "back"
    """Clave devuelta al pulsar Volver/Pausa (``None``: no se puede salir)."""
    _anim: float = field(default=0.0, repr=False)

    def handle(self, action: UiAction, settings: Settings) -> tuple[Settings, str | None]:
        if not self.items:
            return settings, None
        item = self.items[self.index]
        if action is UiAction.UP:
            self.index = (self.index - 1) % len(self.items)
            return settings, "_move"
        if action is UiAction.DOWN:
            self.index = (self.index + 1) % len(self.items)
            return settings, "_move"
        if action in (UiAction.BACK, UiAction.PAUSE):
            return settings, self.on_back
        if action in (UiAction.LEFT, UiAction.RIGHT):
            delta = -1 if action is UiAction.LEFT else 1
            new = _adjust(item, settings, delta)
            return new, ("_change" if new != settings else None)
        if action is UiAction.CONFIRM:
            if item.kind == "action":
                return settings, item.key
            new = _adjust(item, settings, 1)
            return new, "_change"
        return settings, None

    def value_text(self, item: MenuItem, settings: Settings) -> str:
        if item.kind == "action":
            return ""
        value = getattr(settings, item.key)
        if item.kind == "toggle":
            return "SÍ" if value else "NO"
        if item.kind == "slider":
            return f"{round(float(value) * 100):d}%"
        for v, label in item.choices:
            if v == value:
                return label
        return str(value)


def _adjust(item: MenuItem, settings: Settings, delta: int) -> Settings:
    if item.kind == "toggle":
        return settings.with_(**{item.key: not getattr(settings, item.key)})
    if item.kind == "slider":
        v = round(float(getattr(settings, item.key)) + 0.1 * delta, 2)
        return settings.with_(**{item.key: v})
    if item.kind == "choice" and item.choices:
        values = [v for v, _ in item.choices]
        cur = getattr(settings, item.key)
        i = values.index(cur) if cur in values else 0
        return settings.with_(**{item.key: values[(i + delta) % len(values)]})
    return settings


# ---------------------------------------------------------------------------
# Menús concretos
# ---------------------------------------------------------------------------


def main_menu(has_save: bool, has_progress: bool = False) -> Menu:
    items = []
    if has_save:
        items.append(MenuItem("continue", "Continuar"))
    items.append(MenuItem("new", "Nueva partida"))
    if has_progress:
        items.append(MenuItem("levels", "Niveles"))
    items += [
        MenuItem("options", "Opciones"),
        MenuItem("controls", "Controles"),
        MenuItem("quit", "Salir"),
    ]
    return Menu("", items, on_back=None)


def pause_menu() -> Menu:
    return Menu(
        "PAUSA",
        [
            MenuItem("resume", "Reanudar"),
            MenuItem("restart", "Reiniciar nivel"),
            MenuItem("map", "Mapa"),
            MenuItem("options", "Opciones"),
            MenuItem("controls", "Controles"),
            MenuItem("title", "Salir al título"),
        ],
        on_back="resume",
    )


def options_menu() -> Menu:
    return Menu(
        "OPCIONES",
        [
            MenuItem(
                "game_mode",
                "Modo de juego",
                "choice",
                (("modern", "MODERNO"), ("classic", "CLÁSICO 1989")),
                "Moderno: rebobinar y reaparecer en la sala. Clásico: reglas de 1989.",
            ),
            MenuItem(
                "difficulty",
                "Dificultad",
                "choice",
                (("normal", "NORMAL"), ("hard", "DIFÍCIL")),
                "Difícil: guardias más diestros y 45 minutos. Vale para partidas nuevas.",
            ),
            MenuItem("master_volume", "Volumen general", "slider"),
            MenuItem("music_volume", "Música", "slider"),
            MenuItem("sfx_volume", "Efectos", "slider"),
            MenuItem("fullscreen", "Pantalla completa", "toggle", hint="También F11 o Alt+Enter."),
            MenuItem(
                "window_scale",
                "Tamaño de ventana",
                "choice",
                tuple((i, f"{i}x") for i in (1, 2, 3, 4)),
            ),
            MenuItem(
                "scale_mode",
                "Escalado",
                "choice",
                (("smooth", "SUAVE"), ("pixel", "ENTERO NÍTIDO")),
            ),
            MenuItem("lighting", "Iluminación dinámica", "toggle"),
            MenuItem("particles", "Partículas", "toggle"),
            MenuItem("crt_filter", "Filtro CRT", "toggle"),
            MenuItem("bloom", "Resplandor", "toggle", hint="Halo de llamas y destellos."),
            MenuItem("screen_shake", "Sacudida de cámara", "toggle", hint="Accesibilidad."),
            MenuItem(
                "flashes", "Destellos de daño", "toggle", hint="Accesibilidad: fotosensibilidad."
            ),
            MenuItem("hints", "Pistas", "toggle"),
            MenuItem("always_show_timer", "Reloj siempre visible", "toggle"),
            MenuItem("back", "Volver"),
        ],
    )


CONTROLS: tuple[tuple[str, str, str], ...] = (
    ("Correr", "← →  /  A D", "Cruceta / stick"),
    ("Saltar · trepar", "↑  /  W", "A  (Cruz)"),
    ("Salto largo parado", "↑ + dirección", "A + dirección"),
    ("Agacharse · descolgarse", "↓  /  S", "B  (Círculo)"),
    ("Agarrarse · paso corto", "SHIFT", "RB / RT"),
    ("Atacar", "ESPACIO / J", "X  (Cuadrado)"),
    ("Parar (en guardia)", "↑", "A"),
    ("Rebobinar (moderno)", "R  (mantener)", "LB / LT"),
    ("Pausa · mapa", "ESC · M", "Start · Back"),
    ("Reloj", "TAB", "—"),
    ("Pantalla completa", "F11 · Alt+Enter", "—"),
)


# ---------------------------------------------------------------------------
# Dibujo
# ---------------------------------------------------------------------------


@functools.lru_cache(maxsize=16)
def _panel(w: int, h: int, alpha: int = 232) -> pygame.Surface:
    """Panel de vidrio oscuro con degradado, doble filo dorado y esquinas
    ornamentadas."""
    panel = pygame.Surface((w, h), pygame.SRCALPHA)
    radius = px(10)
    body = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(h):
        k = y / max(1, h - 1)
        col = (int(16 - 6 * k), int(11 - 4 * k), int(30 - 10 * k), alpha)
        pygame.draw.line(body, col, (0, y), (w, y))
    mask = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=radius)
    body.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    panel.blit(body, (0, 0))
    gold, gold_dark = PALETTE.poster_gold, PALETTE.poster_gold_dark
    pygame.draw.rect(panel, (*gold_dark, 255), panel.get_rect(), px(2), border_radius=radius)
    inner = panel.get_rect().inflate(-px(6), -px(6))
    pygame.draw.rect(panel, (*gold, 120), inner, 1, border_radius=radius - px(2))
    # Brillo superior (vidrio)
    sheen = pygame.Surface((w - px(8), px(14)), pygame.SRCALPHA)
    for y in range(sheen.get_height()):
        a = int(26 * (1 - y / sheen.get_height()))
        pygame.draw.line(sheen, (255, 240, 200, a), (0, y), (sheen.get_width(), y))
    panel.blit(sheen, (px(4), px(4)))
    # Rombos dorados en las esquinas
    d = px(5)
    for cx, cy in (
        (px(10), px(10)),
        (w - px(10), px(10)),
        (px(10), h - px(10)),
        (w - px(10), h - px(10)),
    ):
        pygame.draw.polygon(
            panel, (*gold, 230), [(cx, cy - d), (cx + d, cy), (cx, cy + d), (cx - d, cy)]
        )
    return panel


def dim(surf: pygame.Surface, alpha: int = 150) -> None:
    veil = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    veil.fill((0, 0, 0, alpha))
    surf.blit(veil, (0, 0))


def _flame_marker(surf: pygame.Surface, x: int, y: int, t: float) -> None:
    """Marcador de selección: llamita que titila."""
    k = 1.0 + 0.15 * math.sin(t * 14)
    hgt = px(7) * k
    pygame.draw.polygon(
        surf, PALETTE.warning, [(x, y + px(5)), (x + px(4), y - hgt), (x + px(8), y + px(5))]
    )
    pygame.draw.polygon(
        surf,
        (255, 240, 180),
        [(x + px(2), y + px(5)), (x + px(4), y - hgt / 3), (x + px(6), y + px(5))],
    )


def draw_menu(
    surf: pygame.Surface,
    menu: Menu,
    settings: Settings,
    t: float,
    *,
    center_y: int | None = None,
    width: int = 330,
) -> None:
    """``center_y`` en píxeles del lienzo; ``width`` en escala de diseño."""
    w, h = surf.get_size()
    title_h = px(40 if menu.title else 12)
    hint_h = px(26)
    n = max(1, len(menu.items))
    row_h = px(24 if n <= 7 else 21)
    # Que quepa siempre en pantalla (el menú de opciones es largo)
    row_h = min(row_h, (h - px(12) - title_h - hint_h - px(10)) // n)
    ph = title_h + row_h * n + hint_h + px(10)
    cy = center_y if center_y is not None else h // 2 + px(20)
    rect = pygame.Rect(0, 0, px(width), ph)
    rect.center = (w // 2, cy)
    rect.clamp_ip(pygame.Rect(0, px(6), w, h - px(12)))
    surf.blit(_panel(rect.w, rect.h), rect)
    if menu.title:
        title = fonts.render(menu.title, 34, PALETTE.poster_gold, bold=True)
        surf.blit(title, title.get_rect(midtop=(rect.centerx, rect.top + px(10))))
    size = 22 if row_h >= px(24) else (20 if row_h >= px(20) else 18)
    y = rect.top + title_h + px(4)
    for i, item in enumerate(menu.items):
        sel = i == menu.index
        row = pygame.Rect(rect.left + px(12), y, rect.w - px(24), row_h - px(2))
        if sel:
            glow = 90 + int(50 * (0.5 + 0.5 * math.sin(t * 5)))
            bar = pygame.Surface(row.size, pygame.SRCALPHA)
            for x in range(row.w):
                d = x / max(1, row.w - 1)
                a = int(glow * (1 - 0.7 * d))
                pygame.draw.line(bar, (*PALETTE.poster_gold_dark, a), (x, 0), (x, row.h))
            surf.blit(bar, row)
            pygame.draw.line(surf, PALETTE.poster_gold, row.topleft, row.bottomleft, px(2))
            _flame_marker(surf, row.left + px(6), row.centery, t)
        col = PALETTE.primary if sel else PALETTE.primary_dark
        label = fonts.render(item.label, size, col)
        surf.blit(label, label.get_rect(midleft=(row.left + px(18), row.centery)))
        value = menu.value_text(item, settings)
        if value:
            if item.kind == "slider":
                v = float(getattr(settings, item.key))
                bar_r = pygame.Rect(row.right - px(120), row.centery - px(4), px(80), px(8))
                pygame.draw.rect(surf, (40, 30, 50), bar_r, border_radius=bar_r.h // 2)
                fill = bar_r.copy()
                fill.w = int(bar_r.w * v)
                pygame.draw.rect(
                    surf,
                    PALETTE.warning if sel else PALETTE.poster_gold_dark,
                    fill,
                    border_radius=bar_r.h // 2,
                )
                vt = fonts.render(value, 18, col)
                surf.blit(vt, vt.get_rect(midright=(row.right - px(4), row.centery)))
            else:
                text = f"\u2039 {value} \u203a" if sel and item.kind == "choice" else value
                vt = fonts.render(text, size, PALETTE.warning if sel else col)
                surf.blit(vt, vt.get_rect(midright=(row.right - px(4), row.centery)))
        y += row_h
    hint = menu.items[menu.index].hint if menu.items else ""
    if hint:
        ht = fonts.render(hint, 18, PALETTE.muted)
        limit = rect.w - px(20)
        if ht.get_width() > limit:
            ht = pygame.transform.smoothscale(
                ht, (limit, int(ht.get_height() * limit / ht.get_width()))
            )
        surf.blit(ht, ht.get_rect(midbottom=(rect.centerx, rect.bottom - px(8))))


def draw_controls(surf: pygame.Surface, t: float, pad: bool) -> None:
    _ = t
    w, h = surf.get_size()
    rect = pygame.Rect(0, 0, w - px(60), px(46 + 22 * len(CONTROLS) + 40))
    rect.center = (w // 2, h // 2)
    surf.blit(_panel(rect.w, rect.h, 235), rect)
    title = fonts.render("CONTROLES", 34, PALETTE.poster_gold, bold=True)
    surf.blit(title, title.get_rect(midtop=(rect.centerx, rect.top + px(10))))
    head_y = rect.top + px(44)
    cols = (rect.left + px(20), rect.left + rect.w * 0.45, rect.left + rect.w * 0.73)
    for x, label in zip(cols, ("Acción", "Teclado", "Mando" + (" ✓" if pad else "")), strict=True):
        surf.blit(fonts.render(label, 19, PALETTE.warning), (int(x), head_y))
    pygame.draw.line(
        surf,
        PALETTE.poster_gold_dark,
        (rect.left + px(16), head_y + px(20)),
        (rect.right - px(16), head_y + px(20)),
        1,
    )
    for i, (action, kb, gp) in enumerate(CONTROLS):
        y = head_y + px(22 + i * 22)
        if i % 2 == 0:
            stripe = pygame.Surface((rect.w - px(24), px(21)), pygame.SRCALPHA)
            stripe.fill((255, 255, 255, 8))
            surf.blit(stripe, (rect.left + px(12), y - px(1)))
        for x, txt, c in zip(
            cols,
            (action, kb, gp),
            (PALETTE.primary, PALETTE.primary_dark, PALETTE.primary_dark),
            strict=True,
        ):
            surf.blit(fonts.render(txt, 20, c), (int(x), y))
    foot = fonts.render("Enter / B para volver", 18, PALETTE.muted)
    surf.blit(foot, foot.get_rect(midbottom=(rect.centerx, rect.bottom - px(8))))


MenuHandler = Callable[[str], None]
