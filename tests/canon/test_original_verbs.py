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
    bot: list[Tile],
    guards: tuple[GuardSpawn, ...] = (),
    mid: list[Tile] | None = None,
    top: list[Tile] | None = None,
) -> Level:
    """Sala de prueba. Geometría canon: el kid pisa la fila 2 (``bot``)."""
    fg = tuple(encode_tile(t, 0) for row in [top or [E] * 10, mid or [E] * 10, bot] for t in row)
    room = Room(id=1, fg=fg, bg=tuple([0] * 30), guards=guards)
    return Level(number=2, name="verbs", rooms=(room,), start_room=1, start_col=2, start_row=2)


_HANGING = (Action.HANG_STRAIGHT, Action.HANG_CLIMB)


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
        fila 2 vacías): el kid de pie en (3,1), de espaldas al hueco
        (mirando a la izquierda), tiene el borde detrás."""
        mid = [F, F, F, F, E, E, E, E, E, E]
        bot = [F] * 10
        bot[4] = E
        bot[5] = E
        lvl = _level(bot, mid=mid)
        return replace(lvl, start_col=3, start_row=1)

    def test_down_with_back_to_edge_hangs(self) -> None:
        """↓ de espaldas al borde (canon): el kid se descuelga y queda
        colgado de la cornisa, con el cuerpo en la celda del hueco una
        fila más abajo, mirando hacia la cornisa."""
        g = new_game(self._ledge_level())
        g = replace(g, kid=replace(g.kid, direction=-1))
        g = advance(g, Command(down=True))
        k = g.kid
        assert k.action in _HANGING
        assert (k.curr_col, k.curr_row) == (4, 2)
        assert k.direction == -1, "cuelga mirando hacia la cornisa"

    def test_down_facing_the_edge_crouches(self) -> None:
        """Mirando al hueco, ↓ es agacharse (no hay borde detrás)."""
        g = new_game(self._ledge_level())
        g = replace(g, kid=replace(g.kid, direction=0))
        g = advance(g, Command(down=True))
        assert g.kid.action is Action.STAND
        assert g.kid.curr_seq_id == int(Seq.CROUCH)
        assert (g.kid.curr_col, g.kid.curr_row) == (3, 1)

    def test_climb_back_up(self) -> None:
        g = new_game(self._ledge_level())
        g = replace(g, kid=replace(g.kid, direction=-1))
        g = advance(g, Command(down=True))
        # SHIFT mantiene el agarre durante la animación; luego ↑ trepa.
        g = _run(g, [Command(shift=True)] * 10 + [Command(up=True)] * 3 + [Command()] * 30)
        assert g.kid.action is Action.STAND
        assert (g.kid.curr_col, g.kid.curr_row) == (3, 1)
        assert g.kid.alive < 0

    def _two_room_level(self, south_floor_row: int) -> Level:
        top = self._ledge_level()
        room1 = replace(top.rooms[0], link_s=2)
        rows = [[E] * 10 for _ in range(3)]
        rows[south_floor_row] = [F] * 10
        fg2 = tuple(encode_tile(t, 0) for row in rows for t in row)
        room2 = Room(id=2, fg=fg2, bg=tuple([0] * 30), link_n=1)
        return replace(top, rooms=(room1, room2))

    def test_release_two_rows_below_ledge_is_safe(self) -> None:
        """Soltarse desde colgado (sin SHIFT): de pie en la fila 1, el
        cuerpo cuelga en la fila 2 (pies a ras de su suelo) y aterriza
        en la sala sur fila 0 — dos filas bajo la cornisa: sin daño. Es
        el truco canon de descolgarse para bajar dos pisos."""
        g = new_game(self._two_room_level(0))
        g = replace(g, kid=replace(g.kid, direction=-1))
        g = advance(g, Command(down=True))
        assert g.kid.action in _HANGING
        g = _run(g, [Command()] * 50)
        assert g.kid.action is Action.STAND
        assert (g.kid.room, g.kid.curr_row) == (2, 0)
        assert g.kid.hp_curr == 3

    def test_release_three_rows_below_ledge_hurts(self) -> None:
        """Tres filas bajo la cornisa (dos bajo el cuerpo colgado) cuesta
        1 HP pero no mata (canon)."""
        g = new_game(self._two_room_level(1))
        g = replace(g, kid=replace(g.kid, direction=-1))
        g = advance(g, Command(down=True))
        g = _run(g, [Command()] * 50)
        assert g.kid.action is Action.STAND
        assert g.kid.alive < 0
        assert (g.kid.room, g.kid.curr_row) == (2, 1)
        assert g.kid.hp_curr == 2

    def test_release_four_rows_below_ledge_kills(self) -> None:
        g = new_game(self._two_room_level(2))
        g = replace(g, kid=replace(g.kid, direction=-1))
        g = advance(g, Command(down=True))
        g = _run(g, [Command()] * 50)
        assert g.kid.alive >= 0

    def test_shift_keeps_hanging(self) -> None:
        g = new_game(self._ledge_level())
        g = replace(g, kid=replace(g.kid, direction=-1))
        g = advance(g, Command(down=True))
        g = _run(g, [Command(shift=True)] * 30)
        assert g.kid.action is Action.HANG_STRAIGHT
        assert (g.kid.curr_col, g.kid.curr_row) == (4, 2)

    def test_climb_down_into_south_room(self) -> None:
        """Descolgarse desde la última fila: el cuerpo pasa a la sala sur."""
        bot = [F, F, F, F, E, E, E, E, E, E]
        room1 = replace(_level(bot).rooms[0], link_s=2)
        fg2 = tuple(encode_tile(t, 0) for row in [[E] * 10, [E] * 10, [F] * 10] for t in row)
        room2 = Room(id=2, fg=fg2, bg=tuple([0] * 30), link_n=1)
        lvl = Level(
            number=2, name="s", rooms=(room1, room2), start_room=1, start_col=3, start_row=2
        )
        g = new_game(lvl)
        g = replace(g, kid=replace(g.kid, direction=-1))
        g = advance(g, Command(down=True))
        assert g.kid.action in _HANGING
        assert (g.kid.room, g.kid.curr_col, g.kid.curr_row) == (2, 4, 0)
        g = _run(g, [Command(shift=True)] * 10 + [Command(up=True)] * 3 + [Command()] * 30)
        assert (g.kid.room, g.kid.curr_col, g.kid.curr_row) == (1, 3, 2)
        assert g.kid.action is Action.STAND


class TestJumpUpGrab:
    def test_up_grabs_ledge_in_front(self) -> None:
        """↑ de pie bajo una cornisa delante-arriba: salta, se agarra y
        con ↑ trepa a ella (canon grab_up_with_floor_behind)."""
        mid = [E, E, E, E, F, F, F, F, F, F]
        g = new_game(_level([F] * 10, mid=mid))
        g = replace(g, kid=replace(g.kid, curr_col=3, direction=0))
        g = advance(g, Command(up=True))
        assert g.kid.action in _HANGING
        assert (g.kid.curr_col, g.kid.curr_row) == (3, 2)
        g = _run(g, [Command(shift=True)] * 8 + [Command(up=True)] * 3 + [Command()] * 30)
        assert g.kid.action is Action.STAND
        assert (g.kid.curr_col, g.kid.curr_row) == (4, 1)

    def test_up_with_back_to_a_shaft_grabs_ledge_above(self) -> None:
        """Canon grab_up_no_floor_behind: de pie en (3,1) de espaldas al
        pozo (col 4), con suelo justo encima (3,0) y aire en (4,0): ↑
        se agarra al borde trasero de (3,0) colgando sobre el pozo, y
        trepa a (3,0). Es cómo se sube un pozo de cornisas en POP1."""
        top = [F, F, F, F, E, E, E, E, E, E]
        mid = [F, F, F, F, E, E, E, E, E, E]
        lvl = replace(_level([F] * 10, mid=mid, top=top), start_col=3, start_row=1)
        g = new_game(lvl)
        g = replace(g, kid=replace(g.kid, direction=-1))
        g = advance(g, Command(up=True))
        assert g.kid.action in _HANGING
        assert (g.kid.curr_col, g.kid.curr_row) == (4, 1)
        assert g.kid.direction == -1
        g = _run(g, [Command(shift=True)] * 8 + [Command(up=True)] * 3 + [Command()] * 30)
        assert g.kid.action is Action.STAND
        assert (g.kid.curr_col, g.kid.curr_row) == (3, 0)

    def test_up_under_a_ceiling_is_a_plain_jump(self) -> None:
        """Con suelo encima y suelo detrás-arriba no hay cornisa: ↑ es un
        salto vertical que no cambia de celda."""
        mid = [F] * 10
        g = new_game(_level([F] * 10, mid=mid))
        g = replace(g, kid=replace(g.kid, curr_col=3, direction=0))
        g = advance(g, Command(up=True))
        assert g.kid.curr_seq_id == int(Seq.STANDING_JUMP)
        g = _run(g, [Command()] * 30)
        assert g.kid.action is Action.STAND
        assert (g.kid.curr_col, g.kid.curr_row) == (3, 2)

    def test_up_grabs_ledge_in_north_room(self) -> None:
        """La cornisa puede estar en la sala norte (fila -1)."""
        fg_n = tuple(
            encode_tile(t, 0)
            for row in [[E] * 10, [E] * 10, [F, F, F, F, E, E, E, E, E, E]]
            for t in row
        )
        north = Room(id=2, fg=fg_n, bg=tuple([0] * 30), link_s=1)
        top = [F, F, F, F, E, E, E, E, E, E]
        south = replace(_level([F] * 10, top=top).rooms[0], link_n=2)
        lvl = Level(
            number=2, name="n", rooms=(south, north), start_room=1, start_col=3, start_row=0
        )
        g = new_game(lvl)
        g = replace(g, kid=replace(g.kid, curr_col=3, curr_row=0, direction=-1))
        # De pie en (3,0) de espaldas al hueco: suelo encima = sala 2 (3,2)
        g = advance(g, Command(up=True))
        assert g.kid.action in _HANGING
        g = _run(g, [Command(shift=True)] * 8 + [Command(up=True)] * 3 + [Command()] * 30)
        assert g.kid.action is Action.STAND
        assert (g.kid.room, g.kid.curr_col, g.kid.curr_row) == (2, 3, 2)


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
