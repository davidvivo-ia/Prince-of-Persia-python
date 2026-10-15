"""Salida de vídeo: el juego se pinta en un lienzo HD fijo de 1280x852
(el canon a 4x) y se presenta escalado en una ventana redimensionable o a
pantalla completa, con bandas negras para conservar la proporción.

- ``pixel``: escala ENTERA (píxeles nítidos); si la ventana es menor
  que el lienzo, reduce con filtrado (nunca a vecino más próximo).
- ``smooth``: escala fraccionaria suavizada que llena todo lo posible.
- Filtro CRT opcional: líneas de barrido y viñeta de tubo.
"""

from __future__ import annotations

import pygame

from pop2026canon.infrastructure.settings import Settings
from pop2026canon.presentation.layout import LAYOUT


def fit_rect(
    window: tuple[int, int], canvas: tuple[int, int], *, pixel_perfect: bool
) -> tuple[int, int, int, int]:
    """Rectángulo (x, y, w, h) donde presentar el lienzo en la ventana,
    centrado y con la proporción del lienzo."""
    ww, wh = window
    cw, ch = canvas
    if ww <= 0 or wh <= 0:
        return 0, 0, cw, ch
    scale = min(ww / cw, wh / ch)
    if pixel_perfect and scale >= 1.0:
        scale = float(int(scale))
    w = max(1, int(cw * scale))
    h = max(1, int(ch * scale))
    return (ww - w) // 2, (wh - h) // 2, w, h


def window_to_canvas(
    pos: tuple[int, int], window: tuple[int, int], canvas: tuple[int, int], *, pixel_perfect: bool
) -> tuple[int, int] | None:
    """Convierte una posición de la ventana (ratón) al lienzo; ``None``
    si cae en las bandas negras."""
    x, y, w, h = fit_rect(window, canvas, pixel_perfect=pixel_perfect)
    px, py = pos
    if not (x <= px < x + w and y <= py < y + h):
        return None
    return (px - x) * canvas[0] // w, (py - y) * canvas[1] // h


class Display:
    """Ventana + lienzo interno."""

    def __init__(self, settings: Settings) -> None:
        self.canvas_size = (LAYOUT.window_w, LAYOUT.window_h)
        self.canvas = pygame.Surface(self.canvas_size)
        self.settings = settings
        self._windowed_size = self._scaled(settings.window_scale)
        self._crt_cache: pygame.Surface | None = None
        self._crt_size: tuple[int, int] = (0, 0)
        self.window = self._open(settings.fullscreen)

    @staticmethod
    def _scaled(scale: int) -> tuple[int, int]:
        """Tamaño de ventana para el factor de los ajustes (1x = 640x426,
        2x = el lienzo HD a 1:1)."""
        bw, bh = LAYOUT.base_size
        return bw * scale, bh * scale

    def _open(self, fullscreen: bool) -> pygame.Surface:
        if fullscreen:
            return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        size = self._fit_to_desktop(self._windowed_size)
        return pygame.display.set_mode(size, pygame.RESIZABLE)

    def _fit_to_desktop(self, size: tuple[int, int]) -> tuple[int, int]:
        """No abrir una ventana mayor que el escritorio."""
        try:
            desktops = pygame.display.get_desktop_sizes()
        except pygame.error:
            desktops = []
        if not desktops:
            return size
        dw, dh = desktops[0]
        _ = size
        scale = self.settings.window_scale
        while scale > 1 and (
            self._scaled(scale)[0] > dw * 0.95 or self._scaled(scale)[1] > dh * 0.9
        ):
            scale -= 1
        return self._scaled(scale)

    def apply(self, settings: Settings) -> None:
        """Aplica cambios de ajustes de vídeo en caliente."""
        fullscreen_changed = settings.fullscreen != self.settings.fullscreen
        scale_changed = settings.window_scale != self.settings.window_scale
        self.settings = settings
        if scale_changed:
            self._windowed_size = self._scaled(settings.window_scale)
        if fullscreen_changed or (scale_changed and not settings.fullscreen):
            self.window = self._open(settings.fullscreen)

    def on_resize(self, size: tuple[int, int]) -> None:
        if not self.settings.fullscreen:
            self._windowed_size = size
            self.window = pygame.display.get_surface() or self.window

    def to_canvas(self, pos: tuple[int, int]) -> tuple[int, int] | None:
        return window_to_canvas(
            pos,
            self.window.get_size(),
            self.canvas_size,
            pixel_perfect=self.settings.scale_mode == "pixel",
        )

    def present(self) -> None:
        """Escala el lienzo a la ventana y hace flip."""
        win = self.window
        x, y, w, h = fit_rect(
            win.get_size(), self.canvas_size, pixel_perfect=self.settings.scale_mode == "pixel"
        )
        win.fill((0, 0, 0))
        if (w, h) == self.canvas_size:
            frame = self.canvas
        elif self.settings.scale_mode == "smooth" or w < self.canvas_size[0]:
            frame = pygame.transform.smoothscale(self.canvas, (w, h))
        else:
            frame = pygame.transform.scale(self.canvas, (w, h))
        if self.settings.crt_filter:
            frame = frame.copy() if frame is self.canvas else frame
            frame.blit(self._crt_overlay((w, h)), (0, 0))
        win.blit(frame, (x, y))
        pygame.display.flip()

    def _crt_overlay(self, size: tuple[int, int]) -> pygame.Surface:
        if self._crt_cache is None or self._crt_size != size:
            w, h = size
            overlay = pygame.Surface(size, pygame.SRCALPHA)
            step = max(2, h // LAYOUT.base_size[1])
            for yy in range(0, h, step):
                pygame.draw.line(overlay, (0, 0, 0, 70), (0, yy), (w, yy))
            # Viñeta de tubo: bordes oscurecidos
            for i in range(24):
                a = int(90 * (1 - i / 24) ** 2)
                pygame.draw.rect(overlay, (0, 0, 0, a), (i, i, w - 2 * i, h - 2 * i), 1)
            self._crt_cache = overlay
            self._crt_size = size
        return self._crt_cache
