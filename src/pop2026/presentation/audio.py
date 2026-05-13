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


class Beeper:
    """Pequeña batería de sonidos PC-speaker para el juego."""

    def __init__(self, *, mute: bool = False) -> None:
        self._mute = mute
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
        elif p_now.action is Action.PARRY:
            beeper.play("parry")
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
