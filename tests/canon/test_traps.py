"""Tests de las máquinas de estado de trampas (canon seg007.c)."""

from __future__ import annotations

from dataclasses import replace

from pop2026canon.application.controller import Command
from pop2026canon.application.tick import advance
from pop2026canon.domain.constants import CHOMPER_SPEED, LOOSE_FLOOR_DELAY
from pop2026canon.domain.game import GameStatus, new_game
from pop2026canon.domain.level import DoorLink, Level
from pop2026canon.domain.room import Room
from pop2026canon.domain.tiles import Tile, encode_tile
from pop2026canon.domain.traps import (
    CHOMPER_BITE_FRAME,
    GATE_PASSABLE_MIN,
    LOOSE_SHAKE,
    SPIKE_DISABLED,
    SPIKE_OUT,
    ChomperPhase,
    GatePhase,
    LevelState,
    chomper_is_lethal,
    chomper_phase,
    chomper_start,
    chomper_stop,
    gate_is_passable,
    loose_press,
    loose_shake,
    next_chomper_timing,
    spike_harm,
    spike_kills,
    spike_trigger,
    start_chompers,
    tick_chomper,
    tick_gate,
    tick_loose,
    tick_spike,
    trap_kills,
)

CELL = (1, 2, 1)
"""Coordenada de prueba: (room=1, col=2, row=1)."""

E, F, W = Tile.EMPTY, Tile.FLOOR, Tile.WALL


def _level(rows: list[list[Tile]], *, start_col: int, start_row: int, **kw) -> Level:  # type: ignore[no-untyped-def]
    fg = tuple(encode_tile(t, 0) for row in rows for t in row)
    room = Room(id=1, fg=fg, bg=tuple([0] * 30))
    return Level(
        number=1,
        name="traps",
        rooms=(room,),
        start_room=1,
        start_col=start_col,
        start_row=start_row,
        **kw,
    )


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
    def test_press_starts_countdown(self) -> None:
        s = loose_press(LevelState(), CELL)
        assert s.state_at(CELL) == 1

    def test_falls_after_delay_even_if_released(self) -> None:
        """Canon: una vez pisada, la losa cae a los 11 ticks aunque el kid
        ya no esté encima."""
        s = loose_press(LevelState(), CELL)
        fell = False
        for _ in range(LOOSE_FLOOR_DELAY):
            s, fell = tick_loose(s, CELL)
            if fell:
                break
        assert fell
        assert CELL in s.fallen_floors
        assert len(s.falling_tiles) == 1
        assert (s.falling_tiles[0].room, s.falling_tiles[0].col, s.falling_tiles[0].row) == CELL

    def test_shake_only_does_not_fall(self) -> None:
        """Una losa sacudida por otra (do_knock) tiembla y se queda."""
        s = loose_shake(LevelState(), CELL)
        assert s.state_at(CELL) == LOOSE_SHAKE
        for _ in range(10):
            s, fell = tick_loose(s, CELL)
            assert not fell
        assert s.state_at(CELL) == 0
        assert CELL not in s.fallen_floors

    def test_press_while_shaking_starts_countdown(self) -> None:
        s = loose_press(loose_shake(LevelState(), CELL), CELL)
        assert s.state_at(CELL) == 1

    def test_fallen_stays_fallen(self) -> None:
        s = LevelState().with_floor_fallen(CELL)
        s = loose_press(s, CELL)
        s, fell = tick_loose(s, CELL)
        assert fell is False
        assert CELL in s.fallen_floors

    def test_falling_tile_leaves_debris_and_hole(self) -> None:
        """Integración: el kid pisa la losa, se aparta, la losa cae y
        se estrella en la fila de abajo dejando escombros; arriba queda
        un agujero."""
        rows = [[E] * 10, [F] * 10, [F] * 10]
        rows[1][5] = Tile.LOOSE
        lvl = _level(rows, start_col=5, start_row=1)
        g = new_game(lvl)
        g = advance(g, Command())  # pisa
        assert g.state.state_at((1, 5, 1)) in (1, 2)
        g = replace(g, kid=replace(g.kid, curr_col=2))  # se aparta
        for _ in range(40):
            g = advance(g, Command())
        assert (1, 5, 1) in g.state.fallen_floors
        assert (1, 5, 2) in g.state.debris_cells
        assert not g.state.falling_tiles

    def test_falling_tile_hits_kid_below(self) -> None:
        rows = [[F] * 10, [E] * 10, [F] * 10]
        rows[0][5] = Tile.LOOSE
        lvl = _level(rows, start_col=5, start_row=2)
        g = new_game(lvl)
        s = loose_press(g.state, (1, 5, 0))
        g = replace(g, state=s)
        hp0 = g.kid.hp_curr
        for _ in range(60):
            g = advance(g, Command())
        assert g.kid.hp_curr == hp0 - 1, "la losa en la cabeza quita 1 HP"


