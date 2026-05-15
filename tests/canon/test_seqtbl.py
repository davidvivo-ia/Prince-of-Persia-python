"""Tests del seqtbl + frames + sequence runner."""

from __future__ import annotations

import pytest

from pop2026canon.domain.actions import FrameID, Seq
from pop2026canon.domain.frames import (
    FrameFlag,
    all_known_frame_ids,
    get_frame,
    total_known_frames,
)
from pop2026canon.domain.seqtbl import (
    BLOCK_WINDOW,
    STRIKE_WINDOW,
    TABLE,
    ActKind,
    SeqAct,
    dx,
    frame,
    get,
    jmp,
    set_fall,
)


class TestSequenceTable:
    def test_25_critical_sequences(self) -> None:
        """Las 25 secuencias críticas están en la tabla."""
        critical = [
            Seq.STAND,
            Seq.START_RUN,
            Seq.RUN,
            Seq.STOP_RUN,
            Seq.TURN,
            Seq.STANDING_JUMP,
            Seq.RUN_JUMP,
            Seq.FALL,
            Seq.FALL_AFTER_STANDING_JUMP,
            Seq.SOFT_LAND,
            Seq.GRAB_LEDGE_MIDAIR,
            Seq.JUMP_UP_GRAB_STRAIGHT,
            Seq.JUMP_UP_GRAB,
            Seq.CLIMB_UP,
            Seq.RELEASE_LEDGE_LAND,
            Seq.CROUCH,
            Seq.STAND_UP_FROM_CROUCH,
            Seq.DRAW_SWORD,
            Seq.STRIKE,
            Seq.DYING,
            Seq.STABBED_TO_DEATH,
            Seq.SPIKED,
            Seq.CHOMPED,
            Seq.CRUSHED,
            Seq.LOOSE_FLOOR_FELL_ON_KID,
            Seq.DRINK,
        ]
        for s in critical:
            assert int(s) in TABLE, f"falta seq {s.name}"

    def test_combat_advanced_sequences(self) -> None:
        """Combate avanzado: engarde, advance, retreat, block."""
        for s in (
            Seq.ENGARDE,
            Seq.ADVANCE,
            Seq.RETREAT,
            Seq.BLOCK_STRIKE,
            Seq.BLOCK_TO_STRIKE,
            Seq.PUT_SWORD_AWAY,
        ):
            assert int(s) in TABLE, f"falta seq combate {s.name}"

    def test_locomotion_extra_sequences(self) -> None:
        """Locomoción extra: runturn, bump, hard/med land."""
        for s in (
            Seq.RUNTURN,
            Seq.BUMP,
            Seq.HARD_LAND,
            Seq.MED_LAND,
            Seq.JUMP_HANG_MIDAIR,
            Seq.BUMPED_FALL,
            Seq.GUARD_FALL,
            Seq.EXIT_LEVEL,
        ):
            assert int(s) in TABLE, f"falta seq locomoción {s.name}"

    def test_table_at_least_40_entries(self) -> None:
        assert len(TABLE) >= 40

    def test_get_raises_on_unknown(self) -> None:
        with pytest.raises(KeyError, match="no implementada"):
            get(999)


class TestNewSequenceShapes:
    def test_advance_moves_right(self) -> None:
        seq = get(Seq.ADVANCE)
        dxs = [a.arg for a in seq if a.kind is ActKind.DX]
        assert sum(dxs) > 0

    def test_retreat_moves_left(self) -> None:
        seq = get(Seq.RETREAT)
        dxs = [a.arg for a in seq if a.kind is ActKind.DX]
        assert sum(dxs) < 0

    def test_engarde_loops_idle(self) -> None:
        seq = get(Seq.ENGARDE)
        assert seq[-1].kind is ActKind.JMP
        assert seq[-1].arg == int(Seq.ENGARDE)

    def test_block_strike_returns_to_engarde(self) -> None:
        seq = get(Seq.BLOCK_STRIKE)
        assert seq[-1].arg == int(Seq.ENGARDE)

    def test_block_to_strike_chains_to_strike(self) -> None:
        seq = get(Seq.BLOCK_TO_STRIKE)
        assert seq[-1].arg == int(Seq.STRIKE)

    def test_exit_level_uses_canonical_frames(self) -> None:
        seq = get(Seq.EXIT_LEVEL)
        frame_ids = [a.arg for a in seq if a.kind is ActKind.FRAME]
        assert min(frame_ids) == 217
        assert max(frame_ids) == 228


