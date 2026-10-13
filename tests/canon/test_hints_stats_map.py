"""Pistas contextuales, estadísticas de nivel y mapa de salas."""

from __future__ import annotations

from dataclasses import replace

from pop2026canon.application.controller import Command
from pop2026canon.application.hints import HINTS, detect_hint
from pop2026canon.application.stats import LevelStats
from pop2026canon.application.tick import advance
from pop2026canon.domain.actions import SwordStatus
from pop2026canon.domain.chars import GuardSpawn
from pop2026canon.domain.game import new_game
from pop2026canon.domain.level import Level
from pop2026canon.domain.levels_canon import CANON_LEVELS
from pop2026canon.domain.room import Room
from pop2026canon.domain.tiles import Tile, encode_tile
from pop2026canon.presentation.minimap import room_layout

E, F = Tile.EMPTY, Tile.FLOOR


def _level(bot: list[Tile], mid: list[Tile] | None = None, guards=()) -> Level:  # type: ignore[no-untyped-def]
    fg = tuple(encode_tile(t, 0) for row in [[E] * 10, mid or [E] * 10, bot] for t in row)
    room = Room(id=1, fg=fg, bg=tuple([0] * 30), guards=guards)
    return Level(number=2, name="h", rooms=(room,), start_room=1, start_col=3, start_row=2)


class TestHints:
    def test_every_hint_has_pad_text(self) -> None:
        for h in HINTS.values():
            assert h.text
            assert h.pad_text

    def test_jump_up_under_ledge(self) -> None:
        mid = [E, E, E, E, F, F, F, F, F, F]
        g = new_game(_level([F] * 10, mid=mid))
        g = replace(g, kid=replace(g.kid, direction=0))
        assert detect_hint(g) == "jump_up"

    def test_short_gap_suggests_jump(self) -> None:
        bot = [F] * 10
        bot[4] = E
        g = new_game(_level(bot))
        g = replace(g, kid=replace(g.kid, direction=0))
        assert detect_hint(g) == "running_jump"

    def test_wide_pit_suggests_edge_moves(self) -> None:
        bot = [F, F, F, F, E, E, E, E, E, E]
        g = new_game(_level(bot))
        g = replace(g, kid=replace(g.kid, direction=0))
        assert detect_hint(g) == "edge"

    def test_guard_in_sight(self) -> None:
        guards = (GuardSpawn(col=6, row=2, direction=-1, skill=0),)
        armed = new_game(_level([F] * 10, guards=guards), has_sword=True)
        assert detect_hint(armed) == "duel"
        unarmed = new_game(_level([F] * 10, guards=guards), has_sword=False)
        assert detect_hint(unarmed) == "unarmed"

    def test_death_suggests_rewind(self) -> None:
        g = new_game(_level([F] * 10))
        assert detect_hint(g, died=True) == "rewind"

    def test_nothing_on_plain_floor(self) -> None:
        g = new_game(_level([F] * 10))
        assert detect_hint(g) is None


class TestStats:
    def test_counts_time_rooms_and_kills(self) -> None:
        guards = (GuardSpawn(col=5, row=2, direction=-1, skill=0),)
        g = new_game(_level([F] * 10, guards=guards), has_sword=True)
        st = LevelStats(level=2)
        st.start(g)
        prev = g
        killed = replace(
            g,
            others=(replace(g.others[0], alive=0, hp_curr=0),),
            kid=replace(g.kid, sword=SwordStatus.DRAWN),
        )
        st.observe(prev, killed)
        assert st.guards_defeated == 1
        assert st.ticks == 1
        assert 1 in st.visited
        for _ in range(23):
            st.observe(killed, advance(killed, Command()))
        assert st.seconds == 2
        assert st.clock == "0:02"


class TestRoomLayout:
    def test_all_rooms_placed_without_overlap(self) -> None:
        for level in CANON_LEVELS:
            layout = room_layout(level)
            assert level.start_room in layout
            cells = list(layout.values())
            assert len(cells) == len(set(cells)), f"L{level.number}: salas solapadas"

    def test_links_are_adjacent_when_possible(self) -> None:
        level = CANON_LEVELS[0]
        layout = room_layout(level)
        start = level.room(level.start_room)
        if start.link_e:
            sx, sy = layout[level.start_room]
            ex, ey = layout[start.link_e]
            assert ey == sy
            assert ex > sx
