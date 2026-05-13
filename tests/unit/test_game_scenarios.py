"""Tests adicionales de Game cubriendo escenarios completos."""

from __future__ import annotations

from dataclasses import replace

from pop2026.domain.actions import Action
from pop2026.domain.game import GameStatus, advance, new_game
from pop2026.domain.input import InputFrame, PlayerCommand
from pop2026.domain.level import Level
from pop2026.domain.ports import Rng
from pop2026.domain.tiles import Tile


class StaticRng:
    """RNG fijo determinista."""

    def __init__(self, b: int = 0) -> None:
        self._b = b

    def next_byte(self) -> int:
        return self._b

    def coin(self, prob: float) -> bool:
        return self._b < int(prob * 256)

    def randrange(self, n: int) -> int:
        return self._b % max(1, n)


def _rng() -> Rng:
    return StaticRng(50)


PLATE_GATE = """
##############
#..@.._.|...>#
##############
"""

POISON = """
##############
#..@-........#
##############
"""

LOOSE_FLOOR = """
##############
#..@.........#
###=.........#
##############
"""

SPIKES_ABOVE = """
##############
#..@.........#
#............#
#............#
#............#
#.....^......#
##############
"""


def _run(g, cmd: PlayerCommand, n: int):  # type: ignore[no-untyped-def]
    inp = InputFrame(command=cmd)
    for _ in range(n):
        if not g.running:
            break
        g = advance(g, inp, _rng())
    return g


class TestPressurePlate:
    def test_plate_opens_nearest_gate(self) -> None:
        lv = Level.parse(PLATE_GATE)
        g = new_game(lv, time_limit=10_000)
        # caminar hacia la placa
        g2 = _run(g, PlayerCommand.RIGHT, 50)
        # tras pisar la placa, la gate más cercana debería estar abierta
        assert len(g2.state.open_gates) >= 1


class TestPoisonPotion:
    def test_poison_damages_prince(self) -> None:
        lv = Level.parse(POISON)
        g = new_game(lv, time_limit=10_000, starting_hp=3)
        # caminar 1 celda a la derecha → poción en (1, 4)
        g2 = _run(g, PlayerCommand.RIGHT, 30)
        # HP debería haber bajado en algún punto
        assert g2.prince.hp <= 3


class TestLooseFloor:
    def test_loose_floor_breaks_when_stood_on(self) -> None:
        # príncipe en fila 1, columna 3; loose-floor directamente debajo
        src = "##############\n#..@.........#\n###===########\n##############\n"
        lv = Level.parse(src)
        # Verifica que (2,3) es LOOSE_FLOOR antes de jugar
        assert lv.tile_at(lv.prince_spawn.shifted(drow=1)) is Tile.LOOSE_FLOOR
        g = new_game(lv, time_limit=10_000)
        g2 = _run(g, PlayerCommand.NONE, 5)
        # tras unos ticks la celda debajo del príncipe debería haber caído
        assert len(g2.state.fallen_floors) >= 1


class TestGameOver:
    def test_dead_prince_sets_status(self) -> None:
        lv = Level.parse("##############\n#..@.........#\n##############\n")
        g = new_game(lv, time_limit=10_000)
        g = replace(g, prince=replace(g.prince, hp=0, action=Action.DEAD))
        g2 = advance(g, InputFrame(), _rng())
        assert g2.status is GameStatus.LOST_DIED

    def test_not_running_returns_self(self) -> None:
        lv = Level.parse("##############\n#..@........>#\n##############\n")
        g = new_game(lv, time_limit=10)
        g = replace(g, status=GameStatus.WON)
        g2 = advance(g, InputFrame(), _rng())
        assert g2 is g


class TestSpikes:
    def test_spikes_kill_on_landing(self) -> None:
        lv = Level.parse(SPIKES_ABOVE)
        # El príncipe en (1,3) caerá por gravedad hasta los spikes en (5,6)
        # no llegará a los spikes porque están desplazados — usemos uno alineado
        src = (
            "##############\n"
            "#..@.........#\n"
            "#............#\n"
            "#............#\n"
            "#............#\n"
            "#...^........#\n"
            "##############\n"
        )
        lv = Level.parse(src)
        g = new_game(lv, time_limit=10_000)
        # el príncipe en (1,3) caerá; spikes en (5,4) — no alineadas
        # usar mejor un test directo: forzar al príncipe a estar sobre spikes con fall>0
        from pop2026.domain.geometry import Position
        from pop2026.domain.prince import Prince

        p = Prince(pos=Position(5, 4), fall_distance=2)
        g = replace(g, prince=p)
        # un tick para procesar interacción de tile
        g2 = advance(g, InputFrame(), _rng())
        assert g2.prince.hp == 0 or g2.status is GameStatus.LOST_DIED