class TestSpike:
    def test_trigger_extends_then_retracts(self) -> None:
        """Canon: 1..4 saliendo, 15 ticks fuera (0x8F..0x80), 6..8
        recogiéndose, 0."""
        s = spike_trigger(LevelState(), CELL)
        seen = []
        for _ in range(40):
            seen.append(s.state_at(CELL))
            s = tick_spike(s, CELL)
        assert seen[:5] == [1, 2, 3, 4, SPIKE_OUT]
        assert seen[5] == SPIKE_OUT - 1
        assert 6 in seen
        assert 8 in seen
        assert seen[-1] == 0

    def test_harm_levels(self) -> None:
        assert spike_harm(0) == 0
        assert spike_harm(2) == 2
        assert spike_harm(SPIKE_OUT) == 1
        assert spike_harm(7) == 0
        assert spike_harm(SPIKE_DISABLED) == 0

    def test_running_dies_only_while_extending(self) -> None:
        s = LevelState().with_state(CELL, 3)
        assert spike_kills(s, CELL, running=True, landing=False)
        s = LevelState().with_state(CELL, SPIKE_OUT)
        assert not spike_kills(s, CELL, running=True, landing=False), "fuera: se puede pasar"

    def test_landing_dies_if_out_or_extending(self) -> None:
        s = LevelState().with_state(CELL, SPIKE_OUT)
        assert spike_kills(s, CELL, running=False, landing=True)
        s = LevelState().with_state(CELL, 0)
        assert not spike_kills(s, CELL, running=False, landing=True), "recogidos: inofensivos"

    def test_retrigger_while_out_keeps_them_out(self) -> None:
        s = LevelState().with_state(CELL, SPIKE_OUT - 5)
        assert spike_trigger(s, CELL).state_at(CELL) == SPIKE_OUT

    def test_trap_kills_on_spike(self) -> None:
        s = LevelState().with_state(CELL, SPIKE_OUT)
        assert trap_kills(s, CELL, Tile.SPIKE, fall_y=20)
        assert not trap_kills(LevelState(), CELL, Tile.SPIKE, fall_y=20)

    def test_falling_onto_spikes_kills(self) -> None:
        """Integración: al caer, los pinchos de abajo salen y matan."""
        rows = [[F] * 10, [E] * 10, [F] * 10]
        rows[0][5] = E
        rows[2][5] = Tile.SPIKE
        lvl = _level(rows, start_col=5, start_row=0)
        g = new_game(lvl)
        for _ in range(30):
            g = advance(g, Command())
            if g.status is GameStatus.LOST_DIED:
                break
        assert g.status is GameStatus.LOST_DIED

    def test_walking_through_extended_spikes_is_safe(self) -> None:
        rows = [[E] * 10, [E] * 10, [F] * 10]
        rows[2][5] = Tile.SPIKE
        lvl = _level(rows, start_col=3, start_row=2)
        g = new_game(lvl)
        g = replace(g, state=g.state.with_state((1, 5, 2), SPIKE_OUT))
        for _ in range(30):
            g = advance(g, Command(right=True, shift=True))
            assert g.status is GameStatus.PLAYING, "andando con cuidado no mata"


class TestChomper:
    def test_timing_sequence(self) -> None:
        t = CHOMPER_SPEED
        seq = []
        for _ in range(6):
            seq.append(t)
            t = next_chomper_timing(t)
        assert seq == [15, 12, 9, 6, 13, 10]

    def test_start_sets_staggered_timings(self) -> None:
        s = start_chompers(LevelState(), 1, 1, [2, 5, 8])
        assert s.state_at((1, 2, 1)) == 15
        assert s.state_at((1, 5, 1)) == 12
        assert s.state_at((1, 8, 1)) == 9

    def test_cycle_bites_at_frame_2(self) -> None:
        s = chomper_start(LevelState(), CELL, 15)
        lethal_ticks = []
        for t in range(CHOMPER_SPEED * 2):
            s = tick_chomper(s, CELL)
            if chomper_is_lethal(s, CELL):
                lethal_ticks.append(t)
        assert len(lethal_ticks) == 2
        assert s.state_at(CELL) & 0x7F in range(1, CHOMPER_SPEED + 1)

    def test_phase_names(self) -> None:
        assert chomper_phase(0) is ChomperPhase.OPEN
        assert chomper_phase(CHOMPER_BITE_FRAME) is ChomperPhase.CLOSED
        assert chomper_phase(10) is ChomperPhase.OPEN

    def test_idle_chomper_does_not_tick(self) -> None:
        s = tick_chomper(LevelState(), CELL)
        assert s.state_at(CELL) == 0

    def test_stop_only_when_open(self) -> None:
        s = LevelState().with_state(CELL, 3)
        assert chomper_stop(s, CELL).state_at(CELL) == 3
        s = LevelState().with_state(CELL, 9)
        assert chomper_stop(s, CELL).state_at(CELL) == 0

    def test_kid_in_row_starts_chompers_and_can_die(self) -> None:
        rows = [[E] * 10, [E] * 10, [F] * 10]
        rows[2][5] = Tile.CHOMPER
        lvl = _level(rows, start_col=3, start_row=2)
        g = new_game(lvl)
        g = advance(g, Command())
        assert g.state.state_at((1, 5, 2)) != 0, "al llegar el kid a la fila arrancan"
        # De pie dentro de las cuchillas acaba mordido.
        g = replace(g, kid=replace(g.kid, curr_col=5))
        for _ in range(CHOMPER_SPEED + 2):
            g = advance(g, Command())
            if g.status is GameStatus.LOST_DIED:
                break
        assert g.status is GameStatus.LOST_DIED


