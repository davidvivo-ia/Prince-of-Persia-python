"""Sistema de keyframes para articulaciones del cuerpo.

Cada acción puede definir una serie de ``Keyframe`` ordenados por su
``t`` (fracción de la duración de la acción, en ``[0.0, 1.0]``). La
función :func:`interpolate` busca el segmento correspondiente al
``phase`` actual y devuelve una ``JointPose`` linealmente interpolada.

El renderer convierte los offsets de articulación en píxeles. Las
unidades son **fracciones de la altura del cuerpo** para que el sistema
sea independiente de la escala visual: ``arm_x = 0.4`` significa que la
mano está a 40 % de la altura del cuerpo hacia adelante.

Esto sustituye los ``math.sin(phase*2*pi)`` cableados en el renderer.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from pop2026.domain.actions import Action


@dataclass(frozen=True, slots=True)
class JointPose:
    """Posiciones relativas de las articulaciones principales.

    Origen ``(0, 0)`` = centro del torso. Eje X positivo = adelante.
    Eje Y positivo = abajo. Unidades en *fracciones del cuerpo*
    (``body_h`` aprox 44 px en el renderer actual).
    """

    head_dy: float = -0.50
    """Desplazamiento vertical de la cabeza respecto al torso."""

    torso_dy: float = 0.0
    """Inclinación / desplazamiento vertical del torso (signo positivo
    = hacia abajo, e.g., agacharse)."""

    arm_l_dx: float = -0.12
    arm_l_dy: float = 0.10
    arm_r_dx: float = 0.12
    arm_r_dy: float = 0.10
    """Posición de las manos respecto al torso."""

    leg_l_dx: float = -0.10
    leg_l_dy: float = 0.55
    leg_r_dx: float = 0.10
    leg_r_dy: float = 0.55
    """Posición de los pies respecto al torso."""

    def lerp(self, other: JointPose, t: float) -> JointPose:
        """Interpola linealmente con otra pose (``t`` en ``[0, 1]``)."""
        return JointPose(
            head_dy=_lerp(self.head_dy, other.head_dy, t),
            torso_dy=_lerp(self.torso_dy, other.torso_dy, t),
            arm_l_dx=_lerp(self.arm_l_dx, other.arm_l_dx, t),
            arm_l_dy=_lerp(self.arm_l_dy, other.arm_l_dy, t),
            arm_r_dx=_lerp(self.arm_r_dx, other.arm_r_dx, t),
            arm_r_dy=_lerp(self.arm_r_dy, other.arm_r_dy, t),
            leg_l_dx=_lerp(self.leg_l_dx, other.leg_l_dx, t),
            leg_l_dy=_lerp(self.leg_l_dy, other.leg_l_dy, t),
            leg_r_dx=_lerp(self.leg_r_dx, other.leg_r_dx, t),
            leg_r_dy=_lerp(self.leg_r_dy, other.leg_r_dy, t),
        )


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


@dataclass(frozen=True, slots=True)
class Keyframe:
    """Pose en un punto concreto del ciclo de animación."""

    t: float
    """Posición temporal normalizada en ``[0.0, 1.0]``."""

    pose: JointPose


REST = JointPose()
"""Pose neutra de referencia (de pie, brazos a los lados)."""


# ---------------------------------------------------------------------------
# Sets de keyframes por acción. Diseño propio.
# ---------------------------------------------------------------------------

WALK_FRAMES: tuple[Keyframe, ...] = (
    Keyframe(0.0, replace(REST, leg_l_dx=-0.18, leg_r_dx=0.18, arm_l_dx=0.10, arm_r_dx=-0.10)),
    Keyframe(0.25, replace(REST, head_dy=-0.52, leg_l_dx=-0.05, leg_r_dx=0.20)),
    Keyframe(0.5, replace(REST, leg_l_dx=0.18, leg_r_dx=-0.18, arm_l_dx=-0.10, arm_r_dx=0.10)),
    Keyframe(0.75, replace(REST, head_dy=-0.52, leg_l_dx=0.20, leg_r_dx=-0.05)),
    Keyframe(1.0, replace(REST, leg_l_dx=-0.18, leg_r_dx=0.18, arm_l_dx=0.10, arm_r_dx=-0.10)),
)

STRIKE_FRAMES: tuple[Keyframe, ...] = (
    # Anticipación: brazo atrás
    Keyframe(0.0, replace(REST, arm_r_dx=-0.20, arm_r_dy=0.05, torso_dy=-0.02)),
    # Aceleración
    Keyframe(0.4, replace(REST, arm_r_dx=0.10, arm_r_dy=0.05)),
    # Golpe extendido (dentro de la hit-window)
    Keyframe(0.6, replace(REST, arm_r_dx=0.38, arm_r_dy=0.05)),
    # Recuperación
    Keyframe(1.0, replace(REST, arm_r_dx=0.18, arm_r_dy=0.10)),
)

LUNGE_FRAMES: tuple[Keyframe, ...] = (
    Keyframe(0.0, replace(REST, arm_r_dx=-0.25, arm_r_dy=0.05, leg_r_dx=0.15)),
    Keyframe(0.5, replace(REST, arm_r_dx=0.20, arm_r_dy=0.05, leg_r_dx=0.20)),
    Keyframe(0.7, replace(REST, arm_r_dx=0.55, arm_r_dy=0.08, leg_r_dx=0.30, torso_dy=0.05)),
    Keyframe(1.0, replace(REST, arm_r_dx=0.30, arm_r_dy=0.10, leg_r_dx=0.18, torso_dy=0.02)),
)

PARRY_FRAMES: tuple[Keyframe, ...] = (
    Keyframe(0.0, replace(REST, arm_r_dx=0.0, arm_r_dy=-0.10, arm_l_dx=0.0, arm_l_dy=-0.10)),
    Keyframe(0.5, replace(REST, arm_r_dx=0.10, arm_r_dy=-0.15, arm_l_dx=0.10, arm_l_dy=-0.15)),
    Keyframe(1.0, replace(REST, arm_r_dx=0.05, arm_r_dy=-0.10, arm_l_dx=0.05, arm_l_dy=-0.10)),
)


FRAMES_BY_ACTION: dict[Action, tuple[Keyframe, ...]] = {
    Action.WALK: WALK_FRAMES,
    Action.RUN: WALK_FRAMES,  # comparte ciclo, distintas duraciones
    Action.STRIKE: STRIKE_FRAMES,
    Action.LUNGE: LUNGE_FRAMES,
    Action.PARRY: PARRY_FRAMES,
}


def interpolate(action: Action, phase: float) -> JointPose:
    """Devuelve la pose interpolada para la acción y la fase indicadas.

    Args:
        action: Acción en curso.
        phase: Fracción ``[0, 1]`` del ciclo de la acción.

    Returns:
        ``JointPose`` interpolada. Para acciones sin keyframes definidos,
        devuelve la pose neutra ``REST``.
    """
    frames = FRAMES_BY_ACTION.get(action)
    if not frames:
        return REST
    # Clamp
    p = max(0.0, min(1.0, phase))
    # Busca el segmento
    for i in range(len(frames) - 1):
        a, b = frames[i], frames[i + 1]
        if a.t <= p <= b.t:
            span = b.t - a.t
            if span <= 0.0:
                return a.pose
            local_t = (p - a.t) / span
            return a.pose.lerp(b.pose, local_t)
    # Fuera de rango: última pose
    return frames[-1].pose
