"""Adaptador de teclado pygame → :class:`Command` del dominio.

Mapeo canon-friendly:
- Flechas: dirección
- Shift (izquierdo o derecho): grab / sword / running
- Z / Enter: jump (alternativo a "arriba")
- A / Space: strike
"""

from __future__ import annotations

import pygame

from pop2026canon.application.controller import Command


def poll() -> Command:
    """Lee el estado actual del teclado y devuelve un Command."""
    keys = pygame.key.get_pressed()

    return Command(
        left=bool(keys[pygame.K_LEFT] or keys[pygame.K_a]),
        right=bool(keys[pygame.K_RIGHT] or keys[pygame.K_d]),
        up=bool(keys[pygame.K_UP] or keys[pygame.K_w]),
        down=bool(keys[pygame.K_DOWN] or keys[pygame.K_s]),
        shift=bool(keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]),
        strike=bool(keys[pygame.K_SPACE] or keys[pygame.K_q]),
    )


def should_quit() -> bool:
    """Detecta QUIT o ESC pulsado en la cola de eventos."""
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return True
    return False
