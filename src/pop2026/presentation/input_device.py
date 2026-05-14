"""Mapeo de eventos pygame a :class:`InputFrame`.

pygame se importa perezosamente para que el dominio/aplicación sigan
testeables sin SDL. Los tests de presentación usan
``SDL_VIDEODRIVER=dummy``.
"""

from __future__ import annotations

import pygame

from pop2026.domain.input import InputFrame, PlayerCommand


def poll() -> InputFrame:
    """Lee el estado del teclado y devuelve un ``InputFrame``.

    El salto (``RETURN``) se procesa como canal independiente
    (``jump_pressed`` / ``jump_held``) para que pueda combinarse con
    cualquier dirección — running jump real.
    """
    keys = pygame.key.get_pressed()

    walk = bool(keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT])
    jump_held = bool(keys[pygame.K_RETURN])
    # Mantenemos `jump_pressed=True` mientras la tecla esté pulsada;
    # el buffer de salto del motor (JUMP_BUFFER_TICKS) absorbe el
    # ruido por si el jugador la deja apretada al aterrizar.
    jump_pressed = jump_held

    # Acciones puras de combate / dirección (excluyentes entre sí).
    if keys[pygame.K_x]:
        cmd = PlayerCommand.LUNGE
    elif keys[pygame.K_SPACE]:
        cmd = PlayerCommand.STRIKE
    elif keys[pygame.K_q]:
        cmd = PlayerCommand.PARRY
    elif keys[pygame.K_UP] or keys[pygame.K_w]:
        cmd = PlayerCommand.UP
    elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
        cmd = PlayerCommand.DOWN
    elif keys[pygame.K_LEFT] or keys[pygame.K_a]:
        cmd = PlayerCommand.LEFT
    elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        cmd = PlayerCommand.RIGHT
    elif jump_held:
        # Sólo JUMP en command si no hay dirección activa: el motor
        # leerá igualmente `jump_pressed` para disparar el salto.
        cmd = PlayerCommand.JUMP
    else:
        cmd = PlayerCommand.NONE

    return InputFrame(
        command=cmd,
        walk_modifier=walk,
        jump_pressed=jump_pressed,
        jump_held=jump_held,
    )


def should_quit() -> bool:
    """``True`` si hay evento QUIT o ESC pulsado."""
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return True
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return True
    return False
