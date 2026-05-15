"""Audio sintetizado canon — ondas cuadradas tipo PC-speaker.

Reutiliza la infraestructura del Beeper del motor viejo pero con
catálogo canon: cada SND_* de :mod:`pop2026canon.domain.seqtbl` se
mapea a un buffer numpy generado.
"""

from __future__ import annotations

import contextlib
from typing import Any

import numpy as np
import pygame

SAMPLE_RATE = 22050


def _square(freq: float, dur: float, volume: float = 0.3) -> Any:
    n = int(SAMPLE_RATE * dur)
    t = np.arange(n) / SAMPLE_RATE
    raw = np.sign(np.sin(2 * np.pi * freq * t))
    fade = min(n, int(SAMPLE_RATE * 0.01))
    env = np.ones(n)
    if fade > 0:
        env[-fade:] = np.linspace(1.0, 0.0, fade)
    return (raw * env * (volume * 32767)).astype(np.int16)


def _glide(start: float, end: float, dur: float, volume: float = 0.3) -> Any:
    n = int(SAMPLE_RATE * dur)
    if n <= 0:
        return np.zeros(0, dtype=np.int16)
    freqs = np.linspace(start, end, n)
    phase = 2 * np.pi * np.cumsum(freqs) / SAMPLE_RATE
    raw = np.sign(np.sin(phase))
    env = np.linspace(1.0, 0.0, n) ** 0.6
    return (raw * env * (volume * 32767)).astype(np.int16)


def _silence(dur: float) -> Any:
    return np.zeros(int(SAMPLE_RATE * dur), dtype=np.int16)


# Catálogo canon de SFX (ver `seqtbl.SND_*`)
_SFX_RECIPES: dict[int, Any] = {}


def _build_sfx() -> None:
    """Genera los buffers la primera vez que se llama a play()."""
    if _SFX_RECIPES:
        return
    _SFX_RECIPES[1] = _square(440, 0.04)  # footstep
    _SFX_RECIPES[2] = _glide(220, 440, 0.10)  # jump
    _SFX_RECIPES[3] = _glide(440, 220, 0.06)  # land_soft
    _SFX_RECIPES[4] = _square(110, 0.20)  # land_hard
    _SFX_RECIPES[5] = _glide(660, 880, 0.08)  # grab
    _SFX_RECIPES[6] = _square(330, 0.05)  # climb
    _SFX_RECIPES[7] = _glide(880, 1320, 0.06)  # strike
    _SFX_RECIPES[8] = _glide(220, 55, 0.6)  # death
    _SFX_RECIPES[9] = _glide(330, 880, 0.4)  # drink
    _SFX_RECIPES[10] = _square(1760, 0.06)  # spike
    _SFX_RECIPES[11] = _glide(220, 110, 0.12)  # chomp
    _SFX_RECIPES[12] = _square(165, 0.10)  # loose crack
    # Nuevos canon
    _SFX_RECIPES[20] = _glide(660, 220, 0.25)  # hurt
    _SFX_RECIPES[21] = _square(880, 0.08)  # clash (espadas)
    _SFX_RECIPES[22] = _glide(440, 880, 0.05)  # parry
    _SFX_RECIPES[23] = _square(660, 0.10)  # gate open
    _SFX_RECIPES[24] = _square(330, 0.15)  # gate close
    _SFX_RECIPES[25] = _glide(880, 220, 0.10)  # plate
    _SFX_RECIPES[26] = _glide(330, 660, 0.20)  # pickup_sword
    _SFX_RECIPES[27] = _glide(220, 1320, 0.4)  # victory_level
    _SFX_RECIPES[28] = _glide(440, 1760, 0.8)  # victory_final
    _SFX_RECIPES[29] = _glide(1760, 110, 0.6)  # mirror_break
    _SFX_RECIPES[30] = _glide(440, 110, 0.3)  # shadow_appear


class Beeper:
    """Reproductor de SFX cuadrados estilo PC-speaker."""

    def __init__(self, *, mute: bool = False) -> None:
        self.mute = mute
        self._sounds: dict[int, pygame.mixer.Sound] = {}
        if not mute:
            with contextlib.suppress(pygame.error):
                pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=1, buffer=512)
        _build_sfx()
        if pygame.mixer.get_init() and not mute:
            for sfx_id, buffer in _SFX_RECIPES.items():
                with contextlib.suppress(pygame.error):
                    self._sounds[sfx_id] = pygame.mixer.Sound(buffer=buffer.tobytes())

    def play(self, sfx_id: int) -> None:
        """Reproduce el SFX por ID. Silencioso si mute o init falló."""
        if self.mute:
            return
        snd = self._sounds.get(sfx_id)
        if snd is not None:
            with contextlib.suppress(pygame.error):
                snd.play()


def is_audio_available() -> bool:
    """``True`` si pygame.mixer pudo inicializarse."""
    return pygame.mixer.get_init() is not None
