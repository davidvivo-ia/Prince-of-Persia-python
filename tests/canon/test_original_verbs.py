"""Verbos del original: salto largo desde parado, paso cuidadoso,
descolgarse de un borde y ponerse en guardia solo ante un guard."""

from __future__ import annotations

from dataclasses import replace

from pop2026canon.application.controller import Command, apply_input
from pop2026canon.application.tick import advance
from pop2026canon.domain.actions import Action, Seq, SwordStatus
from pop2026canon.domain.chars import Char, CharId, GuardSpawn
from pop2026canon.domain.game import new_game
from pop2026canon.domain.level import Level
from pop2026canon.domain.room import Room
from pop2026canon.domain.tiles import Tile, encode_tile

E, F = Tile.EMPTY, Tile.FLOOR


def _level(
    bot: list[Tile], guards: tuple[GuardSpawn, ...] = (), mid: list[Tile] | None = None
) -> Level:
    """Sala de prueba. Geometría canon: el kid pisa la fila 2 (``bot``)."""
    fg = tuple(encode_tile(t, 0) for row in [[E] * 10, mid or [E] * 10, bot] for t in row)
    room = Room(id=1, fg=fg, bg=tuple([0] * 30), guards=guards)
    return Level(number=2, name="verbs", rooms=(room,), start_room=1, start_col=2, start_row=2)


def _run(game, cmds):  # type: ignore[no-untyped-def]
    for c in cmds:
        game = advance(game, c)
    return game


class TestStandingJumpForward:
    def test_up_plus_direction_jumps_two_cells(self) -> None:
        """↑+→ desde parado libra un pit de 2 celdas (canon)."""
        bot = [F] * 10
        bot[4] = E
        bot[5] = E
        g = new_game(_level(bot))
        g = replace(g, kid=replace(g.kid, curr_col=3, direction=0))
        g = _run(g, [Command(up=True, right=True)] + [Command()] * 30)
        assert g.kid.alive < 0, "El salto largo desde parado debe librar 2 celdas"
        assert g.kid.curr_col >= 6
        assert g.kid.curr_row == 2
        assert g.kid.action is Action.STAND

    def test_up_alone_is_vertical(self) -> None:
        kid = Char(charid=CharId.KID, room=1, curr_col=3, curr_row=2, direction=0)
        new = apply_input(kid, Command(up=True))
        assert new.curr_seq_id == int(Seq.STANDING_JUMP)


class TestCarefulStep:
    def test_step_moves_one_cell(self) -> None:
        g = new_game(_level([F] * 10))
        g = replace(g, kid=replace(g.kid, curr_col=3, direction=0))
        g = _run(g, [Command(right=True, shift=True)] * 2 + [Command()] * 12)
        assert g.kid.curr_col == 4
        assert g.kid.action is Action.STAND

    def test_step_stops_at_the_edge(self) -> None:
        """SHIFT+→ al borde de un pit NO cae (canon: te detienes)."""
        bot = [F] * 10
        bot[4] = E
        g = new_game(_level(bot))
        g = replace(g, kid=replace(g.kid, curr_col=3, direction=0))
        g = _run(g, [Command(right=True, shift=True)] * 10 + [Command()] * 10)
        assert g.kid.curr_col == 3
        assert g.kid.alive < 0


class TestClimbDown:
    def _ledge_level(self) -> Level:
        """Cornisa en la fila 1 (cols 0-3) sobre un pit (cols 4-5 de la
        fila 2 vacías): el kid de pie en (3,1) tiene el borde delante."""
        mid = [F, F, F, F, E, E, E, E, E, E]
        bot = [F] * 10
        bot[4] = E
        bot[5] = E
        lvl = _level(bot, mid=mid)
        return replace(lvl, start_col=3, start_row=1)

    def test_down_shift_at_edge_hangs(self) -> None:
        """↓+SHIFT en un borde: el kid queda colgado de la cornisa, con el
        cuerpo en la celda de delante una fila más abajo."""
        g = new_game(self._ledge_level())
        g = replace(g, kid=replace(g.kid, direction=0))
        g = advance(g, Command(down=True, shift=True))
        k = g.kid
        assert k.action is Action.HANG_STRAIGHT
        assert (k.curr_col, k.curr_row) == (4, 2)
        assert k.direction == -1, "cuelga mirando hacia la cornisa"

    def test_climb_back_up(self) -> None:
        g = new_game(self._ledge_level())
        g = replace(g, kid=replace(g.kid, direction=0))
        g = advance(g, Command(down=True, shift=True))
        g = _run(g, [Command(up=True)] * 3 + [Command()] * 30)
        assert g.kid.action is Action.STAND
        assert (g.kid.curr_col, g.kid.curr_row) == (3, 1)
        assert g.kid.alive < 0

    def test_release_drops_safely(self) -> None:
        """Soltarse desde colgado cae un piso (a la sala de abajo) sin daño."""
        top = self._ledge_level()
        room1 = replace(top.rooms[0], link_s=2)
        fg2 = tuple(encode_tile(t, 0) for row in [[E] * 10, [E] * 10, [F] * 10] for t in row)
        room2 = Room(id=2, fg=fg2, bg=tuple([0] * 30), link_n=1)
        lvl = replace(top, rooms=(room1, room2))
        g = new_game(lvl)
        g = replace(g, kid=replace(g.kid, direction=0))
        g = advance(g, Command(down=True, shift=True))
        assert g.kid.action is Action.HANG_STRAIGHT
        g = _run(g, [Command(down=True)] * 2 + [Command()] * 40)
        assert g.kid.action is Action.STAND
        assert (g.kid.room, g.kid.curr_row) == (2, 2)
        assert g.kid.hp_curr == 3


class TestAutoEngarde:
    def test_sword_drawn_when_guard_near(self) -> None:
        guards = (GuardSpawn(col=6, row=2, direction=-1, skill=0),)
        g = new_game(_level([F] * 10, guards), has_sword=True)
        g = replace(g, kid=replace(g.kid, curr_col=3, sword=SwordStatus.SHEATHED))
        g = advance(g, Command())
        assert g.kid.sword == SwordStatus.DRAWN
        assert g.kid.curr_seq_id == int(Seq.ENGARDE)
        assert g.kid.direction == 0, "mira hacia el guard"

    def test_no_auto_draw_without_sword(self) -> None:
        guards = (GuardSpawn(col=6, row=2, direction=-1, skill=0),)
        g = new_game(_level([F] * 10, guards), has_sword=False)
        g = replace(g, kid=replace(g.kid, curr_col=3))
        g = advance(g, Command())
        assert g.kid.sword == SwordStatus.SHEATHED
