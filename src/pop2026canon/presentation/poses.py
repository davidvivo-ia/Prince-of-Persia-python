"""Esqueleto 2D de los personajes y su pose para cada frame canon.

Puro (sin pygame) y testeado. Unidades del esqueleto: una fila de
tiles mide 84 unidades (el kid de pie, ~55). Ejes en vista lateral
mirando a la DERECHA: ``x`` hacia delante, ``y`` hacia abajo; el origen
es el punto de los pies (el ``_char_px`` del renderer). El espejo para
mirar a la izquierda lo hace el dibujo.

Ángulos de los segmentos en grados absolutos: 0 = hacia abajo,
90 = hacia delante, 180 = hacia arriba, -90 = hacia atrás.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

ROW_UNITS = 84.0
"""Unidades del esqueleto en una fila de tiles."""

HANG_Y = -ROW_UNITS + 1.5
"""Altura de las manos al colgar de la cornisa (relativa a los pies)."""

HANG_X = 3.0
"""Las manos agarran el borde un poco por delante del cuerpo."""

THIGH = 13.0
SHIN = 13.0
FOOT = 5.5
TORSO = 14.0
NECK = 2.0
HEAD_R = 5.0
UARM = 10.0
FARM = 9.5
SOLE = 1.4
"""Grosor del pie bajo el tobillo."""

Vec = tuple[float, float]


@dataclass(frozen=True, slots=True)
class Pose:
    lean: float = 2.0
    """Torso: grados hacia delante desde la vertical."""
    head: float = 0.0
    """Cabeza: inclinación extra (positivo = hacia delante/abajo)."""
    thigh_n: float = 5.0
    shin_n: float = 0.0
    thigh_f: float = -5.0
    shin_f: float = -3.0
    foot_n: float | None = None
    """Pie: ``None`` = apoyado (perpendicular a la espinilla, casi plano)."""
    foot_f: float | None = None
    uarm_n: float = 6.0
    farm_n: float = 12.0
    uarm_f: float = -6.0
    farm_f: float = 2.0
    blade: float | None = None
    """Ángulo de la hoja (en la mano cercana) o ``None`` sin espada."""
    rot: float = 0.0
    """Rotación de todo el cuerpo alrededor de la cadera (caer tendido)."""
    lift: float = 0.0
    """Elevación sobre el suelo (unidades) tras apoyar el pie más bajo."""
    dx: float = 0.0
    """Desplazamiento horizontal (unidades, hacia delante)."""
    hands: Vec | None = None
    """Objetivo de las manos (IK) en coordenadas finales, p. ej. la cornisa."""
    hang: bool = False
    """Colgado: se ancla por las manos en ``(HANG_X, HANG_Y)``."""
    sx: float = 1.0
    """Escala horizontal del sprite (giro: negativo = espejo)."""
    item: str = ""
    """Objeto en la mano: ``flask``."""
    alpha: float = 1.0


@dataclass(frozen=True, slots=True)
class Joints:
    hip: Vec
    shoulder: Vec
    neck: Vec
    head: Vec
    knee_n: Vec
    ankle_n: Vec
    toe_n: Vec
    knee_f: Vec
    ankle_f: Vec
    toe_f: Vec
    elbow_n: Vec
    hand_n: Vec
    elbow_f: Vec
    hand_f: Vec
    lean: float
    """Inclinación efectiva del torso (incluye ``rot``)."""
    head_angle: float
    blade: float | None

    def points(self) -> tuple[Vec, ...]:
        return (
            self.hip,
            self.shoulder,
            self.neck,
            self.head,
            self.knee_n,
            self.ankle_n,
            self.toe_n,
            self.knee_f,
            self.ankle_f,
            self.toe_f,
            self.elbow_n,
            self.hand_n,
            self.elbow_f,
            self.hand_f,
        )


def _dir(angle: float) -> Vec:
    a = math.radians(angle)
    return math.sin(a), math.cos(a)


def _add(p: Vec, d: Vec, k: float) -> Vec:
    return p[0] + d[0] * k, p[1] + d[1] * k


def _rot(p: Vec, c: Vec, deg: float) -> Vec:
    """Rota ``p`` alrededor de ``c``: positivo = hacia delante (horario en
    pantalla mirando a la derecha: la cabeza va hacia +x)."""
    a = math.radians(deg)
    x, y = p[0] - c[0], p[1] - c[1]
    ca, sa = math.cos(a), math.sin(a)
    return c[0] + x * ca - y * sa, c[1] + x * sa + y * ca


def _ik(
    shoulder: Vec, target: Vec, a: float, b: float, *, elbow_up: bool = True
) -> tuple[Vec, Vec]:
    """Brazo de dos huesos hacia ``target``: (codo, mano)."""
    dx, dy = target[0] - shoulder[0], target[1] - shoulder[1]
    d = math.hypot(dx, dy)
    if d < 1e-6:
        return _add(shoulder, (1.0, 0.0), a), shoulder
    ux, uy = dx / d, dy / d
    if d >= a + b - 1e-6:
        elbow = _add(shoulder, (ux, uy), a)
        return elbow, _add(elbow, (ux, uy), b)
    # Ley de cosenos: ángulo en el hombro
    cos_s = max(-1.0, min(1.0, (a * a + d * d - b * b) / (2 * a * d)))
    s = math.acos(cos_s)
    sign = -1.0 if elbow_up else 1.0
    ca, sa = math.cos(s * sign), math.sin(s * sign)
    ex = ux * ca - uy * sa
    ey = ux * sa + uy * ca
    elbow = _add(shoulder, (ex, ey), a)
    return elbow, target


def _foot(shin: float, foot: float | None) -> float:
    if foot is not None:
        return foot
    # Apoyado: el pie apunta hacia delante y casi plano
    return max(60.0, min(110.0, shin + 90.0))


def solve(pose: Pose) -> Joints:
    """Posiciones de las articulaciones en coordenadas de pies."""
    hip = (0.0, 0.0)
    lean = math.radians(pose.lean)
    up = (math.sin(lean), -math.cos(lean))  # torso hacia arriba inclinado
    shoulder = _add(hip, up, TORSO)
    neck = _add(hip, up, TORSO + NECK)
    ha = pose.lean + pose.head
    head = _add(neck, (math.sin(math.radians(ha)), -math.cos(math.radians(ha))), HEAD_R + 0.6)

    def leg(thigh: float, shin: float, foot: float | None) -> tuple[Vec, Vec, Vec]:
        knee = _add(hip, _dir(thigh), THIGH)
        ankle = _add(knee, _dir(shin), SHIN)
        toe = _add(ankle, _dir(_foot(shin, foot)), FOOT)
        return knee, ankle, toe

    knee_n, ankle_n, toe_n = leg(pose.thigh_n, pose.shin_n, pose.foot_n)
    knee_f, ankle_f, toe_f = leg(pose.thigh_f, pose.shin_f, pose.foot_f)

    def arm(u: float, f: float) -> tuple[Vec, Vec]:
        elbow = _add(shoulder, _dir(u), UARM)
        return elbow, _add(elbow, _dir(f), FARM)

    elbow_n, hand_n = arm(pose.uarm_n, pose.farm_n)
    elbow_f, hand_f = arm(pose.uarm_f, pose.farm_f)

    pts = [hip, shoulder, neck, head, knee_n, ankle_n, toe_n, knee_f, ankle_f, toe_f]
    arms = [elbow_n, hand_n, elbow_f, hand_f]
    if pose.rot:
        pts = [_rot(p, hip, pose.rot) for p in pts]
        arms = [_rot(p, hip, pose.rot) for p in arms]
    blade = None if pose.blade is None else pose.blade - pose.rot

    # Apoyo: el punto más bajo del cuerpo toca el suelo (y = 0)
    if pose.hang:
        # Brazos rectos hacia arriba: la mano cercana marca el ancla.
        hx, hy = arms[1]
        ox, oy = HANG_X - hx, HANG_Y - hy
    else:
        contacts = [
            pts[5][1] + SOLE,
            pts[6][1] + SOLE * 0.6,
            pts[8][1] + SOLE,
            pts[9][1] + SOLE * 0.6,
        ]
        if pose.rot:
            contacts += [p[1] + 3.0 for p in pts[:5]] + [pts[3][1] + HEAD_R]
            contacts += [p[1] + 1.5 for p in arms]
        ox, oy = 0.0, -max(contacts) - pose.lift
    ox += pose.dx

    def mv(p: Vec) -> Vec:
        return p[0] + ox, p[1] + oy

    pts = [mv(p) for p in pts]
    arms = [mv(p) for p in arms]
    elbow_n, hand_n, elbow_f, hand_f = arms
    if pose.hands is not None:
        target = pose.hands
        elbow_n, hand_n = _ik(pts[1], target, UARM, FARM)
        elbow_f, hand_f = _ik(pts[1], (target[0] - 2.0, target[1]), UARM, FARM)
    return Joints(
        hip=pts[0],
        shoulder=pts[1],
        neck=pts[2],
        head=pts[3],
        knee_n=pts[4],
        ankle_n=pts[5],
        toe_n=pts[6],
        knee_f=pts[7],
        ankle_f=pts[8],
        toe_f=pts[9],
        elbow_n=elbow_n,
        hand_n=hand_n,
        elbow_f=elbow_f,
        hand_f=hand_f,
        lean=pose.lean + pose.rot,
        head_angle=pose.lean + pose.head + pose.rot,
        blade=blade,
    )


# ---------------------------------------------------------------------------
# Biblioteca de poses
# ---------------------------------------------------------------------------

STAND = Pose()


def _lerp(a: float, b: float, k: float) -> float:
    return a + (b - a) * k


def blend(a: Pose, b: Pose, k: float) -> Pose:
    """Interpola dos poses (campos numéricos; el resto se toma de ``b``
    si ``k >= 0.5``)."""

    def opt(x: float | None, y: float | None) -> float | None:
        if x is None or y is None:
            return y if k >= 0.5 else x
        return _lerp(x, y, k)

    base = b if k >= 0.5 else a
    return replace(
        base,
        lean=_lerp(a.lean, b.lean, k),
        head=_lerp(a.head, b.head, k),
        thigh_n=_lerp(a.thigh_n, b.thigh_n, k),
        shin_n=_lerp(a.shin_n, b.shin_n, k),
        thigh_f=_lerp(a.thigh_f, b.thigh_f, k),
        shin_f=_lerp(a.shin_f, b.shin_f, k),
        foot_n=opt(a.foot_n, b.foot_n),
        foot_f=opt(a.foot_f, b.foot_f),
        uarm_n=_lerp(a.uarm_n, b.uarm_n, k),
        farm_n=_lerp(a.farm_n, b.farm_n, k),
        uarm_f=_lerp(a.uarm_f, b.uarm_f, k),
        farm_f=_lerp(a.farm_f, b.farm_f, k),
        blade=opt(a.blade, b.blade),
        rot=_lerp(a.rot, b.rot, k),
        lift=_lerp(a.lift, b.lift, k),
        dx=_lerp(a.dx, b.dx, k),
    )


def run_pose(phi: float, amp: float = 1.0) -> Pose:
    """Ciclo de carrera: ``phi`` en radianes (pierna cercana delante en
    pi/2). Los brazos van en oposición a las piernas."""

    def leg(p: float) -> tuple[float, float, float | None]:
        thigh = amp * 40.0 * math.sin(p)
        bend = amp * (8.0 + 78.0 * max(0.0, math.cos(p - 0.5)))
        shin = thigh - bend
        foot = shin + 90.0 if bend > 30 else None
        return thigh, shin, foot if foot is None else min(130.0, foot)

    tn, sn, fn = leg(phi)
    tf, sf, ff = leg(phi + math.pi)
    un = -amp * 38.0 * math.sin(phi)
    uf = amp * 38.0 * math.sin(phi)
    return Pose(
        lean=2.0 + 12.0 * amp,
        head=-4.0 * amp,
        thigh_n=tn,
        shin_n=sn,
        foot_n=fn,
        thigh_f=tf,
        shin_f=sf,
        foot_f=ff,
        uarm_n=un,
        farm_n=un + 25.0 + 55.0 * amp,
        uarm_f=uf,
        farm_f=uf + 25.0 + 55.0 * amp,
    )


CROUCH = Pose(
    lean=32.0,
    head=-18.0,
    thigh_n=92.0,
    shin_n=-22.0,
    thigh_f=82.0,
    shin_f=-30.0,
    uarm_n=40.0,
    farm_n=20.0,
    uarm_f=30.0,
    farm_f=12.0,
)
CROUCH_HALF = blend(STAND, CROUCH, 0.55)

FALL = Pose(
    lean=-6.0,
    head=-8.0,
    thigh_n=18.0,
    shin_n=-14.0,
    thigh_f=-4.0,
    shin_f=-30.0,
    foot_n=40.0,
    foot_f=30.0,
    uarm_n=150.0,
    farm_n=170.0,
    uarm_f=-160.0,
    farm_f=-178.0,
)

HANG = Pose(
    lean=-2.0,
    head=-10.0,
    thigh_n=6.0,
    shin_n=2.0,
    thigh_f=-3.0,
    shin_f=-6.0,
    foot_n=25.0,
    foot_f=20.0,
    uarm_n=178.0,
    farm_n=180.0,
    uarm_f=176.0,
    farm_f=179.0,
    hang=True,
)

ENGARDE = Pose(
    lean=6.0,
    head=-2.0,
    thigh_n=30.0,
    shin_n=6.0,
    thigh_f=-24.0,
    shin_f=-16.0,
    uarm_n=50.0,
    farm_n=86.0,
    blade=82.0,
    uarm_f=-140.0,
    farm_f=-178.0,
)

LUNGE = Pose(
    lean=22.0,
    head=-10.0,
    thigh_n=60.0,
    shin_n=20.0,
    thigh_f=-50.0,
    shin_f=-52.0,
    uarm_n=92.0,
    farm_n=93.0,
    blade=93.0,
    uarm_f=-110.0,
    farm_f=-125.0,
)

PARRY = Pose(
    lean=-2.0,
    head=-6.0,
    thigh_n=26.0,
    shin_n=8.0,
    thigh_f=-26.0,
    shin_f=-14.0,
    uarm_n=42.0,
    farm_n=128.0,
    blade=172.0,
    uarm_f=-140.0,
    farm_f=-175.0,
)

STAGGER = Pose(
    lean=-16.0,
    head=-18.0,
    thigh_n=12.0,
    shin_n=2.0,
    thigh_f=-22.0,
    shin_f=-12.0,
    uarm_n=40.0,
    farm_n=80.0,
    blade=140.0,
    uarm_f=-60.0,
    farm_f=-30.0,
)

KNEEL = Pose(
    lean=22.0,
    head=25.0,
    thigh_n=18.0,
    shin_n=-88.0,
    thigh_f=8.0,
    shin_f=-92.0,
    foot_n=-160.0,
    foot_f=-160.0,
    uarm_n=8.0,
    farm_n=12.0,
    uarm_f=4.0,
    farm_f=8.0,
)

DEAD = Pose(
    lean=0.0,
    head=12.0,
    thigh_n=12.0,
    shin_n=4.0,
    thigh_f=-6.0,
    shin_f=-14.0,
    foot_n=170.0,
    foot_f=160.0,
    uarm_n=168.0,
    farm_n=176.0,
    uarm_f=150.0,
    farm_f=164.0,
    rot=90.0,
)

CLIMB_DX = 9.0
"""Avance hacia la cornisa al trepar (unidades)."""


def _climb(i: int) -> Pose:
    """Trepar 135..149 (i = 0..14). Hasta 142 cuelga de las manos (IK);
    desde 143 está agachado sobre la cornisa y se incorpora."""
    hands = (HANG_X, HANG_Y)
    lifts = (24, 30, 37, 44, 50, 55, 58, 60)
    if i <= 7:
        k = i / 7
        body = Pose(
            lean=_lerp(-2.0, 40.0, k),
            head=_lerp(-10.0, -25.0, k),
            thigh_n=_lerp(6.0, 95.0, k * k),
            shin_n=_lerp(2.0, -45.0, k * k),
            thigh_f=_lerp(-3.0, 25.0, k),
            shin_f=_lerp(-6.0, -40.0, k),
            foot_n=_lerp(25.0, 40.0, k),
            foot_f=_lerp(20.0, 10.0, k),
            lift=float(lifts[i]),
            dx=_lerp(0.0, CLIMB_DX * 0.5, k),
            hands=hands,
        )
        return body
    k = (i - 8) / 6
    crouch = replace(CROUCH, lift=ROW_UNITS, dx=CLIMB_DX)
    stand = replace(STAND, lift=ROW_UNITS, dx=CLIMB_DX)
    return blend(crouch, stand, k * k)


def _turn(frame: int, base: int, frames: int = 5) -> Pose:
    """Giro: el sprite se estrecha y se invierte (``sx`` negativo = mira
    aún hacia el lado viejo; la dirección del dominio ya cambió)."""
    p = (frame - base + 1) / frames
    c = math.cos(math.pi * (1 - p))
    sx = math.copysign(max(0.5, abs(c)), c)
    return replace(STAND, uarm_n=14.0, farm_n=30.0, uarm_f=-14.0, farm_f=-4.0, sx=sx)


def _drink(i: int) -> Pose:
    """Beber 191..205 (i = 0..14): levanta el frasco, bebe y lo baja."""
    lift_arm = Pose(uarm_n=40.0, farm_n=150.0, item="flask")
    sip = Pose(lean=-8.0, head=-28.0, uarm_n=62.0, farm_n=172.0, item="flask")
    if i < 4:
        return blend(replace(STAND, item="flask"), lift_arm, i / 3)
    if i < 10:
        return blend(lift_arm, sip, min(1.0, (i - 3) / 2))
    return blend(sip, replace(STAND, item="flask" if i < 13 else ""), (i - 9) / 5)


def pose_for(frame: int) -> Pose:
    """Pose del esqueleto para un frame canon (los no catalogados: de pie)."""
    f = frame
    if f == 15 or f <= 0:
        return STAND
    # Carrera (121-132) y arranque (7-11)
    if 121 <= f <= 132:
        return run_pose((f - 121) / 12 * 2 * math.pi)
    if 1 <= f <= 6:
        return run_pose((f - 7) / 12 * 2 * math.pi, 0.25 + 0.1 * f)
    if 7 <= f <= 14:
        k = min(1.0, (f - 6) / 5)
        return run_pose((f - 12) / 12 * 2 * math.pi, 0.3 + 0.65 * k)
    # Giro (45-49) y media vuelta corriendo (48-49 dentro de runturn)
    if 45 <= f <= 49:
        return _turn(f, 45)
    # Frenar (50-52) / media vuelta corriendo (53-55)
    if 50 <= f <= 55:
        brake = Pose(
            lean=-8.0,
            head=-6.0,
            thigh_n=34.0,
            shin_n=22.0,
            thigh_f=-24.0,
            shin_f=-58.0,
            uarm_n=40.0,
            farm_n=85.0,
            uarm_f=22.0,
            farm_f=70.0,
        )
        k = min(1.0, (f - 50) / 2.5)
        return blend(brake, STAND, k * 0.8)
    # Choque contra muro (56-60)
    if 56 <= f <= 60:
        recoil = Pose(
            lean=-16.0,
            head=-14.0,
            thigh_n=14.0,
            shin_n=6.0,
            thigh_f=-14.0,
            shin_f=-10.0,
            uarm_n=70.0,
            farm_n=120.0,
            uarm_f=50.0,
            farm_f=100.0,
        )
        return blend(recoil, STAND, (f - 56) / 4)
    # Salto parado (16-27)
    if 16 <= f <= 27:
        return _standing_jump(f)
    # Salto con carrerilla (34-44)
    if 34 <= f <= 44:
        return _running_jump(f)
    # Saltar hacia la cornisa (67-70) y colgado (71-99)
    if 67 <= f <= 70:
        prep = replace(CROUCH_HALF, uarm_n=160.0, farm_n=170.0, uarm_f=150.0, farm_f=165.0)
        reach = replace(
            HANG, hang=False, lift=18.0, foot_n=20.0, foot_f=15.0, uarm_n=176.0, uarm_f=172.0
        )
        if f == 70:
            return HANG
        return blend(prep, reach, (f - 67) / 2)
    if 71 <= f <= 99:
        swing = {77: 18.0, 78: 9.0, 79: -10.0, 80: -4.0}.get(f, 0.0)
        return replace(
            HANG,
            thigh_n=HANG.thigh_n + swing,
            shin_n=HANG.shin_n + swing * 0.6,
            thigh_f=HANG.thigh_f + swing * 0.8,
            shin_f=HANG.shin_f + swing * 0.5,
        )
    # Caída (102-105)
    if 102 <= f <= 105:
        k = f - 102
        return replace(
            FALL,
            uarm_n=FALL.uarm_n + (12.0 if k % 2 else 0.0),
            uarm_f=FALL.uarm_f - (10.0 if k % 2 == 0 else 0.0),
            thigh_n=FALL.thigh_n + 6.0 * (k % 2),
        )
    # Aterrizajes (106-109)
    if 106 <= f <= 109:
        return {106: CROUCH, 107: CROUCH_HALF, 108: blend(CROUCH_HALF, STAND, 0.6), 109: CROUCH}[f]
    # Agacharse / aterrizaje duro (110-114) y levantarse (115-120)
    if 110 <= f <= 114:
        return {
            110: CROUCH_HALF,
            111: CROUCH,
            112: CROUCH,
            113: replace(CROUCH, head=-5.0),
            114: CROUCH,
        }[f]
    if 115 <= f <= 120:
        return blend(CROUCH, STAND, min(1.0, (f - 114) / 5))
    # Trepar (135-149)
    if 135 <= f <= 149:
        return _climb(f - 135)
    # Espada
    if 150 <= f <= 176:
        return _sword(f)
    # Muertes
    if f == 177:
        return Pose(
            lean=38.0,
            head=40.0,
            thigh_n=62.0,
            shin_n=-20.0,
            thigh_f=50.0,
            shin_f=-30.0,
            uarm_n=-10.0,
            farm_n=-5.0,
            uarm_f=-20.0,
            farm_f=-10.0,
            rot=58.0,
        )
    if f == 178:
        return Pose(
            lean=26.0,
            head=42.0,
            thigh_n=10.0,
            shin_n=4.0,
            thigh_f=-4.0,
            shin_f=-8.0,
            uarm_n=-4.0,
            farm_n=0.0,
            uarm_f=-8.0,
            farm_f=-4.0,
            item="slash",
        )
    if 179 <= f <= 185:
        return _collapse(f - 179)
    # Ratón (186-188): lo resuelve el dibujo
    if 191 <= f <= 205:
        return _drink(f - 191)
    if 207 <= f <= 210:
        return _draw_sword(f - 207)
    # Subir la escalera de salida (217-228): paso lento que se desvanece
    if 217 <= f <= 228:
        i = f - 217
        p = run_pose(i / 6 * 2 * math.pi, 0.45)
        return replace(
            p, lean=4.0, lift=min(18.0, i * 1.6), alpha=max(0.0, 1.0 - max(0, i - 6) / 6)
        )
    if f == 229:
        return Pose(lean=-4.0, head=-16.0, uarm_n=168.0, farm_n=174.0, blade=176.0)
    if 230 <= f <= 240:
        k = (f - 230) / 10
        sheathe = replace(STAND, uarm_n=-10.0, farm_n=24.0, blade=-160.0)
        p = blend(ENGARDE, sheathe, k)
        return replace(p, blade=None) if f >= 238 else p
    if VIZIER_STRIDE_FIRST <= f <= VIZIER_GLOAT:
        return _vizier(f)
    if PRINCESS_WAIT <= f <= PRINCESS_GLIDE_LAST:
        return _princess(f)
    return STAND


# ---------------------------------------------------------------------------
# Poses del visir para las cinemáticas (frames 241..259, fuera del rango
# canon): paso solemne con la mano al pecho, señalar, conjurar el reloj
# de arena y regodearse con las manos juntas.
# ---------------------------------------------------------------------------

VIZIER_STRIDE_FIRST = 241
VIZIER_STRIDE_LAST = 252
VIZIER_POINT = 253
VIZIER_SUMMON_FIRST = 254
VIZIER_SUMMON_LAST = 258
VIZIER_GLOAT = 259


VIZIER_POINT_POSE = Pose(lean=-4.0, head=6.0, uarm_n=92.0, farm_n=94.0, uarm_f=-24.0, farm_f=-10.0)
VIZIER_SUMMON_POSE = Pose(
    lean=-10.0, head=-18.0, uarm_n=142.0, farm_n=168.0, uarm_f=128.0, farm_f=160.0
)
VIZIER_GLOAT_POSE = Pose(lean=-2.0, head=4.0, uarm_n=28.0, farm_n=96.0, uarm_f=26.0, farm_f=92.0)


# Poses de la princesa (frames 260..272): espera con las manos juntas y
# la cabeza baja, se sobresalta, abre los brazos de alegría y camina
# deslizándose (paso corto bajo el vestido).
PRINCESS_WAIT = 260
PRINCESS_STARTLE = 261
PRINCESS_JOY = 262
PRINCESS_GLIDE_FIRST = 263
PRINCESS_GLIDE_LAST = 272

PRINCESS_WAIT_POSE = Pose(lean=5.0, head=14.0, uarm_n=24.0, farm_n=84.0, uarm_f=22.0, farm_f=80.0)
PRINCESS_STARTLE_POSE = Pose(
    lean=-6.0, head=-10.0, uarm_n=58.0, farm_n=132.0, uarm_f=50.0, farm_f=120.0
)
PRINCESS_JOY_POSE = Pose(lean=-3.0, head=-6.0, uarm_n=96.0, farm_n=110.0, uarm_f=84.0, farm_f=100.0)


def _princess(f: int) -> Pose:
    if f == PRINCESS_WAIT:
        return PRINCESS_WAIT_POSE
    if f == PRINCESS_STARTLE:
        return PRINCESS_STARTLE_POSE
    if f == PRINCESS_JOY:
        return PRINCESS_JOY_POSE
    phi = (f - PRINCESS_GLIDE_FIRST) / 10 * 2 * math.pi
    p = run_pose(phi, 0.3)
    # Brazos abiertos hacia delante, sin balanceo: va a su encuentro
    return replace(p, lean=4.0, head=-2.0, uarm_n=70.0, farm_n=96.0, uarm_f=60.0, farm_f=88.0)


def _vizier(f: int) -> Pose:
    if f <= VIZIER_STRIDE_LAST:
        phi = (f - VIZIER_STRIDE_FIRST) / 12 * 2 * math.pi
        p = run_pose(phi, 0.42)
        # Mano cercana al pecho (bajo la barba), la otra caída a la espalda
        return replace(
            p, lean=-3.0, head=2.0, uarm_n=34.0, farm_n=118.0, uarm_f=-26.0, farm_f=-12.0
        )
    if f == VIZIER_POINT:
        return VIZIER_POINT_POSE
    if f <= VIZIER_SUMMON_LAST:
        k = (f - VIZIER_SUMMON_FIRST) / (VIZIER_SUMMON_LAST - VIZIER_SUMMON_FIRST)
        return blend(VIZIER_POINT_POSE, VIZIER_SUMMON_POSE, k)
    return VIZIER_GLOAT_POSE


def _standing_jump(f: int) -> Pose:
    prep = replace(CROUCH_HALF, uarm_n=-40.0, farm_n=-20.0, uarm_f=-50.0, farm_f=-30.0)
    deep = replace(CROUCH, uarm_n=-70.0, farm_n=-50.0, uarm_f=-75.0, farm_f=-60.0, head=-10.0)
    launch = Pose(
        lean=4.0,
        head=-12.0,
        thigh_n=2.0,
        shin_n=0.0,
        thigh_f=-4.0,
        shin_f=-6.0,
        foot_n=18.0,
        foot_f=12.0,
        uarm_n=150.0,
        farm_n=160.0,
        uarm_f=140.0,
        farm_f=155.0,
    )
    peak = replace(
        launch, thigh_n=32.0, shin_n=-12.0, thigh_f=22.0, shin_f=-24.0, uarm_n=168.0, farm_n=175.0
    )
    table = {
        16: prep,
        17: deep,
        18: launch,
        19: peak,
        20: replace(peak, uarm_n=175.0, uarm_f=170.0),
        21: blend(peak, launch, 0.6),
        22: replace(CROUCH_HALF, uarm_n=70.0, farm_n=90.0, uarm_f=60.0, farm_f=80.0),
        23: replace(CROUCH, uarm_n=50.0, farm_n=60.0),
        24: CROUCH_HALF,
        25: blend(CROUCH_HALF, STAND, 0.6),
        26: FALL,
        27: replace(FALL, uarm_n=165.0, uarm_f=-150.0),
    }
    return table[f]


def _running_jump(f: int) -> Pose:
    takeoff = Pose(
        lean=16.0,
        head=-6.0,
        thigh_n=-30.0,
        shin_n=-42.0,
        thigh_f=70.0,
        shin_f=4.0,
        foot_f=100.0,
        uarm_n=60.0,
        farm_n=95.0,
        uarm_f=-50.0,
        farm_f=-30.0,
    )
    push = Pose(
        lean=14.0,
        head=-10.0,
        thigh_n=-46.0,
        shin_n=-50.0,
        foot_n=10.0,
        thigh_f=84.0,
        shin_f=28.0,
        foot_f=110.0,
        uarm_n=115.0,
        farm_n=140.0,
        uarm_f=-62.0,
        farm_f=-40.0,
    )
    split = Pose(
        lean=10.0,
        head=-12.0,
        thigh_n=-52.0,
        shin_n=-78.0,
        foot_n=-10.0,
        thigh_f=78.0,
        shin_f=42.0,
        foot_f=120.0,
        uarm_n=140.0,
        farm_n=152.0,
        uarm_f=-72.0,
        farm_f=-55.0,
    )
    gather = Pose(
        lean=8.0,
        head=-4.0,
        thigh_n=14.0,
        shin_n=-22.0,
        thigh_f=52.0,
        shin_f=10.0,
        uarm_n=95.0,
        farm_n=110.0,
        uarm_f=40.0,
        farm_f=70.0,
    )
    land = replace(CROUCH_HALF, uarm_n=70.0, farm_n=80.0, uarm_f=50.0, farm_f=65.0)
    table = {
        34: takeoff,
        35: blend(takeoff, push, 0.5),
        36: push,
        37: blend(push, split, 0.6),
        38: split,
        39: replace(split, thigh_n=-56.0, thigh_f=84.0),
        40: split,
        41: blend(split, gather, 0.5),
        42: gather,
        43: land,
        44: blend(land, STAND, 0.4),
    }
    return table[f]


def _sword(f: int) -> Pose:
    guard_step = replace(ENGARDE, thigh_n=38.0, shin_n=16.0, thigh_f=-14.0, shin_f=-22.0)
    guard_back = replace(ENGARDE, thigh_n=18.0, shin_n=2.0, thigh_f=-36.0, shin_f=-20.0)
    windup = replace(ENGARDE, lean=0.0, uarm_n=28.0, farm_n=62.0, blade=104.0)
    table = {
        150: PARRY,
        151: windup,
        152: blend(windup, LUNGE, 0.45),
        153: blend(windup, LUNGE, 0.8),
        154: LUNGE,
        155: blend(LUNGE, ENGARDE, 0.5),
        156: blend(LUNGE, ENGARDE, 0.8),
        157: guard_step,
        158: ENGARDE,
        159: replace(PARRY, uarm_n=48.0, farm_n=112.0, blade=150.0),
        160: guard_back,
        161: PARRY,
        162: replace(PARRY, uarm_n=58.0, farm_n=106.0, blade=122.0),
        163: guard_step,
        164: blend(guard_step, ENGARDE, 0.5),
        165: ENGARDE,
        166: replace(STAND, uarm_n=14.0, farm_n=32.0, blade=16.0),
        167: replace(ENGARDE, lean=-8.0, head=-10.0, uarm_n=66.0, farm_n=100.0, blade=58.0),
        168: replace(ENGARDE, lean=-3.0, uarm_n=18.0, farm_n=70.0, blade=124.0),
        169: replace(PARRY, uarm_n=48.0, farm_n=112.0, blade=150.0),
        170: ENGARDE,
        171: ENGARDE,
        172: STAGGER,
        173: replace(STAGGER, lean=-20.0, head=-24.0),
        174: blend(STAGGER, ENGARDE, 0.5),
        175: blend(STAGGER, ENGARDE, 0.8),
        176: ENGARDE,
    }
    return table.get(f, ENGARDE)


def _collapse(i: int) -> Pose:
    buckle = Pose(
        lean=12.0,
        head=22.0,
        thigh_n=40.0,
        shin_n=-14.0,
        thigh_f=34.0,
        shin_f=-24.0,
        uarm_n=18.0,
        farm_n=26.0,
        uarm_f=10.0,
        farm_f=18.0,
    )
    steps = (
        buckle,
        blend(buckle, KNEEL, 0.6),
        KNEEL,
        replace(KNEEL, rot=28.0, lean=30.0),
        blend(replace(KNEEL, rot=28.0), DEAD, 0.55),
        blend(replace(KNEEL, rot=28.0), DEAD, 0.85),
        DEAD,
    )
    return steps[min(i, len(steps) - 1)]


def _draw_sword(i: int) -> Pose:
    hip = replace(STAND, uarm_n=-12.0, farm_n=26.0, blade=-158.0)
    up = replace(STAND, lean=0.0, uarm_n=40.0, farm_n=150.0, blade=178.0)
    mid = blend(up, ENGARDE, 0.5)
    return (hip, up, mid, ENGARDE)[min(i, 3)]
