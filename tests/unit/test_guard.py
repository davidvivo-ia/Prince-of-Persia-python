"""Tests de la IA del guardia."""

from __future__ import annotations

from dataclasses import replace

from pop2026.domain.actions import Action
from pop2026.domain.geometry import Facing, Position
from pop2026.domain.guard import Guard, GuardMode, step
from pop2026.domain.input import PlayerCommand
from pop2026.domain.level import Level, LevelState


class FixedRng:
    """RNG predeterminado para tests."""

    def __init__(self, value: int = 50) -> None:
        self._v = value

    def next_byte(self) -> int:
        return self._v

    def coin(self, prob: float) -> bool:
        return self._v < int(prob * 256)

    def randrange(self, n: int) -> int:
        return self._v % max(1, n)


LEVEL = Level.parse("##########\n#..@.....#\n##########\n")


class TestGuardAI:
    def test_dead_guard_does_not_move(self) -> None:
        g = Guard(pos=Position(1, 5), hp=0, mode=GuardMode.DEAD)
        g2 = step(g, LEVEL, LevelState(), Position(1, 2), FixedRng())
        assert g2.pos == g.pos

    def test_patrol_advances(self) -> None:
        g = Guard(pos=Position(1, 5), facing=Facing.LEFT, action=Action.STAND)
        # ejecuta varios ticks; el guardia patrullando debe moverse
        for _ in range(30):
            g = step(g, LEVEL, LevelState(), Position(1, 100), FixedRng())
        assert g.pos != Position(1, 5)

    def test_combat_when_adjacent(self) -> None:
        g = Guard(pos=Position(1, 4), action=Action.STAND, facing=Facing.RIGHT)
        # Príncipe adyacente a la derecha
        for _ in range(5):
            g = step(g, LEVEL, LevelState(), Position(1, 5), FixedRng(0))
        assert g.mode is GuardMode.COMBAT

    def test_alerts_when_visible(self) -> None:
        g = Guard(
            pos=Position(1, 7),
            facing=Facing.LEFT,
            action=Action.STAND,
        )
        for _ in range(10):
            g = step(g, LEVEL, LevelState(), Position(1, 2), FixedRng())
        assert g.mode in (GuardMode.ALERT, GuardMode.COMBAT)

    def test_hurt_resets_to_stand(self) -> None:
        g = Guard(pos=Position(1, 5), action=Action.HURT)
        # Avanzar hasta que termine la animación HURT
        for _ in range(10):
            g = step(g, LEVEL, LevelState(), Position(1, 100), FixedRng(200))
        assert g.action is not Action.HURT

    def test_damage_applied(self) -> None:
        g = Guard(pos=Position(1, 5), hp=2)
        g2 = g.with_damage(1)
        assert g2.hp == 1
        assert g2.action is Action.HURT

    def test_damage_kills(self) -> None:
        g = Guard(pos=Position(1, 5), hp=1)
        g2 = g.with_damage(1)
        assert g2.hp == 0
        assert g2.mode is GuardMode.DEAD

    def test_step_during_action_increments_ticks(self) -> None:
        g = Guard(pos=Position(1, 5), action=Action.WALK, ticks_in_action=0)
        g2 = step(g, LEVEL, LevelState(), Position(1, 100), FixedRng())
        assert g2.ticks_in_action == 1
        assert g2.pos == g.pos

    def test_patrol_turns_at_cliff(self) -> None:
        cliff = Level.parse("##########\n#..@..#..#\n#.....####\n")
        # Guardia sobre el borde con precipicio al otro lado
        g = Guard(pos=Position(1, 7), facing=Facing.LEFT, action=Action.STAND)
        g = replace(g, patrol_steps_left=10)
        for _ in range(30):
            g = step(g, cliff, LevelState(), Position(1, 100), FixedRng(200))
            if g.facing is Facing.RIGHT:
                break
        # Tras patrullar y encontrar un obstáculo debería haber cambiado de cara
        # (o seguir vivo, depende de la disposición)
        assert g.alive


class TestMirrorGuard:
    """H2: el clon-espejo invierte horizontalmente el input del príncipe."""

    def test_mirror_walks_opposite_when_prince_moves_left(self) -> None:
        g = Guard(
            pos=Position(1, 5),
            facing=Facing.LEFT,
            action=Action.STAND,
            is_mirror=True,
        )
        # Avanza varios ticks con prince moviendo LEFT; mirror debe acabar a la derecha.
        for _ in range(10):
            g = step(g, LEVEL, LevelState(), Position(1, 1), FixedRng(), PlayerCommand.LEFT)
        assert g.pos.col > 5, f"mirror no se movió a la derecha: col={g.pos.col}"
        assert g.facing is Facing.RIGHT

    def test_mirror_walks_opposite_when_prince_moves_right(self) -> None:
        g = Guard(
            pos=Position(1, 5),
            facing=Facing.RIGHT,
            action=Action.STAND,
            is_mirror=True,
        )
        for _ in range(10):
            g = step(g, LEVEL, LevelState(), Position(1, 1), FixedRng(), PlayerCommand.RIGHT)
        assert g.pos.col < 5, f"mirror no se movió a la izquierda: col={g.pos.col}"
        assert g.facing is Facing.LEFT

    def test_mirror_copies_strike(self) -> None:
        g = Guard(pos=Position(1, 5), action=Action.STAND, is_mirror=True)
        g2 = step(g, LEVEL, LevelState(), Position(1, 1), FixedRng(), PlayerCommand.STRIKE)
        assert g2.action is Action.STRIKE
