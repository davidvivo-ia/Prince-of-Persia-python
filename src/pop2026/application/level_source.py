"""Source unificado de niveles: built-in (1..12) + procedural (13..100).

Decide si un ``level_index`` se carga desde los ``.poplv`` empaquetados
o se genera procedimentalmente. Es la única función que el runner debe
llamar para obtener un :class:`Level`.
"""

from __future__ import annotations

from pop2026.application.campaign import CAMPAIGN
from pop2026.application.level_generator import GeneratorConfig, generate
from pop2026.domain.errors import LevelLoadError
from pop2026.domain.level import Level
from pop2026.infrastructure.levels import load_builtin

HAND_CRAFTED_COUNT: int = 12
"""Niveles con ``.poplv`` propio. Los demás son procedurales."""


def load_level(level_index: int, *, seed: int = 42) -> Level:
    """Devuelve el ``Level`` para ``level_index`` (1..100).

    Args:
        level_index: Índice del nivel (1..100).
        seed: Semilla para el generador procedural (sólo usada si
            ``level_index > HAND_CRAFTED_COUNT``).

    Returns:
        ``Level`` listo para :func:`pop2026.domain.game.new_game`.

    Raises:
        LevelLoadError: si el índice está fuera de rango o el slug
            built-in no existe.
    """
    if level_index < 1 or level_index > 100:
        raise LevelLoadError(f"level_index fuera de rango 1..100: {level_index}")

    if level_index <= HAND_CRAFTED_COUNT:
        slug = CAMPAIGN[level_index - 1].slug
        return load_builtin(slug)

    return generate(GeneratorConfig(level_index=level_index, seed=seed))
