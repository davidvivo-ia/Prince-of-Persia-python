"""Tests del sistema de keyframes."""

from __future__ import annotations

from pop2026.domain.actions import Action
from pop2026.domain.poses import (
    FRAMES_BY_ACTION,
    REST,
    JointPose,
    Keyframe,
    interpolate,
)


class TestJointPoseLerp:
    def test_lerp_zero_returns_a(self) -> None:
        a = JointPose(head_dy=0.0)
        b = JointPose(head_dy=1.0)
        assert a.lerp(b, 0.0).head_dy == 0.0

    def test_lerp_one_returns_b(self) -> None:
        a = JointPose(head_dy=0.0)
        b = JointPose(head_dy=1.0)
        assert a.lerp(b, 1.0).head_dy == 1.0

    def test_lerp_half_returns_mean(self) -> None:
        a = JointPose(head_dy=0.0, torso_dy=2.0)
        b = JointPose(head_dy=1.0, torso_dy=4.0)
        m = a.lerp(b, 0.5)
        assert m.head_dy == 0.5
        assert m.torso_dy == 3.0

    def test_lerp_independent_for_each_field(self) -> None:
        a = JointPose(arm_l_dx=0.0, arm_r_dx=10.0)
        b = JointPose(arm_l_dx=5.0, arm_r_dx=-5.0)
        m = a.lerp(b, 0.5)
        assert m.arm_l_dx == 2.5
        assert m.arm_r_dx == 2.5


class TestInterpolate:
    def test_unknown_action_returns_rest(self) -> None:
        # STAND no tiene keyframes definidos.
        assert interpolate(Action.STAND, 0.5) == REST

    def test_walk_at_phase_zero(self) -> None:
        pose = interpolate(Action.WALK, 0.0)
        # Pierna izquierda hacia atrás, derecha hacia adelante (definido en frame 0).
        assert pose.leg_l_dx < 0
        assert pose.leg_r_dx > 0

    def test_walk_at_phase_half(self) -> None:
        pose = interpolate(Action.WALK, 0.5)
        # En el medio del ciclo, las piernas se cruzan.
        assert pose.leg_l_dx > 0
        assert pose.leg_r_dx < 0

    def test_strike_progresses_arm_forward(self) -> None:
        early = interpolate(Action.STRIKE, 0.0)
        peak = interpolate(Action.STRIKE, 0.6)
        # El brazo derecho debería extenderse al frente en el pico del golpe.
        assert peak.arm_r_dx > early.arm_r_dx

    def test_lunge_reaches_further_than_strike(self) -> None:
        strike = interpolate(Action.STRIKE, 0.6)
        lunge = interpolate(Action.LUNGE, 0.7)
        assert lunge.arm_r_dx > strike.arm_r_dx

    def test_phase_clamped_to_unit_range(self) -> None:
        # Valores fuera de [0, 1] no deben romper.
        pose_neg = interpolate(Action.WALK, -0.5)
        pose_big = interpolate(Action.WALK, 1.5)
        assert isinstance(pose_neg, JointPose)
        assert isinstance(pose_big, JointPose)


class TestKeyframeData:
    def test_all_action_frames_start_at_zero(self) -> None:
        for action, frames in FRAMES_BY_ACTION.items():
            assert frames[0].t == 0.0, f"{action.name} no empieza en t=0"

    def test_all_action_frames_end_at_one(self) -> None:
        for action, frames in FRAMES_BY_ACTION.items():
            assert frames[-1].t == 1.0, f"{action.name} no termina en t=1"

    def test_frames_are_sorted_by_time(self) -> None:
        for action, frames in FRAMES_BY_ACTION.items():
            ts = [f.t for f in frames]
            assert ts == sorted(ts), f"{action.name} tiene frames desordenados"

    def test_keyframe_pose_field_holds_jointpose(self) -> None:
        for _, frames in FRAMES_BY_ACTION.items():
            for kf in frames:
                assert isinstance(kf, Keyframe)
                assert isinstance(kf.pose, JointPose)
