"""Mapeo de eventos pygame a :class:`InputFrame`.

pygame se importa perezosamente para que el dominio/aplicación sigan
testeables sin SDL. Los tests de presentación usan
``SDL_VIDEODRIVER=dummy``.
"""

from __future__ import annotations

import pygame

from pop2026.domain.input import InputFrame, PlayerCommand


def poll() -> InputFrame:
    """Lee el estado del teclado y devuelve un ``InputFrame``."""
    keys = pygame.key.get_pressed()

    walk = bool(keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT])

    if keys[pygame.K_x]:
        return InputFrame(command=PlayerCommand.LUNGE, walk_modifier=walk)
    if keys[pygame.K_SPACE]:
        return InputFrame(command=PlayerCommand.STRIKE, walk_modifier=walk)
    if keys[pygame.K_q]:
        return InputFrame(command=PlayerCommand.PARRY, walk_modifier=walk)
    if keys[pygame.K_UP] or keys[pygame.K_w]:
        return InputFrame(command=PlayerCommand.UP, walk_modifier=walk)
    if keys[pygame.K_DOWN] or keys[pygame.K_s]:
        return InputFrame(command=PlayerCommand.DOWN, walk_modifier=walk)
    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        return InputFrame(command=PlayerCommand.LEFT, walk_modifier=walk)
    if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        return InputFrame(command=PlayerCommand.RIGHT, walk_modifier=walk)
    if keys[pygame.K_RETURN]:
        return InputFrame(command=PlayerCommand.JUMP, walk_modifier=walk)
    return InputFrame()


def should_quit() -> bool:
    """``True`` si hay evento QUIT o ESC pulsado."""
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return True
    return False
