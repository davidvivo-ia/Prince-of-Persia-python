"""Tests del Beeper + audio_bridge."""

from __future__ import annotations

import os

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from pop2026canon.application.audio_bridge import play_transitions
from pop2026canon.domain.game import new_game
from pop2026canon.domain.levels_canon import LEVEL_1
from pop2026canon.infrastructure.audio import Beeper


def test_beeper_mute_does_not_crash() -> None:
    pygame.init()
    try:
        beeper = Beeper(mute=True)
        for sfx_id in range(1, 31):
            beeper.play(sfx_id)  # no debe crashear
    finally:
        pygame.quit()


def test_play_transitions_no_crash() -> None:
    pygame.init()
    try:
        beeper = Beeper(mute=True)
        prev = new_game(LEVEL_1)
        now = new_game(LEVEL_1)
        play_transitions(beeper, prev, now)  # sin transiciones
    finally:
        pygame.quit()