class TestGate:
    def test_starts_closed(self) -> None:
        s = LevelState()
        assert not gate_is_passable(s, CELL)
        assert s.state_at(CELL) == int(GatePhase.CLOSED)

    def test_plate_pressed_opens(self) -> None:
        s = LevelState()
        for _ in range(int(GatePhase.OPEN)):
            s = tick_gate(s, CELL, plate_pressed=True)
        assert s.state_at(CELL) >= int(GatePhase.FULLY_OPEN)
        assert gate_is_passable(s, CELL)

    def test_opening_continues_after_release(self) -> None:
        """Canon: pisar la plate un instante basta — la gate termina de
        abrirse sola y queda franqueable ~18 s."""
        s = tick_gate(LevelState(), CELL, plate_pressed=True)
        for _ in range(60):
            s = tick_gate(s, CELL, plate_pressed=False)
        assert s.state_at(CELL) >= int(GatePhase.FULLY_OPEN)
        assert gate_is_passable(s, CELL)
        for _ in range(200):
            s = tick_gate(s, CELL, plate_pressed=False)
        assert gate_is_passable(s, CELL), "sigue franqueable a los ~21 s de pisar"
        for _ in range(30):
            s = tick_gate(s, CELL, plate_pressed=False)
        assert not gate_is_passable(s, CELL)

    def test_plate_release_closes(self) -> None:
        s = LevelState()
        for _ in range(int(GatePhase.OPEN)):
            s = tick_gate(s, CELL, plate_pressed=True)
        assert gate_is_passable(s, CELL)
        for _ in range(int(GatePhase.OPEN)):
            s = tick_gate(s, CELL, plate_pressed=False)
        assert s.state_at(CELL) == int(GatePhase.CLOSED)
        assert not gate_is_passable(s, CELL)

    def test_cannot_exceed_open_limit(self) -> None:
        s = LevelState().with_state(CELL, int(GatePhase.OPEN))
        s = tick_gate(s, CELL, plate_pressed=True)
        assert s.state_at(CELL) <= int(GatePhase.OPEN)
        assert s.state_at(CELL) >= int(GatePhase.FULLY_OPEN)

    def test_cannot_go_below_zero(self) -> None:
        s = LevelState()
        s = tick_gate(s, CELL, plate_pressed=False)
        assert s.state_at(CELL) == 0

    def test_permanent_gate_stays_open(self) -> None:
        s = LevelState().with_gate_permanent(CELL)
        for _ in range(500):
            s = tick_gate(s, CELL)
        assert gate_is_passable(s, CELL)

    def test_debris_on_opener_opens_gate_forever(self) -> None:
        """Una losa que cae sobre un OPENER deja su gate abierta para
        siempre (canon trigger con tiles_14_debris)."""
        rows = [[F] * 10, [E] * 10, [F] * 10]
        rows[0][5] = Tile.LOOSE
        rows[2][5] = Tile.OPENER
        rows[2][8] = Tile.GATE
        lvl = _level(
            rows,
            start_col=1,
            start_row=2,
            doorlinks=(
                DoorLink(
                    plate_room=1, plate_col=5, plate_row=2, gate_room=1, gate_col=8, gate_row=2
                ),
            ),
        )
        g = new_game(lvl)
        g = replace(g, state=loose_press(g.state, (1, 5, 0)))
        for _ in range(80):
            g = advance(g, Command())
        assert (1, 8, 2) in g.state.permanent_gates
        assert (1, 5, 2) in g.state.debris_cells


class TestGateCrush:
    def test_gate_closing_on_the_kid_kills_him(self) -> None:
        """Canon: una gate que baja sobre el kid lo aplasta."""
        empty = (encode_tile(Tile.EMPTY, 0),) * 30
        cells = list(empty)
        for c in range(10):
            cells[2 * 10 + c] = encode_tile(Tile.FLOOR, 0)
        cells[2 * 10 + 5] = encode_tile(Tile.GATE, 0)
        room = Room(id=1, fg=tuple(cells), bg=empty)
        lvl = Level(number=1, name="crush", rooms=(room,), start_room=1, start_col=5, start_row=2)
        game = new_game(lvl)
        state = game.state.with_state((1, 5, 2), GATE_PASSABLE_MIN).with_gate_open((1, 5, 2))
        game = replace(game, state=state)
        for _ in range(3):
            game = advance(game, Command())
        assert game.kid.alive >= 0, "la gate cerrándose sobre el kid debe aplastarlo"
