"""Audio sintetizado tipo PC-speaker.

Ondas cuadradas y triangulares mono generadas con numpy y cargadas como
``Sound`` de pygame. Sin ficheros externos.
"""

from __future__ import annotations

import contextlib
from typing import Any

import numpy as np
import pygame

from pop2026.domain.actions import Action
from pop2026.domain.game import Game, GameStatus

SAMPLE_RATE: int = 22050


def _square_wave(freq: float, duration_s: float, *, volume: float = 0.4) -> Any:
    """Genera una onda cuadrada PCM int16."""
    n = int(SAMPLE_RATE * duration_s)
    t = np.arange(n) / SAMPLE_RATE
    raw = np.sign(np.sin(2.0 * np.pi * freq * t))
    # Pequeño fade-out para evitar clicks
    env = np.ones(n)
    fade = min(n, int(SAMPLE_RATE * 0.01))
    if fade > 0:
        env[-fade:] = np.linspace(1.0, 0.0, fade)
    return (raw * env * (volume * 32767)).astype(np.int16)


def _glide(start_freq: float, end_freq: float, duration_s: float, *, volume: float = 0.4) -> Any:
    """Onda cuadrada con frecuencia que glide de start a end (efecto descenso)."""
    n = int(SAMPLE_RATE * duration_s)
    if n <= 0:
        return np.zeros(0, dtype=np.int16)
    freqs = np.linspace(start_freq, end_freq, n)
    phase = 2.0 * np.pi * np.cumsum(freqs) / SAMPLE_RATE
    raw = np.sign(np.sin(phase))
    env = np.linspace(1.0, 0.0, n) ** 0.6
    return (raw * env * (volume * 32767)).astype(np.int16)


def _tone(freq: float, duration_s: float, *, volume: float = 0.18) -> Any:
    """Tono cuadrado con envolvente ADSR sencilla (para música ambient)."""
    n = int(SAMPLE_RATE * duration_s)
    if n <= 0:
        return np.zeros(0, dtype=np.int16)
    t = np.arange(n) / SAMPLE_RATE
    raw = np.sign(np.sin(2.0 * np.pi * freq * t))
    # ADSR: attack 5%, decay 10%, sustain 60% @ 0.8, release 25%
    attack = max(1, int(n * 0.05))
    decay = max(1, int(n * 0.10))
    release = max(1, int(n * 0.25))
    sustain = max(1, n - attack - decay - release)
    env = np.concatenate(
        [
            np.linspace(0.0, 1.0, attack),
            np.linspace(1.0, 0.8, decay),
            np.full(sustain, 0.8),
            np.linspace(0.8, 0.0, release),
        ]
    )[:n]
    return (raw * env * (volume * 32767)).astype(np.int16)


def _silence(duration_s: float) -> Any:
    """Silencio del tiempo dado."""
    return np.zeros(int(SAMPLE_RATE * duration_s), dtype=np.int16)


# ---------------------------------------------------------------------------
# Música ambient — composiciones propias en escalas menores. Patrones de
# 8-12 segundos pensados para loop. Volumen bajo: 0.12 para que los SFX
# corten por encima.
# ---------------------------------------------------------------------------


def _ambient_dungeon() -> Any:
    """Loop sombrío en La menor pentatónica (A, C, D, E, G)."""
    notes = [
        (220.00, 0.8),  # A3
        (261.63, 0.6),  # C4
        (293.66, 0.5),  # D4
        (329.63, 0.7),  # E4
        (0.0, 0.3),
        (220.00, 0.6),
        (196.00, 0.5),  # G3
        (174.61, 0.9),  # F3 (color, fuera de la penta pura)
        (0.0, 0.4),
        (130.81, 1.2),  # C3 (grave, fundamento)
    ]
    return _compose(notes, volume=0.12)


def _ambient_palace() -> Any:
    """Loop intermedio: arpegio Re menor armónico (D, F, A, C#)."""
    notes = [
        (293.66, 0.4),  # D4
        (349.23, 0.4),  # F4
        (440.00, 0.4),  # A4
        (554.37, 0.6),  # C#5 (sensible)
        (440.00, 0.4),
        (349.23, 0.4),
        (293.66, 0.8),
        (0.0, 0.3),
        (220.00, 0.4),  # A3
        (146.83, 1.0),  # D3
    ]
    return _compose(notes, volume=0.12)


def _ambient_throne() -> Any:
    """Loop urgente: pasos cromáticos descendentes desde Mi menor."""
    notes = [
        (329.63, 0.30),  # E4
        (311.13, 0.30),  # D#4
        (293.66, 0.30),  # D4
        (277.18, 0.30),  # C#4
        (261.63, 0.50),  # C4
        (0.0, 0.20),
        (164.81, 0.60),  # E3
        (146.83, 0.40),  # D3
        (164.81, 0.40),  # E3
        (196.00, 0.80),  # G3
    ]
    return _compose(notes, volume=0.13)


def _compose(notes: list[tuple[float, float]], *, volume: float) -> Any:
    """Concatena tonos según ``(freq_Hz, duration_s)``; 0 Hz = silencio."""
    parts: list[Any] = []
    for freq, dur in notes:
        if freq <= 0:
            parts.append(_silence(dur))
        else:
            parts.append(_tone(freq, dur, volume=volume))
    return np.concatenate(parts) if parts else np.zeros(0, dtype=np.int16)


def zone_for_level(level_index: int) -> str:
    """Asigna una zona musical según el índice del nivel."""
    if level_index <= 4:
        return "dungeon"
    if level_index <= 8:
        return "palace"
    return "throne"


