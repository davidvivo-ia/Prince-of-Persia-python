"""Tests de las máquinas de estado de trampas."""

from __future__ import annotations

from pop2026canon.domain.constants import CHOMPER_SPEED, LOOSE_FLOOR_DELAY
from pop2026canon.domain.tiles import Tile
from pop2026canon.domain.traps import (
    SPIKE_LETHAL_FALL_Y,
    ChomperPhase,
    GatePhase,
    LevelState,
    chomper_is_lethal,
    chomper_phase,
    gate_is_passable,
    spike_kills_on_land,
    tick_chomper,
    tick_gate,
    tick_loose,
    trap_kills,
)

CELL = (1, 2, 1)
"""Coordenada de prueba: (room=1, col=2, row=1)."""


class TestLevelState:
    def test_empty_default(self) -> None:
        s = LevelState()
        assert s.state_at(CELL) == 0
        assert CELL not in s.fallen_floors
        assert CELL not in s.open_gates

    def test_with_state(self) -> None:
        s = LevelState().with_state(CELL, 5)
        assert s.state_at(CELL) == 5

    def test_with_state_zero_removes(self) -> None:
        s = LevelState().with_state(CELL, 5)
        s = s.with_state(CELL, 0)
        assert s.state_at(CELL) == 0
        assert len(s.tile_states) == 0

    def test_immutable(self) -> None:
        s1 = LevelState()
        s2 = s1.with_state(CELL, 3)
        assert s1.state_at(CELL) == 0
        assert s2.state_at(CELL) == 3


class TestLooseFloor:
    def test_pressing_increments(self) -> None:
        s = LevelState()
        s, fell = tick_loose(s, CELL, kid_pressing=True)
        assert s.state_at(CELL) == 1
        assert fell is False

    def test_release_resets(self) -> None:
        s = LevelState().with_state(CELL, 5)
        s, fell = tick_loose(s, CELL, kid_pressing=False)
        assert s.state_at(CELL) == 0
        assert fell is False

    def test_falls_after_delay(self) -> None:
        s = LevelState()
        fell_once = False
        for _ in range(LOOSE_FLOOR_DELAY):
            s, fell = tick_loose(s, CELL, kid_pressing=True)
            if fell:
                fell_once = True
                break
        assert fell_once
        assert CELL in s.fallen_floors

    def test_fallen_stays_fallen(self) -> None:
        s = LevelState().with_floor_fallen(CELL)
        s, fell = tick_loose(s, CELL, kid_pressing=True)
        assert fell is False  # no se cae dos veces
        assert CELL in s.fallen_floors


class TestChomper:
    def test_cycle_length(self) -> None:
        """El chomper completa un ciclo en `CHOMPER_SPEED=15` ticks."""
        phases = [chomper_phase(t) for t in range(CHOMPER_SPEED * 2)]
        # Las primeras 15 entradas deben repetirse en las siguientes 15
        assert phases[:15] == phases[15:]

    def test_phase_open(self) -> None:
        assert chomper_phase(0) is ChomperPhase.OPEN
        assert chomper_phase(6) is ChomperPhase.OPEN

    def test_phase_closed_lethal(self) -> None:
        assert chomper_phase(10) is ChomperPhase.CLOSED
        assert chomper_phase(11) is ChomperPhase.CLOSED

    def test_chomper_is_lethal(self) -> None:
        s = LevelState()
        s = s.with_state(CELL, 10)  # tick 10 = CLOSED
        assert chomper_is_lethal(s, CELL)

    def test_chomper_open_not_lethal(self) -> None:
        s = LevelState()  # state 0 = OPEN
        assert not chomper_is_lethal(s, CELL)

    def test_tick_advances(self) -> None:
        s = LevelState()
        s = tick_chomper(s, CELL)
        assert s.state_at(CELL) == 1

    def test_tick_wraps_to_zero(self) -> None:
        s = LevelState().with_state(CELL, CHOMPER_SPEED - 1)
        s = tick_chomper(s, CELL)
        assert s.state_at(CELL) == 0


class TestSpike:
    def test_lethal_at_threshold(self) -> None:
        assert spike_kills_on_land(SPIKE_LETHAL_FALL_Y)

    def test_safe_walking(self) -> None:
        assert not spike_kills_on_land(0)
        assert not spike_kills_on_land(5)

    def test_lethal_when_falling_fast(self) -> None:
        assert spike_kills_on_land(20)
        assert spike_kills_on_land(33)  # FALLING_SPEED_MAX

    def test_trap_kills_on_spike(self) -> None:
        s = LevelState()
        assert trap_kills(s, CELL, Tile.SPIKE, fall_y=20)
        assert not trap_kills(s, CELL, Tile.SPIKE, fall_y=0)


class TestGate:
    def test_starts_closed(self) -> None:
        s = LevelState()
        assert not gate_is_passable(s, CELL)
        assert s.state_at(CELL) == int(GatePhase.CLOSED)

    def test_plate_pressed_opens(self) -> None:
        s = LevelState()
        for _ in range(int(GatePhase.OPEN)):
            s = tick_gate(s, CELL, plate_pressed=True)
        assert s.state_at(CELL) == int(GatePhase.OPEN)
        assert gate_is_passable(s, CELL)

    def test_plate_release_closes(self) -> None:
        # Abre
        s = LevelState()
        for _ in range(int(GatePhase.OPEN)):
            s = tick_gate(s, CELL, plate_pressed=True)
        assert gate_is_passable(s, CELL)
        # Suelta plate
        for _ in range(int(GatePhase.OPEN)):
            s = tick_gate(s, CELL, plate_pressed=False)
        assert s.state_at(CELL) == int(GatePhase.CLOSED)
        assert not gate_is_passable(s, CELL)

    def test_cannot_exceed_open_limit(self) -> None:
        s = LevelState().with_state(CELL, int(GatePhase.OPEN))
        s = tick_gate(s, CELL, plate_pressed=True)
        assert s.state_at(CELL) == int(GatePhase.OPEN)

    def test_cannot_go_below_zero(self) -> None:
        s = LevelState()
        s = tick_gate(s, CELL, plate_pressed=False)
        assert s.state_at(CELL) == 0
