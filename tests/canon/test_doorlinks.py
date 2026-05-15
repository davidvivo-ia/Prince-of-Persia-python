"""Tests de doorlinks plate→gate específicos.

Cierra la TODO "FASE 3.5: pendiente doorlinks" sustituyendo el modelo
"cualquier plate abre cualquier gate" por mapas explícitos por nivel.
"""

from __future__ import annotations

from dataclasses import replace

from pop2026canon.application.controller import Command
from pop2026canon.application.tick import advance
from pop2026canon.domain.game import new_game
from pop2026canon.domain.level import DoorLink, Event, EventKind, Level
from pop2026canon.domain.levels_canon import LEVEL_6, LEVEL_8, LEVEL_11


class TestDoorLinkModel:
    def test_doorlink_coords(self) -> None:
        link = DoorLink(plate_room=3, plate_col=7, plate_row=1, gate_room=2, gate_col=3, gate_row=1)
        assert link.plate_coord == (3, 7, 1)
        assert link.gate_coord == (2, 3, 1)

    def test_level_gates_for_plate(self) -> None:
        gates = LEVEL_6.gates_for_plate((3, 7, 1))
        assert gates == ((2, 3, 1),)

    def test_level_plates_for_gate(self) -> None:
        plates = LEVEL_6.plates_for_gate((2, 3, 1))
        assert plates == ((3, 7, 1),)

    def test_unmapped_plate_returns_empty(self) -> None:
        # Sin doorlink hacia (9, 9, 9), tupla vacía.
        assert LEVEL_6.gates_for_plate((9, 9, 9)) == ()
        assert LEVEL_6.plates_for_gate((9, 9, 9)) == ()


class TestL6PlateGateLink:
    def test_l6_doorlink_declared(self) -> None:
        assert len(LEVEL_6.doorlinks) == 1
        link = LEVEL_6.doorlinks[0]
        assert link.plate_coord == (3, 7, 1)
        assert link.gate_coord == (2, 3, 1)

    def test_plate_pressed_opens_gate(self) -> None:
        """Al pisar la plate (sala 3 col 7 row 1) la gate (sala 2 col 3
        row 1) acaba abriéndose."""
        game = new_game(LEVEL_6)
        # Coloca el kid pisando la plate.
        game = replace(
            game,
            kid=replace(game.kid, room=3, curr_col=7, curr_row=1),
        )
        # Tick suficiente para que la gate llegue a state OPEN (7).
        for _ in range(20):
            game = advance(game, Command())
        assert (2, 3, 1) in game.state.open_gates


class TestL11SelfRoomDoor:
    def test_l11_doorlink_same_room(self) -> None:
        """L11 tiene plate y gate en la misma sala (sala 5)."""
        assert len(LEVEL_11.doorlinks) == 1
        link = LEVEL_11.doorlinks[0]
        assert link.plate_room == link.gate_room == 5


class TestL8MouseOpensGate:
    def test_l8_mouse_event_opens_unlinked_gate(self) -> None:
        """L8 no tiene plate para la gate; el mouse la fuerza abierta."""
        # La gate está en (6, 2, 1) sin doorlink.
        assert LEVEL_8.plates_for_gate((6, 2, 1)) == ()
        game = new_game(LEVEL_8)
        game = replace(game, kid=replace(game.kid, room=6))
        # Un tick basta — trigger_mouse_appear corre en _trigger_special_chars.
        game = advance(game, Command())
        assert (6, 2, 1) in game.state.open_gates


class TestNoPlateNoGate:
    def test_gate_without_link_stays_closed(self) -> None:
        """Una gate sin plate vinculada y sin mouse no se abre sola."""
        # Construyo un nivel mínimo con gate aislada.
        from pop2026canon.domain.room import Room
        from pop2026canon.domain.tiles import Tile, encode_tile

        empty = (encode_tile(Tile.EMPTY, 0),) * 30
        with_gate = list(empty)
        with_gate[1 * 10 + 5] = encode_tile(Tile.GATE, 0)
        room = Room(id=1, fg=tuple(with_gate), bg=empty)
        lvl = Level(number=1, name="iso", rooms=(room,), start_room=1, start_col=0, start_row=1)
        game = new_game(lvl)
        for _ in range(20):
            game = advance(game, Command())
        assert (1, 5, 1) not in game.state.open_gates

    def test_unlinked_plate_does_not_open_random_gate(self) -> None:
        """Si una plate no está vinculada, otra gate suelta no se abre."""
        from pop2026canon.domain.room import Room
        from pop2026canon.domain.tiles import Tile, encode_tile

        empty = (encode_tile(Tile.EMPTY, 0),) * 30
        cells = list(empty)
        # suelo
        for c in range(10):
            cells[2 * 10 + c] = encode_tile(Tile.FLOOR, 0)
        # plate en (3,1)
        cells[1 * 10 + 3] = encode_tile(Tile.OPENER, 0)
        # gate en (6,1) — sin doorlink
        cells[1 * 10 + 6] = encode_tile(Tile.GATE, 0)
        room = Room(id=1, fg=tuple(cells), bg=empty)
        lvl = Level(
            number=1,
            name="iso",
            rooms=(room,),
            start_room=1,
            start_col=3,
            start_row=1,
        )
        game = new_game(lvl)
        for _ in range(20):
            game = advance(game, Command())
        assert (1, 6, 1) not in game.state.open_gates


class TestEventModelStable:
    def test_event_still_has_extra_field(self) -> None:
        """Sanity check del modelo Event tras añadir DoorLink."""
        e = Event(EventKind.SHADOW_STEP, room=1, extra=43)
        assert e.extra == 43
