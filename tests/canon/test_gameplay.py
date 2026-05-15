"""Tests de gameplay real: combate bidireccional + trampas letales + items.

Estos tests simulan ticks reales del game loop, no piezas aisladas.
Validan que el juego se comporta como POP1: los guards atacan al kid,
el kid puede contraatacar, los chompers/spikes/loose matan, las gates
bloquean, las espadas se recogen, etc.
"""

from __future__ import annotations

from dataclasses import replace

from pop2026canon.application.controller import Command
from pop2026canon.application.tick import advance
from pop2026canon.domain.actions import SwordStatus
from pop2026canon.domain.chars import CharId
from pop2026canon.domain.game import GameStatus, new_game
from pop2026canon.domain.levels_canon import (
    LEVEL_1,
    LEVEL_2,
    LEVEL_4,
    LEVEL_8,
)
from pop2026canon.domain.tiles import Tile


def _find_first_tile(level, tile: Tile) -> tuple[int, int, int] | None:  # type: ignore[no-untyped-def]
    for room in level.rooms:
        for r in range(3):
            for c in range(10):
                if Tile(room.fg[r * 10 + c] & 0x1F) is tile:
                    return (room.id, c, r)
    return None


class TestGuardAttacksKid:
    def test_guard_kills_passive_kid_in_same_room(self) -> None:
        """Un guard adyacente al kid acaba matándolo si el kid no responde."""
        g = new_game(LEVEL_1)
        guard = next(c for c in g.others if c.charid is CharId.GUARD)
        g = replace(
            g,
            kid=replace(
                g.kid,
                room=guard.room,
                curr_col=guard.curr_col - 2,
                curr_row=guard.curr_row,
                direction=0,
            ),
        )
        for _ in range(60):
            g = advance(g, Command())
            if g.status is GameStatus.LOST_DIED:
                break
        assert g.status is GameStatus.LOST_DIED, (
            f"Guard no mató al kid en 60 ticks (kid hp={g.kid.hp_curr})"
        )

    def test_guard_advances_toward_kid(self) -> None:
        """Un guard distante avanza hacia el kid en pocos ticks."""
        g = new_game(LEVEL_1)
        guard = next(c for c in g.others if c.charid is CharId.GUARD)
        g = replace(
            g,
            kid=replace(g.kid, room=guard.room, curr_col=1, curr_row=guard.curr_row),
        )
        initial_col = guard.curr_col
        for _ in range(40):
            g = advance(g, Command())
        new_guard = next(c for c in g.others if c.charid is CharId.GUARD)
        # El guard se acercó (movido al menos 1 col hacia el kid en col 1)
        assert new_guard.curr_col < initial_col, (
            f"Guard no avanzó: pasó de col {initial_col} a {new_guard.curr_col}"
        )


class TestKidAttacksGuard:
    def test_kid_with_sword_kills_guard(self) -> None:
        """El kid con espada y pulsando strike repetido mata al guard adyacente."""
        g = new_game(LEVEL_1)
        target_guard = next(c for c in g.others if c.charid is CharId.GUARD)
        target_room = target_guard.room
        g = replace(
            g,
            kid=replace(
                g.kid,
                room=target_room,
                curr_col=target_guard.curr_col - 1,
                curr_row=target_guard.curr_row,
                sword=SwordStatus.DRAWN,
                hp_max=100,
                hp_curr=100,
                direction=0,
            ),
        )
        for tk in range(200):
            cmd = Command(strike=(tk % 8 == 0))
            g = advance(g, cmd)
            # ¿El guard de target_room sigue vivo?
            same_room_guards = [
                c
                for c in g.others
                if c.charid is CharId.GUARD and c.room == target_room and c.alive < 0
            ]
            if not same_room_guards:
                return  # éxito
        same_room_guards = [
            c
            for c in g.others
            if c.charid is CharId.GUARD and c.room == target_room and c.alive < 0
        ]
        assert not same_room_guards, "Kid no consiguió matar al guard de la sala objetivo"

    def test_kid_without_sword_cannot_strike(self) -> None:
        """Sin espada, el strike del kid no hace daño."""
        from pop2026canon.domain.actions import Direction, Seq
        from pop2026canon.domain.chars import Char
        from pop2026canon.domain.combat import resolve_combat

        kid = Char(
            charid=CharId.KID,
            room=1,
            curr_col=3,
            curr_row=1,
            direction=int(Direction.RIGHT),
            sword=SwordStatus.SHEATHED,
            frame=166,  # en strike window
            curr_seq_id=int(Seq.STRIKE),
        )
        guard = Char(
            charid=CharId.GUARD,
            room=1,
            curr_col=4,
            curr_row=1,
            direction=int(Direction.LEFT),
            hp_curr=3,
            hp_max=3,
        )
        # Aún con frame en strike_window, sin sword DRAWN el ataque debería
        # neutralizarse. Mi resolve_combat actual permite el hit
        # independiente del sword status del kid — comprobamos eso aquí
        # como documentación del comportamiento.
        result = resolve_combat(kid, guard)
        # El kid con sword sheathed canónicamente NO hace daño.
        # Si este test falla, hay que actualizar resolve_combat para
        # exigir attacker.sword == DRAWN.
        assert result.guard.hp_curr == 3, (
            "Kid sin espada no debería poder hacer daño — fix en combat.py"
        )


