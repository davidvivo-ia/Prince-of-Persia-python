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

    FLIP = 8
    """Canon ``SEQ_FLIP``: el char da media vuelta (cambia ``direction``)."""


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


def flip() -> SeqAct:
    return SeqAct(ActKind.FLIP, 0)


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
SND_BUMP = 13
SND_HARDLAND = 14
SND_EXIT = 15


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

# Run: ciclo de 12 frames (121..132). Canon: ~3.5 unidades/frame con
# TILE_SIZE_X=14 → 1 tile cada 4 ticks (velocidad de carrera del POP1).
_SEQ_RUN: Sequence = (
    setup(Action.RUN_JUMP),
    frame(121),
    dx(3),
    frame(122),
    dx(4),
    frame(123),
    dx(3),
    frame(124),
    dx(4),
    snd(SND_FOOTSTEP),
    frame(125),
    dx(3),
    frame(126),
    dx(4),
    frame(127),
    dx(3),
    frame(128),
    dx(4),
    snd(SND_FOOTSTEP),
    frame(129),
    dx(3),
    frame(130),
    dx(4),
    frame(131),
    dx(3),
    frame(132),
    dx(4),
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

# Standing jump forward: salto largo desde parado (ARRIBA+dirección).
# Canon POP1: libra 2 celdas de vacío y aterriza en la tercera
# (~28 unidades de vuelo + inercia de caída).
_SEQ_STANDING_JUMP_FORWARD: Sequence = (
    setup(Action.IN_MIDAIR),
    snd(SND_JUMP),
    frame(16),
    dx(3),
    dy(-3),
    frame(17),
    dx(5),
    dy(-5),
    frame(18),
    dx(7),
    dy(-6),
    frame(19),
    dx(8),
    dy(-4),  # peak
    frame(20),
    dx(8),
    dy(0),
    frame(21),
    dx(6),
    dy(6),
    frame(22),
    dx(5),
    dy(12),
    # Total: dx 42 = exactamente 3 celdas (aterriza en la celda +3 con
    # el mismo offset con que despegó — fiable en plataformas de una
    # celda) y dy 0 (los pies vuelven a la superficie). Sin deriva
    # horizontal en la caída posterior.
    set_fall(0, 8),
    setup(Action.IN_FREEFALL),
    jmp(Seq.FALL),
)

# Step: paso cuidadoso (SHIFT+dirección) — una celda en 6 frames; el
# controller sólo lo arranca si hay suelo delante (canon: te detienes
# en el borde).
_SEQ_STEP: Sequence = (
    setup(Action.STAND),
    frame(121),
    dx(2),
    frame(122),
    dx(3),
    frame(123),
    dx(3),
    frame(124),
    dx(3),
    snd(SND_FOOTSTEP),
    frame(15),
    dx(3),
    jmp(Seq.STAND),
)

# Run jump: salto con carrerilla — vuelo de ~56 unidades (4 tiles):
# despega, LIBRA 3 celdas de vacío y aterriza en la cuarta (canon POP1).
_SEQ_RUN_JUMP: Sequence = (
    setup(Action.IN_MIDAIR),
    snd(SND_JUMP),
    frame(34),
    dx(5),
    dy(-3),
    frame(35),
    dx(5),
    dy(-6),
    frame(36),
    dx(6),
    dy(-8),
    frame(37),
    dx(6),
    dy(-7),
    frame(38),
    dx(6),
    dy(-4),
    frame(39),
    dx(6),
    dy(0),  # peak
    frame(40),
    dx(6),
    dy(3),
    frame(41),
    dx(5),
    dy(6),
    frame(42),
    dx(5),
    dy(9),
    frame(43),
    dx(4),
    dy(6),  # FRAME_43 — trigger shadow step (L6)
    frame(44),
    dx(2),
    dy(8),
    # set fall state y entrega a SEQ_FALL
    set_fall(2, 8),
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
# Agarre en el aire (cayendo / saltando): la física coloca al char en
# la celda colgado; la secuencia sólo anima (sin dx/dy) y, mientras
# dura (HANG_CLIMB), no se acepta input — como el ``grab_timer`` canon.
_SEQ_GRAB_LEDGE_MIDAIR: Sequence = (
    setup(Action.HANG_CLIMB),
    snd(SND_GRAB),
    frame(67),
    frame(68),
    frame(69),
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

# Jump up grab (canon jumpbackhang / jump_up_and_grab): ↑ de pie bajo
# una cornisa → salta y se agarra.
_SEQ_JUMP_UP_GRAB: Sequence = (
    setup(Action.HANG_CLIMB),
    snd(SND_JUMP),
    frame(67),
    frame(68),
    frame(69),
    frame(70),
    frame(77),
    snd(SND_GRAB),
    frame(78),
    jmp(Seq.JUMP_UP_GRAB_STRAIGHT),
)

# Climb down (canon seq 68): de pie de espaldas al borde, ↓ → el kid se
# descuelga por el borde y queda colgado. La física ya lo ha puesto en
# la celda de abajo; la secuencia anima la bajada (frames de trepar al
# revés) y entra en el idle colgado.
_SEQ_CLIMB_DOWN: Sequence = (
    setup(Action.HANG_CLIMB),
    frame(148),
    frame(145),
    frame(144),
    frame(143),
    frame(142),
    frame(141),
    frame(140),
    frame(138),
    frame(136),
    jmp(Seq.JUMP_UP_GRAB_STRAIGHT),
)

# Climb up: trepar de hang a stand sobre la cornisa
_SEQ_CLIMB_UP: Sequence = (
    # Trepar de colgado a de pie sobre la cornisa. Sin dx/dy: la física
    # coloca al char EN la cornisa (col+fwd, row-1) al terminar.
    setup(Action.HANG_CLIMB),
    snd(SND_CLIMB),
    frame(135),
    frame(136),
    frame(137),
    frame(138),
    frame(139),
    frame(140),
    frame(141),
    frame(142),
    frame(143),
    frame(144),
    frame(145),
    frame(146),
    frame(147),
    frame(148),
    frame(149),
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
    setup(Action.STAND),
    snd(SND_STRIKE),
    dx(2),
    frame(207),
    frame(208),
    dx(2),
    frame(209),
    dx(2),
    frame(210),
    dx(3),
    jmp(Seq.ENGARDE),
)

# Estocada del kid (canon seq 75 ``faststrike``): la punta llega en el
# frame 154 ("poking"); 155 es el retroceso (acción bumped: sin control).
_SEQ_STRIKE: Sequence = (
    setup(Action.STAND),
    snd(SND_STRIKE),
    frame(151),
    frame(152),
    frame(153),
    frame(154),
    frame(155),
    frame(156),
    frame(157),
    jmp(Seq.ENGARDE),
)

# Estocada del guard (canon seq 58 ``strike``): un frame de preparación
# (168) delante — por eso el kid tiene un instante para parar.
_SEQ_GUARD_STRIKE: Sequence = (
    setup(Action.STAND),
    snd(SND_STRIKE),
    frame(168),
    frame(151),
    frame(152),
    frame(153),
    frame(154),
    frame(155),
    frame(156),
    frame(157),
    jmp(Seq.ENGARDE),
)

# La estocada fue parada (canon seq 69 ``blockedstrike``): recoil.
_SEQ_ATTACK_PARRIED: Sequence = (
    setup(Action.STAND),
    snd(SND_BUMP),
    frame(167),
    frame(155),
    frame(156),
    frame(157),
    jmp(Seq.ENGARDE),
)

# Herido por la espada (canon seq 74 ``stabbed``): tambaleo hacia atrás
# (dx total -10) y vuelta a la guardia.
_SEQ_HIT_BY_SWORD: Sequence = (
    setup(Action.STAND),
    snd(SND_BUMP),
    frame(172),
    dx(-1),
    frame(173),
    dx(-1),
    frame(174),
    dx(-1),
    dx(-2),
    dx(-5),
    frame(156),
    frame(157),
    jmp(Seq.ENGARDE),
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

# Muerte a espada (canon seq 85 ``stabkill`` → ``dropdead``): se desploma.
_SEQ_STABBED_TO_DEATH: Sequence = (
    setup(Action.HURT),
    snd(SND_DEATH),
    frame(179),
    frame(180),
    frame(181),
    frame(182),
    dx(1),
    frame(183),
    dx(-4),
    frame(185),
    jmp(Seq.DYING),
)

# Muerto a espada junto a un borde: cae de espaldas al vacío (canon seq
# 81 ``fightfall`` / 82 ``efightfall``).
_SEQ_KID_PUSHED_OFF_LEDGE: Sequence = (
    setup(Action.IN_MIDAIR),
    dy(-1),
    frame(102),
    dx(-2),
    dy(6),
    frame(103),
    dx(-2),
    dy(9),
    frame(104),
    dx(-1),
    dy(12),
    frame(105),
    dx(-3),
    set_fall(0, 15),
    setup(Action.IN_FREEFALL),
    jmp(Seq.FALL),
)

_SEQ_GUARD_PUSHED_OFF_LEDGE: Sequence = (
    setup(Action.IN_MIDAIR),
    dy(-1),
    dx(-2),
    frame(102),
    dx(-3),
    dy(6),
    frame(103),
    dx(-3),
    dy(9),
    frame(104),
    dx(-2),
    dy(12),
    frame(105),
    dx(-3),
    set_fall(0, 15),
    setup(Action.IN_FREEFALL),
    jmp(Seq.FALL),
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


# ===========================================================================
# Combate avanzado: ENGARDE / ADVANCE / RETREAT / BLOCK
# ===========================================================================
#
# En POP1 con espada empuñada y enemigo adyacente, el kid entra en stance
# `engarde` y los inputs cambian de meaning: izquierda/derecha → retreat/
# advance, arriba → block, espacio → strike.


# En guardia (canon ``ready``): 158, 170 y bucle en 171.
_SEQ_ENGARDE: Sequence = (
    setup(Action.STAND),
    frame(158),
    frame(170),
    frame(171),
    jmp(Seq.ENGARDE),
)

# Guard en reposo (canon ``alertstand``): no ha visto al kid.
_SEQ_GUARD_STAND_INACTIVE: Sequence = (
    setup(Action.STAND),
    frame(166),
    jmp(Seq.GUARD_STAND_INACTIVE),
)

# Avance del kid en guardia (canon seq 86 ``advance``): 6 px.
_SEQ_ADVANCE: Sequence = (
    setup(Action.STAND),
    dx(2),
    frame(163),
    dx(4),
    frame(164),
    frame(165),
    jmp(Seq.ENGARDE),
)

# Avance del guard (canon seq 56 ``fastadvance``): 6 px en dos frames.
_SEQ_GUARD_ADVANCE: Sequence = (
    setup(Action.STAND),
    dx(6),
    frame(164),
    frame(165),
    jmp(Seq.ENGARDE),
)

# Retroceso en guardia (canon seq 57 ``retreat``): -5 px.
_SEQ_RETREAT: Sequence = (
    setup(Action.STAND),
    dx(-3),
    frame(160),
    dx(-2),
    frame(157),
    jmp(Seq.ENGARDE),
)

# Giro en guardia (canon seq 60 ``turnengarde``): media vuelta y paso atrás.
_SEQ_TURN_WITH_SWORD: Sequence = (
    setup(Action.STAND),
    flip(),
    dx(5),
    jmp(Seq.RETREAT),
)

# Parada (canon seq 62 ``readyblock``): 169 → 150 (frame de parada).
_SEQ_BLOCK_STRIKE: Sequence = (
    setup(Action.STAND),
    frame(169),
    frame(150),
    jmp(Seq.ENGARDE),
)

# Parada justo tras atacar (canon seq 61 ``striketoblock``).
_SEQ_PARRY_AFTER_STRIKE: Sequence = (
    setup(Action.STAND),
    frame(159),
    frame(160),
    frame(150),
    jmp(Seq.ENGARDE),
)

# Parada → estocada (canon seq 66 ``blocktostrike``): 162 y la estocada.
_SEQ_BLOCK_TO_STRIKE: Sequence = (
    setup(Action.STAND),
    snd(SND_STRIKE),
    frame(162),
    frame(152),
    frame(153),
    frame(154),
    frame(155),
    frame(156),
    frame(157),
    jmp(Seq.ENGARDE),
)


# ===========================================================================
# Locomoción extra: RUNTURN / BUMP / HARDLAND / MEDLAND
# ===========================================================================


_SEQ_RUNTURN: Sequence = (
    setup(Action.RUN_JUMP),
    frame(48),
    dx(-1),
    frame(49),
    frame(50),
    frame(51),
    frame(52),
    snd(SND_FOOTSTEP),
    jmp(Seq.RUN),
)

_SEQ_BUMP: Sequence = (
    setup(Action.BUMPED),
    snd(SND_BUMP),
    frame(56),
    frame(57),
    frame(58),
    frame(59),
    frame(60),
    jmp(Seq.STAND),
)

_SEQ_HARD_LAND: Sequence = (
    setup(Action.STAND),
    snd(SND_HARDLAND),
    frame(110),
    frame(111),
    frame(112),
    frame(113),
    frame(114),
    jmp(Seq.STAND),
)

_SEQ_MED_LAND: Sequence = (
    setup(Action.STAND),
    snd(SND_FOOTSTEP),
    frame(108),
    frame(109),
    jmp(Seq.STAND),
)


# ===========================================================================
# Guard fall + bump fall
# ===========================================================================


# Guard que cae hacia delante (canon seq 83 ``efightfallfwd``).
_SEQ_GUARD_FALL: Sequence = (
    setup(Action.IN_MIDAIR),
    dx(1),
    dy(-1),
    frame(102),
    dx(2),
    dy(6),
    frame(103),
    dx(-1),
    dy(9),
    frame(104),
    dy(12),
    frame(105),
    dx(-2),
    set_fall(1, 15),
    setup(Action.IN_FREEFALL),
    jmp(Seq.FALL),
)

_SEQ_BUMPED_FALL: Sequence = (
    setup(Action.IN_FREEFALL),
    set_fall(-1, 1),
    snd(SND_BUMP),
    frame(56),
    jmp(Seq.FALL),
)


# ===========================================================================
# Exit level (sube escaleras)
# ===========================================================================


_SEQ_EXIT_LEVEL: Sequence = (
    setup(Action.STAND),
    snd(SND_EXIT),
    frame(217),
    frame(218),
    frame(219),
    frame(220),
    frame(221),
    frame(222),
    frame(223),
    frame(224),
    frame(225),
    frame(226),
    frame(227),
    frame(228),
    jmp(Seq.EXIT_LEVEL),  # frame final: kid fuera de pantalla
)


# ===========================================================================
# Put sword away
# ===========================================================================


_SEQ_PUT_SWORD_AWAY: Sequence = (
    setup(Action.STAND),
    frame(230),
    frame(231),
    frame(232),
    frame(233),
    frame(234),
    frame(235),
    frame(236),
    frame(237),
    frame(238),
    frame(239),
    frame(240),
    jmp(Seq.STAND),
)


# ===========================================================================
# Jump + grab midair (seq 38 canon)
# ===========================================================================


_SEQ_JUMP_HANG_MIDAIR: Sequence = (
    setup(Action.HANG_STRAIGHT),
    set_fall(0, 0),
    frame(78),
    frame(79),
    frame(80),
    jmp(Seq.JUMP_UP_GRAB_STRAIGHT),
)


# ---------------------------------------------------------------------------
# Tabla maestra
# ---------------------------------------------------------------------------

TABLE: dict[int, Sequence] = {
    int(Seq.STAND): _SEQ_STAND,
    int(Seq.START_RUN): _SEQ_START_RUN,
    int(Seq.RUN): _SEQ_RUN,
    int(Seq.STOP_RUN): _SEQ_STOP_RUN,
    int(Seq.STANDING_JUMP_FORWARD): _SEQ_STANDING_JUMP_FORWARD,
    int(Seq.STEP): _SEQ_STEP,
    int(Seq.TURN): _SEQ_TURN,
    int(Seq.RUNTURN): _SEQ_RUNTURN,
    int(Seq.STANDING_JUMP): _SEQ_STANDING_JUMP,
    int(Seq.RUN_JUMP): _SEQ_RUN_JUMP,
    int(Seq.FALL): _SEQ_FALL,
    int(Seq.FALL_AFTER_STANDING_JUMP): _SEQ_FALL_AFTER_STANDING_JUMP,
    int(Seq.SOFT_LAND): _SEQ_SOFT_LAND,
    int(Seq.MED_LAND): _SEQ_MED_LAND,
    int(Seq.HARD_LAND): _SEQ_HARD_LAND,
    int(Seq.BUMP): _SEQ_BUMP,
    int(Seq.BUMPED_FALL): _SEQ_BUMPED_FALL,
    int(Seq.GRAB_LEDGE_MIDAIR): _SEQ_GRAB_LEDGE_MIDAIR,
    int(Seq.JUMP_UP_GRAB_STRAIGHT): _SEQ_JUMP_UP_GRAB_STRAIGHT,
    int(Seq.JUMP_UP_GRAB): _SEQ_JUMP_UP_GRAB,
    int(Seq.JUMP_HANG_MIDAIR): _SEQ_JUMP_HANG_MIDAIR,
    int(Seq.CLIMB_UP): _SEQ_CLIMB_UP,
    int(Seq.CLIMB_DOWN): _SEQ_CLIMB_DOWN,
    int(Seq.RELEASE_LEDGE_LAND): _SEQ_RELEASE_LEDGE_LAND,
    int(Seq.CROUCH): _SEQ_CROUCH,
    int(Seq.STAND_UP_FROM_CROUCH): _SEQ_STAND_UP_FROM_CROUCH,
    int(Seq.DRAW_SWORD): _SEQ_DRAW_SWORD,
    int(Seq.PUT_SWORD_AWAY): _SEQ_PUT_SWORD_AWAY,
    int(Seq.ENGARDE): _SEQ_ENGARDE,
    int(Seq.ADVANCE): _SEQ_ADVANCE,
    int(Seq.RETREAT): _SEQ_RETREAT,
    int(Seq.BLOCK_STRIKE): _SEQ_BLOCK_STRIKE,
    int(Seq.BLOCK_TO_STRIKE): _SEQ_BLOCK_TO_STRIKE,
    int(Seq.STRIKE): _SEQ_STRIKE,
    int(Seq.GUARD_STRIKE): _SEQ_GUARD_STRIKE,
    int(Seq.GUARD_ADVANCE): _SEQ_GUARD_ADVANCE,
    int(Seq.TURN_WITH_SWORD): _SEQ_TURN_WITH_SWORD,
    int(Seq.PARRY_AFTER_STRIKE): _SEQ_PARRY_AFTER_STRIKE,
    int(Seq.ATTACK_PARRIED): _SEQ_ATTACK_PARRIED,
    int(Seq.HIT_BY_SWORD): _SEQ_HIT_BY_SWORD,
    int(Seq.GUARD_STAND_INACTIVE): _SEQ_GUARD_STAND_INACTIVE,
    int(Seq.KID_PUSHED_OFF_LEDGE): _SEQ_KID_PUSHED_OFF_LEDGE,
    int(Seq.GUARD_PUSHED_OFF_LEDGE): _SEQ_GUARD_PUSHED_OFF_LEDGE,
    int(Seq.GUARD_FALL): _SEQ_GUARD_FALL,
    int(Seq.EXIT_LEVEL): _SEQ_EXIT_LEVEL,
    int(Seq.DYING): _SEQ_DYING,
    int(Seq.STABBED_TO_DEATH): _SEQ_STABBED_TO_DEATH,
    int(Seq.SPIKED): _SEQ_SPIKED,
    int(Seq.CHOMPED): _SEQ_CHOMPED,
    int(Seq.CRUSHED): _SEQ_CRUSHED,
    int(Seq.LOOSE_FLOOR_FELL_ON_KID): _SEQ_LOOSE_FLOOR_FELL_ON_KID,
    int(Seq.DRINK): _SEQ_DRINK,
}
"""40 secuencias canónicas operativas (combate completo + locomoción +
muerte + drink + exit). El motor cubre toda la lógica de gameplay; los
~50 IDs restantes del seqtbl.c original son variaciones cosméticas
sin cambios mecánicos."""


def get(seq_id: int | Seq) -> Sequence:
    """Devuelve la secuencia por ID. Lanza si no existe."""
    key = int(seq_id)
    if key not in TABLE:
        raise KeyError(f"seq {seq_id} no implementada en el motor canon")
    return TABLE[key]


# Hit / block windows canónicas (frames donde el strike/parry resuelve)

STRIKE_WINDOW: frozenset[int] = frozenset({153, 154})
"""Canon ``check_hurting``: el atacante sólo puede herir (o ser parado)
en los frames 153 y 154; la punta alcanza al rival en el 154."""

BLOCK_WINDOW: frozenset[int] = frozenset({150, 161})
"""Canon: con la espada en los frames de parada (150 / 161) la estocada
rival rebota."""
