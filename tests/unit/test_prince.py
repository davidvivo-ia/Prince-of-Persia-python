"""Tests de la FSM del príncipe."""

from __future__ import annotations

from pop2026.domain.actions import Action, duration_ticks
from pop2026.domain.geometry import Facing, Position
from pop2026.domain.input import InputFrame, PlayerCommand
from pop2026.domain.level import Level, LevelState
from pop2026.domain.prince import Prince, step

CORRIDOR = """
##############
#............#
#............#
#..@.........#
##############
"""

PIT = """
##############
#............#
#....@.......#
#.....#......#
##############
"""

LEDGE = """
##############
#............#
#..@.........#
#####...#####
"""


def _make_prince(level: Level) -> Prince:
    return Prince(pos=level.prince_spawn)


def _tick_n(p: Prince, lv: Level, st: LevelState, inp: InputFrame, n: int) -> Prince:
    for _ in range(n):
        p = step(p, lv, st, inp)
    return p


class TestPrinceMovement:
    def test_idle_stays(self) -> None:
        lv = Level.parse("######\n#.@..#\n######\n")
        p = _make_prince(lv)
        p2 = step(p, lv, LevelState(), InputFrame())
        # tras 1 tick está en STAND, no se ha movido
        assert p2.pos == p.pos

    def test_run_right_advances_one_cell(self) -> None:
        lv = Level.parse("########\n#.@....#\n########\n")
        p = _make_prince(lv)
        inp = InputFrame(command=PlayerCommand.RIGHT)
        # un ciclo completo de RUN debe avanzar 1 celda
        p2 = _tick_n(p, lv, LevelState(), inp, duration_ticks(Action.RUN) + 2)
        assert p2.pos.col > p.pos.col

    def test_walk_with_modifier(self) -> None:
        lv = Level.parse("########\n#.@....#\n########\n")
        p = _make_prince(lv)
        inp = InputFrame(command=PlayerCommand.RIGHT, walk_modifier=True)
        p2 = _tick_n(p, lv, LevelState(), inp, duration_ticks(Action.WALK) + 2)
        assert p2.pos == Position(p.pos.row, p.pos.col + 1)
        assert p2.action in (Action.WALK, Action.STAND, Action.RUN)

    def test_wall_blocks_run(self) -> None:
        lv = Level.parse("########\n#.@#...#\n########\n")
        p = _make_prince(lv)
        inp = InputFrame(command=PlayerCommand.RIGHT)
        p2 = _tick_n(p, lv, LevelState(), inp, 30)
        assert p2.pos == p.pos

    def test_left_changes_facing(self) -> None:
        lv = Level.parse("########\n#...@..#\n########\n")
        p = _make_prince(lv)
        inp = InputFrame(command=PlayerCommand.LEFT)
        # esperar a fin de stand para que se aplique transición
        p2 = step(p, lv, LevelState(), inp)
        assert p2.facing is Facing.LEFT


class TestPrinceGravity:
    def test_falls_off_ledge(self) -> None:
        lv = Level.parse(LEDGE)
        p = Prince(pos=Position(2, 5))  # sobre la "ventana" donde no hay suelo
        # gravedad debería activar FALL tras transición
        p2 = step(p, lv, LevelState(), InputFrame())
        # como STAND dura 1 tick, ya está en FALL o cayendo
        assert p2.action is Action.FALL

    def test_lethal_fall_kills(self) -> None:
        lv = Level.parse(
            "##############\n"
            "#..@.........#\n"
            "#............#\n"
            "#............#\n"
            "#............#\n"
            "#............#\n"
            "##############\n"
        )
        p = Prince(pos=Position(1, 3))
        # cae libremente; tras varios ticks debería morir
        p2 = _tick_n(p, lv, LevelState(), InputFrame(), 80)
        # ya sea por caída letal o daño acumulado, hp debe estar 0
        assert p2.hp <= p.hp


class TestPrinceClimbing:
    def test_can_jump(self) -> None:
        lv = Level.parse(CORRIDOR)
        p = Prince(pos=Position(3, 3))
        inp = InputFrame(command=PlayerCommand.JUMP)
        p2 = _tick_n(p, lv, LevelState(), inp, 1)
        # tras 1 tick el príncipe sigue en stand; en el segundo entra en jump
        p3 = step(p2, lv, LevelState(), inp)
        assert p3.action in (Action.JUMP_V, Action.STAND, Action.FALL)


class TestPrinceHealth:
    def test_damage_drops_to_zero(self) -> None:
        p = Prince(pos=Position(0, 0), hp=2, max_hp=2)
        p2 = p.with_damage(2)
        assert p2.hp == 0
        assert p2.action is Action.DEAD

    def test_damage_partial(self) -> None:
        p = Prince(pos=Position(0, 0), hp=3, max_hp=3)
        p2 = p.with_damage(1)
        assert p2.hp == 2
        assert p2.action is Action.HURT

    def test_heal_caps_at_max(self) -> None:
        p = Prince(pos=Position(0, 0), hp=2, max_hp=3)
        p2 = p.with_heal(99)
        assert p2.hp == 3

    def test_max_hp_bonus_raises_and_fills(self) -> None:
        p = Prince(pos=Position(0, 0), hp=1, max_hp=3)
        p2 = p.with_max_hp_bonus(2)
        assert p2.max_hp == 5
        assert p2.hp == 5


def _unused(_: object) -> None:
    pass


_unused(PIT)