class TestTrapsLethal:
    def test_chomper_kills_kid_when_closed(self) -> None:
        coord = _find_first_tile(LEVEL_2, Tile.CHOMPER)
        assert coord is not None, "L2 sin chompers"
        g = new_game(LEVEL_2)
        g = replace(
            g,
            kid=replace(g.kid, room=coord[0], curr_col=coord[1], curr_row=coord[2]),
        )
        for _ in range(30):
            g = advance(g, Command())
            if g.status is GameStatus.LOST_DIED:
                break
        assert g.status is GameStatus.LOST_DIED, "Kid no muere pisando chomper"

    def test_spike_kills_kid_on_fall(self) -> None:
        from pop2026canon.domain.actions import Action

        coord = _find_first_tile(LEVEL_4, Tile.SPIKE)
        assert coord is not None, "L4 sin spikes"
        g = new_game(LEVEL_4)
        g = replace(
            g,
            kid=replace(
                g.kid,
                room=coord[0],
                curr_col=coord[1],
                curr_row=coord[2],
                action=Action.IN_FREEFALL,
                fall_y=20,
            ),
        )
        g = advance(g, Command())
        assert g.status is GameStatus.LOST_DIED, "Kid no muere aterrizando sobre spike"

    def test_loose_floor_eventually_falls(self) -> None:
        from pop2026canon.domain.traps import LOOSE_FLOOR_DELAY, LevelState, tick_loose

        state = LevelState()
        coord = (1, 5, 2)
        fell = False
        for _ in range(LOOSE_FLOOR_DELAY + 2):
            state, fell_now = tick_loose(state, coord, kid_pressing=True)
            if fell_now:
                fell = True
                break
        assert fell, f"Loose floor no cayó tras {LOOSE_FLOOR_DELAY} ticks de presión"
        assert coord in state.fallen_floors


class TestGatesBlock:
    def test_closed_gate_is_solid(self) -> None:
        from pop2026canon.domain.physics import is_solid_at

        # Busca gate
        coord = _find_first_tile(LEVEL_2, Tile.GATE)
        assert coord is not None, "L2 sin gates"
        room = LEVEL_2.room(coord[0])
        assert is_solid_at(room, coord[1], coord[2]), "Gate cerrada no es sólida"


class TestItemPickup:
    def test_kid_picks_up_sword(self) -> None:
        coord = _find_first_tile(LEVEL_1, Tile.SWORD)
        assert coord is not None, "L1 sin sword"
        g = new_game(LEVEL_1)
        g = replace(
            g,
            kid=replace(g.kid, room=coord[0], curr_col=coord[1], curr_row=coord[2]),
        )
        g = advance(g, Command())
        assert g.kid.sword == SwordStatus.DRAWN, "Kid no recogió la sword"
        assert g.flags.sword_picked, "flag sword_picked no se activó"


class TestMouseOpensGate:
    def test_mouse_opens_l8_gate(self) -> None:
        """L8: cuando el kid entra en la sala del mouse, la gate del exit
        se abre completamente."""
        from pop2026canon.domain.level import EventKind

        ev = next(e for e in LEVEL_8.events if e.kind is EventKind.MOUSE_APPEAR)
        g = new_game(LEVEL_8)
        g = replace(g, kid=replace(g.kid, room=ev.room))
        g = advance(g, Command())
        # Una gate de la sala debe estar abierta
        opened_in_room = [c for c in g.state.open_gates if c[0] == ev.room]
        assert opened_in_room, f"Mouse no abrió ninguna gate en sala {ev.room}"
