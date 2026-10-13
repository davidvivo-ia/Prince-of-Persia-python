"""Menús navegables con teclado o mando: principal, pausa, opciones y
controles.

La lógica (``Menu.handle``) es pura y está testeada: recibe una
``UiAction`` y los ajustes actuales y devuelve los ajustes nuevos y,
si se eligió una opción, su clave. El dibujo va aparte.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field

import pygame

from pop2026canon.infrastructure.settings import Settings
from pop2026canon.presentation import fonts
from pop2026canon.presentation.input_device import UiAction
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


def main_menu(has_save: bool) -> Menu:
    items = []
    if has_save:
        items.append(MenuItem("continue", "Continuar"))
    items += [
        MenuItem("new", "Nueva partida"),
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
                (("pixel", "PÍXEL NÍTIDO"), ("smooth", "SUAVE")),
            ),
            MenuItem("lighting", "Iluminación dinámica", "toggle"),
            MenuItem("particles", "Partículas", "toggle"),
            MenuItem("crt_filter", "Filtro CRT", "toggle"),
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


def _panel(w: int, h: int, alpha: int = 232) -> pygame.Surface:
    panel = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(panel, (10, 7, 20, alpha), panel.get_rect(), border_radius=10)
    pygame.draw.rect(panel, (*PALETTE.poster_gold_dark, 255), panel.get_rect(), 2, border_radius=10)
    pygame.draw.rect(
        panel, (*PALETTE.poster_gold, 120), panel.get_rect().inflate(-6, -6), 1, border_radius=8
    )
    return panel


def dim(surf: pygame.Surface, alpha: int = 150) -> None:
    veil = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    veil.fill((0, 0, 0, alpha))
    surf.blit(veil, (0, 0))


def draw_menu(
    surf: pygame.Surface,
    menu: Menu,
    settings: Settings,
    t: float,
    *,
    center_y: int | None = None,
    width: int = 330,
) -> None:
    w, h = surf.get_size()
    row_h = 24 if len(menu.items) <= 7 else 21
    title_h = 40 if menu.title else 12
    hint_h = 26
    ph = title_h + row_h * len(menu.items) + hint_h + 10
    cy = center_y if center_y is not None else h // 2 + 20
    rect = pygame.Rect(0, 0, width, ph)
    rect.center = (w // 2, cy)
    surf.blit(_panel(rect.w, rect.h), rect)
    if menu.title:
        title = fonts.render(menu.title, 34, PALETTE.poster_gold, bold=True)
        surf.blit(title, title.get_rect(midtop=(rect.centerx, rect.top + 10)))
    size = 22 if row_h >= 24 else 20
    y = rect.top + title_h + 4
    for i, item in enumerate(menu.items):
        sel = i == menu.index
        row = pygame.Rect(rect.left + 12, y, rect.w - 24, row_h - 2)
        if sel:
            glow = 90 + int(50 * (0.5 + 0.5 * math.sin(t * 5)))
            bar = pygame.Surface(row.size, pygame.SRCALPHA)
            bar.fill((*PALETTE.poster_gold_dark, glow))
            surf.blit(bar, row)
            # marcador: llama
            fx = row.left + 6
            fy = row.centery
            pygame.draw.polygon(
                surf, PALETTE.warning, [(fx, fy + 5), (fx + 4, fy - 6), (fx + 8, fy + 5)]
            )
        col = PALETTE.primary if sel else PALETTE.primary_dark
        label = fonts.render(item.label, size, col)
        surf.blit(label, label.get_rect(midleft=(row.left + 18, row.centery)))
        value = menu.value_text(item, settings)
        if value:
            if item.kind == "slider":
                v = float(getattr(settings, item.key))
                bar_r = pygame.Rect(row.right - 120, row.centery - 4, 80, 8)
                pygame.draw.rect(surf, (40, 30, 50), bar_r, border_radius=4)
                fill = bar_r.copy()
                fill.w = int(bar_r.w * v)
                pygame.draw.rect(
                    surf,
                    PALETTE.warning if sel else PALETTE.poster_gold_dark,
                    fill,
                    border_radius=4,
                )
                vt = fonts.render(value, 18, col)
                surf.blit(vt, vt.get_rect(midright=(row.right - 4, row.centery)))
            else:
                text = f"\u2039 {value} \u203a" if sel and item.kind == "choice" else value
                vt = fonts.render(text, size, PALETTE.warning if sel else col)
                surf.blit(vt, vt.get_rect(midright=(row.right - 4, row.centery)))
        y += row_h
    hint = menu.items[menu.index].hint if menu.items else ""
    if hint:
        ht = fonts.render(hint, 18, PALETTE.muted)
        if ht.get_width() > rect.w - 20:
            ht = pygame.transform.smoothscale(
                ht, (rect.w - 20, int(ht.get_height() * (rect.w - 20) / ht.get_width()))
            )
        surf.blit(ht, ht.get_rect(midbottom=(rect.centerx, rect.bottom - 8)))


def draw_controls(surf: pygame.Surface, t: float, pad: bool) -> None:
    _ = t
    w, h = surf.get_size()
    rect = pygame.Rect(0, 0, w - 60, 46 + 22 * len(CONTROLS) + 40)
    rect.center = (w // 2, h // 2)
    surf.blit(_panel(rect.w, rect.h, 235), rect)
    title = fonts.render("CONTROLES", 34, PALETTE.poster_gold, bold=True)
    surf.blit(title, title.get_rect(midtop=(rect.centerx, rect.top + 10)))
    head_y = rect.top + 44
    cols = (rect.left + 20, rect.left + rect.w * 0.45, rect.left + rect.w * 0.73)
    for x, label in zip(cols, ("Acción", "Teclado", "Mando" + (" ✓" if pad else "")), strict=True):
        surf.blit(fonts.render(label, 19, PALETTE.warning), (int(x), head_y))
    for i, (action, kb, gp) in enumerate(CONTROLS):
        y = head_y + 22 + i * 22
        for x, txt, c in zip(
            cols,
            (action, kb, gp),
            (PALETTE.primary, PALETTE.primary_dark, PALETTE.primary_dark),
            strict=True,
        ):
            surf.blit(fonts.render(txt, 20, c), (int(x), y))
    foot = fonts.render("Enter / B para volver", 18, PALETTE.muted)
    surf.blit(foot, foot.get_rect(midbottom=(rect.centerx, rect.bottom - 8)))


MenuHandler = Callable[[str], None]
