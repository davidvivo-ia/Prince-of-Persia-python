"""Tipos de tile canónicos (31 valores, enum `tiles` de SDLPoP types.h).

Cada tile = byte con:
- 5 bits bajos: piece (0..31)
- 3 bits altos: modifier (variante visual o sub-state)

El modifier se usa para variantes (potion type, gate state, etc.).
"""

from __future__ import annotations

from enum import IntEnum


class Tile(IntEnum):
    """31 tipos de tile del POP1 original. Coincide con `enum tiles` en types.h."""

    EMPTY = 0
    """Aire — el kid cae por aquí."""

    FLOOR = 1
    """Suelo sólido pisable."""

    SPIKE = 2
    """Pinchos — letales con caída."""

    PILLAR = 3
    """Columna decorativa estrecha."""

    GATE = 4
    """Reja vertical. Modifier = altura abierta 0..7."""

    STUCK = 5
    """Bloqueado / pieza atascada."""

    CLOSER = 6
    """Botón que CIERRA gates."""

    DOORTOP_WITH_FLOOR = 7
    """Tapiz con suelo pisable encima."""

    BIGPILLAR_BOTTOM = 8
    """Columna grande, mitad inferior."""

    BIGPILLAR_TOP = 9
    """Columna grande, mitad superior."""

    POTION = 10
    """Frasco de poción. Modifier define el tipo (heal/empty/maxhp/poison/float/time)."""

    LOOSE = 11
    """Suelo suelto — cae tras `LOOSE_FLOOR_DELAY` ticks de presión."""

    DOORTOP = 12
    """Tapiz superior (sin suelo)."""

    MIRROR = 13
    """Espejo del nivel 4. Al saltar a través, spawn shadow."""

    DEBRIS = 14
    """Suelo roto (debris de loose). Pisable pero visualmente roto."""

    OPENER = 15
    """Placa de presión. ABRE gates."""

    LEVEL_DOOR_LEFT = 16
    """Mitad izquierda de la puerta de exit del nivel."""

    LEVEL_DOOR_RIGHT = 17
    """Mitad derecha de la puerta de exit del nivel."""

    CHOMPER = 18
    """Mandíbula vertical letal. Modifier define el frame de cierre."""

    TORCH = 19
    """Antorcha decorativa (con llama animada)."""

    WALL = 20
    """Muro sólido decorativo (no pisable, no atravesable)."""

    SKELETON = 21
    """Esqueleto durmiente — se levanta como char `charid_4` al trigger."""

    SWORD = 22
    """Espada recogible."""

    BALCONY_LEFT = 23
    """Balcón izquierdo (niveles avanzados)."""

    BALCONY_RIGHT = 24
    """Balcón derecho."""

    LATTICE_PILLAR = 25
    """Reja decorativa vertical."""

    LATTICE_DOWN = 26
    """Reja descendente."""

    LATTICE_SMALL = 27
    """Reja corta."""

    LATTICE_LEFT = 28
    """Reja con borde izquierdo."""

    LATTICE_RIGHT = 29
    """Reja con borde derecho."""

    TORCH_WITH_DEBRIS = 30
    """Antorcha sobre suelo roto."""


# ---------------------------------------------------------------------------
# Categorías para colisión y queries
# ---------------------------------------------------------------------------

SOLID: frozenset[Tile] = frozenset(
    {
        Tile.FLOOR,
        Tile.LOOSE,
        Tile.PILLAR,
        Tile.BIGPILLAR_BOTTOM,
        Tile.BIGPILLAR_TOP,
        Tile.DOORTOP_WITH_FLOOR,
        Tile.WALL,
        Tile.DEBRIS,
        Tile.GATE,  # solo cuando state CLOSED (chequeo dinámico)
    }
)
"""Tiles sobre los que el kid puede pararse o que bloquean movimiento."""

LETHAL_WITH_FALL: frozenset[Tile] = frozenset({Tile.SPIKE})
"""Tiles letales cuando se aterriza encima con velocidad de caída."""

LETHAL_INSTANT: frozenset[Tile] = frozenset({Tile.CHOMPER})
"""Tiles que matan al pisarlos en estado activo (chomper cerrado)."""

WALKABLE: frozenset[Tile] = frozenset(
    {
        Tile.EMPTY,
        Tile.OPENER,
        Tile.CLOSER,
        Tile.POTION,
        Tile.SWORD,
        Tile.LEVEL_DOOR_LEFT,
        Tile.LEVEL_DOOR_RIGHT,
        Tile.TORCH,
        Tile.SKELETON,  # esqueleto durmiente no bloquea
        Tile.MIRROR,
        Tile.STUCK,
    }
)
"""Tiles que el kid puede atravesar."""


# ---------------------------------------------------------------------------
# Modifiers
# ---------------------------------------------------------------------------


class PotionType(IntEnum):
    """Modifier de `Tile.POTION`. Tipos canónicos de poción."""

    EMPTY = 0
    """Frasco vacío. No tiene efecto."""

    HEAL = 1
    """+1 HP."""

    MAX_HP = 2
    """+1 max HP (la gran)."""

    BOOST = 3
    """Efecto de "levantar al kid" (cinemática)."""

    POISON = 4
    """-1 HP."""

    FLOAT = 5
    """Caída lenta durante `FEATHER_FALL_LENGTH` segundos."""

    TIME = 6
    """+30s de tiempo. Visible sólo en pulsación de tecla."""


def encode_tile(piece: Tile, modifier: int = 0) -> int:
    """Empaqueta tile + modifier en un byte (5+3 bits)."""
    if not (0 <= int(piece) <= 31):
        raise ValueError(f"piece {piece} fuera de [0, 31]")
    if not (0 <= modifier <= 7):
        raise ValueError(f"modifier {modifier} fuera de [0, 7]")
    return int(piece) | (modifier << 5)


def decode_tile(byte: int) -> tuple[Tile, int]:
    """Desempaqueta byte en (tile, modifier)."""
    return Tile(byte & 0x1F), (byte >> 5) & 0x07