class TestDSLConstructors:
    def test_frame_act(self) -> None:
        a = frame(15)
        assert a.kind is ActKind.FRAME
        assert a.arg == 15

    def test_frame_accepts_frameid_enum(self) -> None:
        a = frame(FrameID.STAND)
        assert a.arg == 15

    def test_dx_act(self) -> None:
        a = dx(3)
        assert a.kind is ActKind.DX
        assert a.arg == 3

    def test_set_fall_act(self) -> None:
        a = set_fall(2, 5)
        assert a.kind is ActKind.SET_FALL
        assert a.arg == 2
        assert a.arg2 == 5

    def test_jmp_with_seq_enum(self) -> None:
        a = jmp(Seq.RUN)
        assert a.arg == int(Seq.RUN)


class TestStandSequence:
    def test_stand_is_idle_loop(self) -> None:
        seq = get(Seq.STAND)
        # Termina con jmp(STAND) — auto-repite
        assert seq[-1].kind is ActKind.JMP
        assert seq[-1].arg == int(Seq.STAND)


class TestRunSequence:
    def test_run_cycle_has_12_frames(self) -> None:
        """El run cycle canónico es de 12 frames (121-132)."""
        seq = get(Seq.RUN)
        frame_acts = [a for a in seq if a.kind is ActKind.FRAME]
        assert len(frame_acts) == 12

    def test_run_loops_to_self(self) -> None:
        seq = get(Seq.RUN)
        assert seq[-1].kind is ActKind.JMP
        assert seq[-1].arg == int(Seq.RUN)

    def test_run_uses_canonical_frame_range(self) -> None:
        seq = get(Seq.RUN)
        frame_ids = [a.arg for a in seq if a.kind is ActKind.FRAME]
        assert min(frame_ids) == 121
        assert max(frame_ids) == 132


class TestRunJumpHasFrame43:
    def test_runjump_contains_frame_43(self) -> None:
        """Frame_43 es el trigger del shadow step en L6."""
        seq = get(Seq.RUN_JUMP)
        frame_ids = [a.arg for a in seq if a.kind is ActKind.FRAME]
        assert 43 in frame_ids


class TestCombatWindows:
    def test_strike_window_canonical(self) -> None:
        # Frames 165-167 son la ventana de impacto del strike
        assert 165 in STRIKE_WINDOW
        assert 167 in STRIKE_WINDOW
        # 168 ya es recover
        assert 168 not in STRIKE_WINDOW

    def test_block_window_canonical(self) -> None:
        # Frames 161-164 son la ventana de bloqueo
        assert 161 in BLOCK_WINDOW
        assert 164 in BLOCK_WINDOW
        # 165 ya es strike windup, no bloqueo
        assert 165 not in BLOCK_WINDOW


class TestFrames:
    def test_canonical_key_frames_defined(self) -> None:
        # Subconjunto crítico — explícitamente definidos
        critical = (15, 43, 91, 102, 165, 167, 177, 178, 185, 207, 229)
        for fid in critical:
            f = get_frame(fid)
            assert f.name != f"f{fid:03d}", (
                f"frame {fid} debería tener nombre semántico, no placeholder"
            )

    def test_unknown_frame_returns_placeholder(self) -> None:
        f = get_frame(250)
        assert f.id == 250
        assert f.name == "f250"

    def test_run_cycle_has_footstep_sounds(self) -> None:
        # Frames 124 y 128 marcan pisada en el run cycle (cada ~4 frames)
        f124 = get_frame(124)
        f128 = get_frame(128)
        assert FrameFlag.SOUND_FOOTSTEP in f124.flags
        assert FrameFlag.SOUND_FOOTSTEP in f128.flags

    def test_spiked_chomped_invulnerable(self) -> None:
        # Frames de muerte por trampa: invulnerable mientras dura la anim
        assert FrameFlag.HARM_INVULNERABLE in get_frame(177).flags
        assert FrameFlag.HARM_INVULNERABLE in get_frame(178).flags

    def test_total_frames_known(self) -> None:
        # >100 frames con definición explícita (de los ~180 canon)
        assert total_known_frames() > 100

    def test_all_known_unique(self) -> None:
        ids = all_known_frame_ids()
        assert len(ids) == len(set(ids))


class TestSeqActImmutable:
    def test_seq_act_is_frozen(self) -> None:
        a = SeqAct(ActKind.FRAME, 15)
        with pytest.raises(AttributeError):
            a.arg = 99  # type: ignore[misc]