AMBIENT_TRACKS: dict[str, Any] = {}
"""Cache lazy: el primer uso compila el numpy y se reusa."""


def _ambient_track(zone: str) -> Any:
    """Devuelve el array PCM para el zone (con cache)."""
    if zone in AMBIENT_TRACKS:
        return AMBIENT_TRACKS[zone]
    builder = {
        "dungeon": _ambient_dungeon,
        "palace": _ambient_palace,
        "throne": _ambient_throne,
    }.get(zone, _ambient_dungeon)
    arr = builder()
    AMBIENT_TRACKS[zone] = arr
    return arr


class Beeper:
    """Pequeña batería de sonidos PC-speaker + música ambient para el juego."""

    def __init__(self, *, mute: bool = False) -> None:
        self._mute = mute
        self._music_tracks: dict[str, pygame.mixer.Sound] = {}
        self._current_zone: str | None = None
        if mute:
            self._sounds: dict[str, pygame.mixer.Sound] = {}
            return
        recipes: list[tuple[str, Any]] = [
            ("step", _square_wave(180.0, 0.035, volume=0.25)),
            ("jump", _glide(330.0, 540.0, 0.10, volume=0.35)),
            ("strike", _square_wave(660.0, 0.04, volume=0.45)),
            ("clash", _square_wave(1320.0, 0.05, volume=0.35)),
            ("parry", _square_wave(440.0, 0.05, volume=0.30)),
            ("hurt", _glide(200.0, 90.0, 0.18, volume=0.45)),
            ("death", _glide(180.0, 50.0, 0.45, volume=0.55)),
            ("pickup", _glide(660.0, 1100.0, 0.12, volume=0.35)),
            ("gate", _square_wave(110.0, 0.20, volume=0.45)),
            ("land", _square_wave(140.0, 0.06, volume=0.35)),
            ("victory", _glide(440.0, 880.0, 0.50, volume=0.50)),
            ("grab", _square_wave(280.0, 0.06, volume=0.35)),
            ("lunge", _glide(440.0, 880.0, 0.09, volume=0.45)),
        ]
        sounds: dict[str, pygame.mixer.Sound] = {}
        for name, arr in recipes:
            arr2 = np.column_stack([arr, arr])
            try:
                snd = pygame.sndarray.make_sound(arr2)
                sounds[name] = snd
            except (pygame.error, ValueError):
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

    def play_music(self, zone: str) -> None:
        """Reproduce el loop ambient de la zona dada. No reinicia si ya
        está sonando la misma. Silencioso si está muteado.
        """
        if self._mute or zone == self._current_zone:
            return
        # Carga lazy del Sound (necesita mixer inicializado)
        snd = self._music_tracks.get(zone)
        if snd is None:
            arr = _ambient_track(zone)
            stereo = np.column_stack([arr, arr])
            try:
                snd = pygame.sndarray.make_sound(stereo)
                self._music_tracks[zone] = snd
            except (pygame.error, ValueError):
                return
        with contextlib.suppress(pygame.error):
            # Para la zona anterior si la había
            if self._current_zone is not None:
                prev = self._music_tracks.get(self._current_zone)
                if prev is not None:
                    prev.stop()
            snd.play(loops=-1)
            self._current_zone = zone

    def stop_music(self) -> None:
        """Detiene la música ambient actual."""
        if self._current_zone is None:
            return
        snd = self._music_tracks.get(self._current_zone)
        if snd is not None:
            with contextlib.suppress(pygame.error):
                snd.stop()
        self._current_zone = None


def play_transitions(beeper: Beeper, prev: Game, now: Game) -> None:
    """Compara dos frames consecutivos y dispara los SFX adecuados."""
    p_prev = prev.prince
    p_now = now.prince

    # Cambio de acción
    if p_prev.action is not p_now.action:
        if p_now.action in (Action.JUMP_V, Action.JUMP_R):
            beeper.play("jump")
        elif p_now.action is Action.STRIKE:
            beeper.play("strike")
        elif p_now.action is Action.LUNGE:
            beeper.play("lunge")
        elif p_now.action is Action.PARRY:
            beeper.play("parry")
        elif p_now.action is Action.HANG and p_prev.action is not Action.HANG:
            beeper.play("grab")
        elif p_now.action is Action.FALL and p_prev.action not in (
            Action.JUMP_V,
            Action.JUMP_R,
        ):
            pass  # caída sin sonido específico
        elif p_prev.action is Action.FALL and p_now.action is not Action.DEAD:
            beeper.play("land")

    # Combate: golpes recibidos y dados
    if now.hits_received_total > prev.hits_received_total:
        beeper.play("hurt")
    if now.hits_dealt_total > prev.hits_dealt_total:
        beeper.play("clash")

    # Recoger sable
    if not p_prev.has_sword and p_now.has_sword:
        beeper.play("pickup")

    # Abrir gate
    if len(now.state.open_gates) > len(prev.state.open_gates):
        beeper.play("gate")

    # Beber poción
    if len(now.state.consumed_potions) > len(prev.state.consumed_potions):
        beeper.play("pickup")

    # Muerte / victoria / derrota
    if now.status is not prev.status:
        if now.status is GameStatus.LOST_DIED:
            beeper.play("death")
        elif now.status is GameStatus.WON:
            beeper.play("victory")

    # Pasos durante RUN (cada vez que arranca un nuevo paso)
    if (
        p_now.action is Action.RUN
        and p_now.ticks_in_action == 0
        and p_prev.action is not Action.RUN
    ):
        beeper.play("step")
