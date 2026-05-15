"""Tabla de secuencias canónicas — DSL + 25 secuencias críticas.

Cada secuencia es una cadena de :class:`SeqAct`. El motor avanza por
una secuencia tick a tick hasta encontrar un ``FRAME`` (= un frame
visible). Acts intermedios aplican ``dx``/``dy``, sonido, fall config,
o saltan a otra secuencia.

Las 25 secuencias aquí cubren el bucle de juego básico (stand, run,
jump, fall, hang, climb, basic combat, muertes por trampas). Las
otras ~70 (las 94 totales documentadas en `docs/audit.md`) se
añadirán progresivamente en FASE 3.3.

> Los valores de ``dx``/``dy`` por act son **aproximaciones canónicas
> documentadas** — derivadas del comportamiento descrito por SDLPoP
> seqtbl.c. Para una paridad byte-perfect haría falta extracción
> mecánica de cada `act_*` macro del .c original.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from pop2026canon.domain.actions import Action, FrameID, Seq


class ActKind(IntEnum):
    """Tipo de acto dentro de una secuencia."""

    FRAME = 0
    """Pinta el frame ``arg``. **Termina el tick.**"""

    DX = 1
    """Desplaza ``arg`` px sub-tile en la dirección del char."""

    DY = 2
    """Desplaza ``arg`` px sub-tile vertical (positivo = abajo)."""

    SND = 3
    """Dispara sonido ``arg`` (id en domain/audio)."""

    SET_FALL = 4
    """Configura fall_x = ``arg`` y fall_y = ``arg2``."""

    JMP = 5
    """Salta a la secuencia ``arg`` (índice 0 reseteado)."""

    SETUP = 6
    """Cambia char.action a Action(arg)."""

    NOP = 7
    """No-op (placeholder)."""


@dataclass(frozen=True, slots=True)
class SeqAct:
    """Un acto dentro de una secuencia."""

    kind: ActKind
    arg: int
    arg2: int = 0


Sequence = tuple[SeqAct, ...]
"""Una secuencia completa = tupla de actos."""


# ---------------------------------------------------------------------------
# Constructores de actos (azúcar sintáctico)
# ---------------------------------------------------------------------------


def frame(n: int | FrameID) -> SeqAct:
    return SeqAct(ActKind.FRAME, int(n))


def dx(n: int) -> SeqAct:
    return SeqAct(ActKind.DX, n)


def dy(n: int) -> SeqAct:
    return SeqAct(ActKind.DY, n)


def snd(n: int) -> SeqAct:
    return SeqAct(ActKind.SND, n)


def set_fall(fx: int, fy: int) -> SeqAct:
    return SeqAct(ActKind.SET_FALL, fx, fy)


def jmp(to: Seq | int) -> SeqAct:
    return SeqAct(ActKind.JMP, int(to))


def setup(action: Action | int) -> SeqAct:
    return SeqAct(ActKind.SETUP, int(action))


# ---------------------------------------------------------------------------
# Catálogo de secuencias (subset canónico)
# ---------------------------------------------------------------------------

# IDs de sonido (placeholders para SND — el módulo audio los resolverá)
SND_FOOTSTEP = 1
SND_JUMP = 2
SND_LAND_SOFT = 3
SND_LAND_HARD = 4
SND_GRAB = 5
SND_CLIMB = 6
SND_STRIKE = 7
SND_DEATH = 8
SND_DRINK = 9
SND_SPIKE = 10
SND_CHOMP = 11
SND_LOOSE_CRACK = 12


# ===========================================================================
# Stand / idle
# ===========================================================================

_SEQ_STAND: Sequence = (
    setup(Action.STAND),
    frame(FrameID.STAND),
    jmp(Seq.STAND),  # se queda quieto auto-repitiendo
)


# ===========================================================================
# Run
# ===========================================================================

# Start_run: 5 frames de windup desde stand
_SEQ_START_RUN: Sequence = (
    setup(Action.RUN_JUMP),
    frame(7),
    dx(1),
    frame(8),
    dx(2),
    frame(9),
    dx(2),
    frame(10),
    dx(2),
    snd(SND_FOOTSTEP),
    frame(11),
    dx(2),
    jmp(Seq.RUN),
)

# Run: ciclo de 12 frames (121..132) cubriendo ~2 tiles
_SEQ_RUN: Sequence = (
    setup(Action.RUN_JUMP),
    frame(121),
    dx(2),
    frame(122),
    dx(2),
    frame(123),
    dx(2),
    frame(124),
    dx(2),
    snd(SND_FOOTSTEP),
    frame(125),
    dx(2),
    frame(126),
    dx(2),
    frame(127),
    dx(2),
    frame(128),
    dx(2),
    snd(SND_FOOTSTEP),
    frame(129),
    dx(2),
    frame(130),
    dx(2),
    frame(131),
    dx(2),
    frame(132),
    dx(2),
    jmp(Seq.RUN),
)

# Stop_run: desacelera y vuelve a stand
_SEQ_STOP_RUN: Sequence = (
    frame(50),
    dx(1),
    frame(51),
    dx(1),
    frame(52),
    dx(0),
    jmp(Seq.STAND),
)

# Turn: gira sin avanzar
_SEQ_TURN: Sequence = (
    setup(Action.TURN),
    frame(45),
    frame(46),
    frame(47),
    frame(48),
    frame(49),
    jmp(Seq.STAND),
)


# ===========================================================================
# Jump
# ===========================================================================

# Standing jump: salta vertical desde quieto
_SEQ_STANDING_JUMP: Sequence = (
    setup(Action.IN_MIDAIR),
    snd(SND_JUMP),
    frame(16),
    dy(-3),
    frame(17),
    dy(-5),
    frame(18),
    dy(-7),
    frame(19),
    dy(-7),  # peak
    frame(20),
    dy(-5),
    frame(21),
    dy(-3),
    frame(22),
    dy(0),
    frame(23),
    dy(2),
    frame(24),
    dy(4),
    frame(25),
    dy(6),
    jmp(Seq.FALL_AFTER_STANDING_JUMP),
)

# Run jump: salto con carrerilla — cubre 2-3 tiles horizontal
_SEQ_RUN_JUMP: Sequence = (
    setup(Action.IN_MIDAIR),
    snd(SND_JUMP),
    frame(34),
    dx(2),
    dy(-3),
    frame(35),
    dx(2),
    dy(-6),
    frame(36),
    dx(2),
    dy(-8),
    frame(37),
    dx(2),
    dy(-7),
    frame(38),
    dx(2),
    dy(-4),
    frame(39),
    dx(2),
    dy(0),  # peak
    frame(40),
    dx(2),
    dy(3),
    frame(41),
    dx(2),
    dy(6),
    frame(42),
    dx(2),
    dy(9),
    frame(43),
    dx(2),
    dy(12),  # FRAME_43 — trigger shadow step (L6)
    frame(44),
    dx(2),
    dy(15),
    # set fall state y entrega a SEQ_FALL
    set_fall(2, 15),
    setup(Action.IN_FREEFALL),
    jmp(Seq.FALL),
)


# ===========================================================================
# Fall
# ===========================================================================

# Fall: sigue cayendo según fall_y, gravity aplicado externo
_SEQ_FALL: Sequence = (
    setup(Action.IN_FREEFALL),
    frame(102),
    jmp(Seq.FALL),  # se repite hasta hit_ground
)

# Fall after standing jump: caída suave tras stand-jump
_SEQ_FALL_AFTER_STANDING_JUMP: Sequence = (
    setup(Action.IN_FREEFALL),
    frame(26),
    dy(6),
    frame(27),
    dy(8),
    set_fall(0, 8),
    jmp(Seq.FALL),
)


# ===========================================================================
# Soft land (sin daño)
# ===========================================================================

_SEQ_SOFT_LAND: Sequence = (
    snd(SND_LAND_SOFT),
    frame(106),
    frame(107),
    frame(108),
    jmp(Seq.STAND),
)


# ===========================================================================
# Hang / climb
# ===========================================================================

# Grab ledge midair: el grab automático tras check_grab exitoso
_SEQ_GRAB_LEDGE_MIDAIR: Sequence = (
    setup(Action.HANG_STRAIGHT),
    snd(SND_GRAB),
    frame(67),
    dy(-4),
    frame(68),
    dy(-2),
    frame(69),
    dy(0),
    set_fall(0, 0),
    frame(70),
    jmp(Seq.JUMP_UP_GRAB_STRAIGHT),
)

# Jump up & hang straight: el kid sostiene la cornisa
_SEQ_JUMP_UP_GRAB_STRAIGHT: Sequence = (
    setup(Action.HANG_STRAIGHT),
    frame(91),
    jmp(Seq.JUMP_UP_GRAB_STRAIGHT),  # idle hanging
)

# Jump up grab: salto vertical → agarrar cornisa arriba
_SEQ_JUMP_UP_GRAB: Sequence = (
    setup(Action.IN_MIDAIR),
    frame(67),
    dy(-8),
    frame(68),
    dy(-6),
    frame(69),
    dy(-4),
    frame(70),
    dy(-2),
    jmp(Seq.JUMP_UP_GRAB_STRAIGHT),
)

# Climb up: trepar de hang a stand sobre la cornisa
_SEQ_CLIMB_UP: Sequence = (
    setup(Action.HANG_CLIMB),
    snd(SND_CLIMB),
    frame(135),
    dx(0),
    dy(-3),
    frame(136),
    dx(1),
    dy(-5),
    frame(137),
    dx(1),
    dy(-7),
    frame(138),
    dx(2),
    dy(-9),
    frame(139),
    dx(2),
    dy(-11),
    frame(140),
    dx(2),
    dy(-13),
    frame(141),
    dx(2),
    dy(-15),
    frame(142),
    dx(2),
    dy(-17),
    frame(143),
    dx(2),
    dy(-19),
    frame(144),
    dx(2),
    dy(-21),
    frame(145),
    dx(2),
    dy(-23),
    frame(146),
    dx(2),
    dy(-25),
    frame(147),
    dx(2),
    dy(-27),
    frame(148),
    dx(2),
    dy(-29),
    frame(149),
    dx(2),
    dy(-31),
    jmp(Seq.STAND),
)

# Release ledge: soltar agarre → freefall
_SEQ_RELEASE_LEDGE_LAND: Sequence = (
    setup(Action.IN_FREEFALL),
    frame(102),
    set_fall(0, 5),
    jmp(Seq.FALL),
)


# ===========================================================================
# Crouch
# ===========================================================================

_SEQ_CROUCH: Sequence = (
    frame(110),
    frame(111),
    frame(112),
    jmp(Seq.STAND),  # nota: se queda en crouch idle, no en STAND
)

_SEQ_STAND_UP_FROM_CROUCH: Sequence = (
    frame(115),
    frame(116),
    frame(117),
    frame(118),
    frame(119),
    jmp(Seq.STAND),
)


# ===========================================================================
# Sword combat
# ===========================================================================

_SEQ_DRAW_SWORD: Sequence = (
    frame(207),
    frame(208),
    frame(209),
    frame(210),
    jmp(Seq.STAND),  # debería ir a engarde — placeholder
)

_SEQ_STRIKE: Sequence = (
    snd(SND_STRIKE),
    frame(165),  # ventana de impacto comienza
    frame(166),
    frame(167),  # ventana de impacto termina
    frame(168),
    frame(169),
    frame(170),
    jmp(Seq.STAND),
)


# ===========================================================================
# Muerte
# ===========================================================================

_SEQ_DYING: Sequence = (
    snd(SND_DEATH),
    frame(179),
    frame(180),
    frame(181),
    frame(182),
    frame(183),
    frame(184),
    frame(185),
    jmp(Seq.DYING),  # frame final permanente
)

_SEQ_STABBED_TO_DEATH: Sequence = (
    snd(SND_DEATH),
    frame(171),
    frame(172),
    frame(173),
    frame(174),
    frame(175),
    jmp(Seq.DYING),
)

_SEQ_SPIKED: Sequence = (
    snd(SND_SPIKE),
    frame(FrameID.SPIKED),
    jmp(Seq.SPIKED),  # frame permanente
)

_SEQ_CHOMPED: Sequence = (
    snd(SND_CHOMP),
    frame(FrameID.CHOMPED),
    jmp(Seq.CHOMPED),
)

_SEQ_CRUSHED: Sequence = (
    snd(SND_LOOSE_CRACK),
    frame(185),  # placeholder — el kid plano
    jmp(Seq.CRUSHED),
)

_SEQ_LOOSE_FLOOR_FELL_ON_KID: Sequence = (
    snd(SND_LOOSE_CRACK),
    frame(185),
    jmp(Seq.CRUSHED),
)


# ===========================================================================
# Drink potion
# ===========================================================================

_SEQ_DRINK: Sequence = (
    snd(SND_DRINK),
    frame(191),
    frame(192),
    frame(193),
    frame(194),
    frame(195),
    frame(196),
    frame(197),
    frame(198),
    frame(199),
    frame(200),
    frame(201),
    frame(202),
    frame(203),
    frame(204),
    frame(205),
    jmp(Seq.STAND),
)


# ---------------------------------------------------------------------------
# Tabla maestra
# ---------------------------------------------------------------------------

TABLE: dict[int, Sequence] = {
    int(Seq.STAND): _SEQ_STAND,
    int(Seq.START_RUN): _SEQ_START_RUN,
    int(Seq.RUN): _SEQ_RUN,
    int(Seq.STOP_RUN): _SEQ_STOP_RUN,
    int(Seq.TURN): _SEQ_TURN,
    int(Seq.STANDING_JUMP): _SEQ_STANDING_JUMP,
    int(Seq.RUN_JUMP): _SEQ_RUN_JUMP,
    int(Seq.FALL): _SEQ_FALL,
    int(Seq.FALL_AFTER_STANDING_JUMP): _SEQ_FALL_AFTER_STANDING_JUMP,
    int(Seq.SOFT_LAND): _SEQ_SOFT_LAND,
    int(Seq.GRAB_LEDGE_MIDAIR): _SEQ_GRAB_LEDGE_MIDAIR,
    int(Seq.JUMP_UP_GRAB_STRAIGHT): _SEQ_JUMP_UP_GRAB_STRAIGHT,
    int(Seq.JUMP_UP_GRAB): _SEQ_JUMP_UP_GRAB,
    int(Seq.CLIMB_UP): _SEQ_CLIMB_UP,
    int(Seq.RELEASE_LEDGE_LAND): _SEQ_RELEASE_LEDGE_LAND,
    int(Seq.CROUCH): _SEQ_CROUCH,
    int(Seq.STAND_UP_FROM_CROUCH): _SEQ_STAND_UP_FROM_CROUCH,
    int(Seq.DRAW_SWORD): _SEQ_DRAW_SWORD,
    int(Seq.STRIKE): _SEQ_STRIKE,
    int(Seq.DYING): _SEQ_DYING,
    int(Seq.STABBED_TO_DEATH): _SEQ_STABBED_TO_DEATH,
    int(Seq.SPIKED): _SEQ_SPIKED,
    int(Seq.CHOMPED): _SEQ_CHOMPED,
    int(Seq.CRUSHED): _SEQ_CRUSHED,
    int(Seq.LOOSE_FLOOR_FELL_ON_KID): _SEQ_LOOSE_FLOOR_FELL_ON_KID,
    int(Seq.DRINK): _SEQ_DRINK,
}
"""25 secuencias canónicas. Faltan ~70 — añadir progresivamente."""


def get(seq_id: int | Seq) -> Sequence:
    """Devuelve la secuencia por ID. Lanza si no existe."""
    key = int(seq_id)
    if key not in TABLE:
        raise KeyError(f"seq {seq_id} no implementada (FASE 3.3 pendiente)")
    return TABLE[key]


# Hit / block windows canónicas (frames donde el strike/parry resuelve)

STRIKE_WINDOW: frozenset[int] = frozenset({165, 166, 167})
"""Frames del kid en los que un strike conecta."""

BLOCK_WINDOW: frozenset[int] = frozenset({161, 162, 163, 164})
"""Frames del kid en los que un block neutraliza un strike entrante."""
