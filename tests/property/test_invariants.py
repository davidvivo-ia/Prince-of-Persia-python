"""Tests de propiedad (hypothesis) sobre invariantes del dominio."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from pop2026.domain.actions import Action
from pop2026.domain.geometry import Facing, Position
from pop2026.domain.input import InputFrame, PlayerCommand
from pop2026.domain.level import Level, LevelState
from pop2026.domain.prince import Prince, step

SIMPLE_LEVEL = Level.parse(
    "######################\n"
    "#..@.................#\n"
    "#....................#\n"
    "######################\n"
)


@st.composite
def commands(draw: st.DrawFn) -> InputFrame:
    cmd = draw(st.sampled_from(list(PlayerCommand)))
    walk = draw(st.booleans())
    return InputFrame(command=cmd, walk_modifier=walk)


@given(commands_seq=st.lists(commands(), min_size=1, max_size=40))
@settings(max_examples=50, deadline=None)
def test_hp_never_exceeds_max(commands_seq: list[InputFrame]) -> None:
    p = Prince(pos=Position(2, 3), hp=3, max_hp=3, has_sword=True)
    for inp in commands_seq:
        p = step(p, SIMPLE_LEVEL, LevelState(), inp)
        assert p.hp <= p.max_hp
        assert p.hp >= 0


@given(commands_seq=st.lists(commands(), min_size=1, max_size=80))
@settings(max_examples=50, deadline=None)
def test_position_stays_in_bounds(commands_seq: list[InputFrame]) -> None:
    p = Prince(pos=Position(2, 10), hp=3, max_hp=3)
    for inp in commands_seq:
        p = step(p, SIMPLE_LEVEL, LevelState(), inp)
        assert 0 <= p.pos.row < SIMPLE_LEVEL.rows
        assert 0 <= p.pos.col < SIMPLE_LEVEL.cols


@given(commands_seq=st.lists(commands(), min_size=1, max_size=80))
@settings(max_examples=50, deadline=None)
def test_dead_prince_stays_dead(commands_seq: list[InputFrame]) -> None:
    p = Prince(pos=Position(2, 5), hp=0, max_hp=3, action=Action.DEAD)
    for inp in commands_seq:
        p2 = step(p, SIMPLE_LEVEL, LevelState(), inp)
        assert p2.action is Action.DEAD
        assert p2.hp == 0
        p = p2


@given(facing=st.sampled_from([Facing.LEFT, Facing.RIGHT]))
def test_facing_opposite_involutive(facing: Facing) -> None:
    assert facing.opposite().opposite() is facing
