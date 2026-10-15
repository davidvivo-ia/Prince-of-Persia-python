"""Definición de los ~180 frames canónicos del kid.

Cada frame tiene un id (apunta a un sprite procedural en
`presentation/char_atlas`), un shift sub-tile opcional para alinear
con el char body, y flags para gameplay (sonido implícito, peso
extra para colisión, etc.).

Los rangos documentados en `docs/design/02-frame-system.md §2`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntFlag


class FrameFlag(IntFlag):
    """Banderas opcionales por frame."""

    NORMAL = 0
    """Sin nada especial."""

    SOUND_FOOTSTEP = 1 << 0
    """Pisada — el renderer/audio dispara `SND_FOOTSTEP` al pintar."""

    HEAVY = 1 << 1
    """Peso doble — para detección de loose floor más agresiva."""

    HARM_INVULNERABLE = 1 << 2
    """Inmune a daño durante este frame (animación HURT)."""

    CHAR_MIRROR = 1 << 3
    """Se renderiza espejado independiente de char.direction."""


@dataclass(frozen=True, slots=True)
class Frame:
    """Definición canónica de un frame del kid."""

    id: int
    """0..255. ID único del frame."""

    name: str
    """Nombre semántico (stand, run1, runjump_peak, etc.)."""

    shift_x: int = 0
    """Ajuste sub-tile px horizontal (para alinear silueta con body)."""

    shift_y: int = 0
    """Ajuste sub-tile px vertical."""

    flags: FrameFlag = FrameFlag.NORMAL


# ---------------------------------------------------------------------------
# Catálogo: registramos los frames críticos. El resto se rellenan como
# placeholders con `_default_frame(id)` para no fallar al renderizar.
# ---------------------------------------------------------------------------


def _default_frame(frame_id: int) -> Frame:
    """Placeholder genérico. El renderer pinta una silueta neutral."""
    return Frame(id=frame_id, name=f"f{frame_id:03d}")


_KEY_FRAMES: tuple[Frame, ...] = (
    # Stand / idle
    Frame(15, "stand"),
    # Start run
    Frame(7, "startrun_1", shift_x=1),
    Frame(8, "startrun_2", shift_x=2),
    Frame(9, "startrun_3", shift_x=2),
    Frame(10, "startrun_4", shift_x=2, flags=FrameFlag.SOUND_FOOTSTEP),
    Frame(11, "startrun_5", shift_x=2),
    # Standing jump (16-25 → 16 frames; coincide con SDLPoP)
    Frame(16, "standjump_1"),
    Frame(17, "standjump_2"),
    Frame(18, "standjump_3"),
    Frame(19, "standjump_peak"),
    Frame(20, "standjump_5"),
    Frame(21, "standjump_6"),
    Frame(22, "standjump_7"),
    Frame(23, "standjump_8"),
    Frame(24, "standjump_9"),
    Frame(25, "standjump_10"),
    Frame(26, "standjump_fall_1"),
    Frame(27, "standjump_fall_2"),
    # Run jump (34-44, 11 frames)
    Frame(34, "runjump_1"),
    Frame(35, "runjump_2"),
    Frame(36, "runjump_3"),
    Frame(37, "runjump_4"),
    Frame(38, "runjump_5"),
    Frame(39, "runjump_peak"),
    Frame(40, "runjump_7"),
    Frame(41, "runjump_8"),
    Frame(42, "runjump_9"),
    Frame(43, "runjump_10_frame43"),  # trigger shadow step L6
    Frame(44, "runjump_11"),
    # Turn (45-49)
    Frame(45, "turn_1"),
    Frame(46, "turn_2"),
    Frame(47, "turn_3"),
    Frame(48, "turn_4"),
    Frame(49, "turn_5"),
    # Stop run (50-52)
    Frame(50, "stoprun_1"),
    Frame(51, "stoprun_2"),
    Frame(52, "stoprun_3"),
    # Jump up & hang (67-80)
    Frame(67, "jumpup_grab_1"),
    Frame(68, "jumpup_grab_2"),
    Frame(69, "jumpup_grab_3"),
    Frame(70, "jumpup_grab_4"),
    # Hang straight / variations (81-99)
    Frame(91, "hang_straight"),
    # Fall (102-108)
    Frame(102, "fall_1"),
    Frame(106, "land_1"),
    Frame(107, "land_2"),
    Frame(108, "land_3"),
    # Crouch (110-119)
    Frame(110, "crouch_1"),
    Frame(111, "crouch_2"),
    Frame(112, "crouch_idle"),
    Frame(115, "standup_1"),
    Frame(116, "standup_2"),
    Frame(117, "standup_3"),
    Frame(118, "standup_4"),
    Frame(119, "standup_5"),
    # Run cycle (121-132 — 12 frames)
    *[
        Frame(
            121 + i,
            f"run_{i + 1}",
            flags=(FrameFlag.SOUND_FOOTSTEP if i in (3, 7) else FrameFlag.NORMAL),
        )
        for i in range(12)
    ],
    # Climb up (135-149)
    *[Frame(135 + i, f"climb_{i + 1}") for i in range(15)],
    # Sword (150-176) — engarde, strike, parry, etc.
    Frame(150, "engarde_1"),
    Frame(151, "engarde_2"),
    Frame(152, "engarde_3"),
    Frame(153, "engarde_idle"),
    Frame(161, "block_1"),
    Frame(162, "block_2"),
    Frame(163, "block_3"),
    Frame(164, "block_4"),
    Frame(165, "strike_windup_1"),
    Frame(166, "strike_windup_2"),
    Frame(167, "strike_hit"),  # ventana de impacto
    Frame(168, "strike_recover_1"),
    Frame(169, "strike_recover_2"),
    Frame(170, "strike_recover_3"),
    Frame(171, "stabbed_1"),
    Frame(172, "stabbed_2"),
    Frame(173, "stabbed_3"),
    Frame(174, "stabbed_4"),
    Frame(175, "stabbed_5"),
    # Letales
    Frame(177, "spiked", flags=FrameFlag.HARM_INVULNERABLE),
    Frame(178, "chomped", flags=FrameFlag.HARM_INVULNERABLE),
    # Muerte
    Frame(179, "death_1"),
    Frame(180, "death_2"),
    Frame(181, "death_3"),
    Frame(182, "death_4"),
    Frame(183, "death_5"),
    Frame(184, "death_6"),
    Frame(185, "death_flat"),
    # Drink potion (191-205)
    *[Frame(191 + i, f"drink_{i + 1}") for i in range(15)],
    # Draw sword (207-210)
    Frame(207, "drawsword_1"),
    Frame(208, "drawsword_2"),
    Frame(209, "drawsword_3"),
    Frame(210, "drawsword_4"),
    # Exit stairs (217-228)
    *[Frame(217 + i, f"exit_{i + 1}") for i in range(12)],
    # Found sword (229)
    Frame(229, "found_sword"),
    # Sheathe sword (230-240)
    *[Frame(230 + i, f"sheathe_{i + 1}") for i in range(11)],
)


# Tabla por ID: lookup rápido, fallback a default.
_FRAME_BY_ID: dict[int, Frame] = {f.id: f for f in _KEY_FRAMES}


def get_frame(frame_id: int) -> Frame:
    """Devuelve el frame por id. Si no está catalogado, devuelve un
    placeholder genérico."""
    return _FRAME_BY_ID.get(frame_id, _default_frame(frame_id))


def all_known_frame_ids() -> tuple[int, ...]:
    """IDs catalogados (para tests)."""
    return tuple(sorted(_FRAME_BY_ID.keys()))


def total_known_frames() -> int:
    """Cantidad de frames con definición explícita."""
    return len(_FRAME_BY_ID)
