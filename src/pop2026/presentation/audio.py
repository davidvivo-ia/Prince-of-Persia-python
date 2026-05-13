"""Audio sintetizado tipo PC-speaker.

Ondas cuadradas mono generadas con numpy y cargadas como ``Sound`` de
pygame. Sin ficheros externos.
"""

from __future__ import annotations

import contextlib

import numpy as np
import pygame

SAMPLE_RATE: int = 22050


def _square_wave(freq: float, duration_s: float, *, volume: float = 0.4) -> np.ndarray:
    """Genera una onda cuadrada PCM int16."""
    n = int(SAMPLE_RATE * duration_s)
    t = np.arange(n) / SAMPLE_RATE
    raw = np.sign(np.sin(2.0 * np.pi * freq * t))
    return (raw * (volume * 32767)).astype(np.int16)


class Beeper:
    """Pequeña batería de sonidos PC-speaker para el juego."""

    def __init__(self, *, mute: bool = False) -> None:
        self._mute = mute
        if mute:
            self._sounds: dict[str, pygame.mixer.Sound] = {}
            return
        sounds: dict[str, pygame.mixer.Sound] = {}
        for name, freq, dur in (
            ("step", 220.0, 0.04),
            ("jump", 440.0, 0.08),
            ("strike", 660.0, 0.05),
            ("parry", 330.0, 0.05),
            ("hurt", 110.0, 0.15),
            ("death", 80.0, 0.30),
            ("victory", 880.0, 0.40),
        ):
            arr = _square_wave(freq, dur)
            arr2 = np.column_stack([arr, arr])
            try:
                snd = pygame.sndarray.make_sound(arr2)
                sounds[name] = snd
            except (pygame.error, ValueError):
                # Sin mixer disponible: degrada a silencio
                self._mute = True
                sounds = {}
                break
        self._sounds = sounds

    def play(self, name: str) -> None:
        """Reproduce un beep por nombre. Silencioso si está muteado."""
        if self._mute:
            return
        snd = self._sounds.get(name)
        if snd is not None:
            with contextlib.suppress(pygame.error):
                snd.play()
