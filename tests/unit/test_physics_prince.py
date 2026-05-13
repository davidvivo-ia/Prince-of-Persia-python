"""Tests del príncipe en coordenadas continuas (F-1 fase 1)."""

from __future__ import annotations

import os

from pop2026.domain.actions import Action
from pop2026.domain.geometry import Facing, Position
from pop2026.domain.input import InputFrame, PlayerCommand
from pop2026.domain.level import Level, LevelState
from pop2026.domain.physics_prince import (
    PhysicsPrince,
    initial,
    is_v2_enabled,
    step,
)

CORRIDOR = Level.parse(
    "####################\n"
    "....................\n"
    "....................\n"
    "..@.................\n"
    "####################\n"
    "####################\n"
)


def _spawn() -> PhysicsPrince:
    return initial(Position(3, 2))


class TestSpawn:
    def test_initial_has_zero_velocity(self) -> None:
        p = _spawn()
        assert p.body.vel.vx == 0.0
        assert p.body.vel.vy == 0.0

    def test_initial_pos_centered_in_cell(self) -> None:
        p = _spawn()
        assert p.body.pos.x == 2.5
        assert p.body.pos.y == 3.5

    def test_initial_alive(self) -> None:
        assert _spawn().alive


class TestStepIntegration:
    def test_no_input_falls_to_floor(self) -> None:
        # Lo soltamos en aire (fila 1, columna 5).
        from pop2026.domain.geometry import PositionF, Velocity
        from pop2026.domain.physics import BodyState

        p = PhysicsPrince(body=BodyState(pos=PositionF(5.5, 1.5), vel=Velocity()))
        # Algunos ticks de caída
        for _ in range(120):
            p = step(p, CORRIDOR, LevelState(), InputFrame())
        # Tras 2 segundos debe estar en el suelo (fila ~3.5 / parado).
        assert p.body.pos.y > 3.0
        assert abs(p.body.vel.vy) < 0.1

    def test_right_input_moves_right(self) -> None:
        p = _spawn()
        for _ in range(30):
            p = step(p, CORRIDOR, LevelState(), InputFrame(command=PlayerCommand.RIGHT))
        assert p.body.pos.x > 2.5
        assert p.facing is Facing.RIGHT

    def test_left_input_flips_facing(self) -> None:
        p = _spawn()
        p = step(p, CORRIDOR, LevelState(), InputFrame(command=PlayerCommand.LEFT))
        assert p.facing is Facing.LEFT

    def test_jump_lifts_when_grounded(self) -> None:
        p = _spawn()
        # Primero deja que asiente en el suelo
        for _ in range(5):
            p = step(p, CORRIDOR, LevelState(), InputFrame())
        p = step(p, CORRIDOR, LevelState(), InputFrame(command=PlayerCommand.JUMP))
        assert p.body.vel.vy < 0  # vy negativa = arriba

    def test_dead_does_not_move(self) -> None:
        from dataclasses import replace

        p = _spawn()
        p = replace(p, action=Action.DEAD)
        p2 = step(p, CORRIDOR, LevelState(), InputFrame(command=PlayerCommand.RIGHT))
        assert p2.body.pos == p.body.pos


class TestActionSelection:
    def test_run_action_when_moving(self) -> None:
        p = _spawn()
        # Asentar primero
        for _ in range(5):
            p = step(p, CORRIDOR, LevelState(), InputFrame())
        for _ in range(8):
            p = step(p, CORRIDOR, LevelState(), InputFrame(command=PlayerCommand.RIGHT))
        # Tras avanzar varios ticks, debe estar en RUN
        assert p.action in (Action.RUN, Action.WALK)

    def test_walk_modifier_picks_walk(self) -> None:
        p = _spawn()
        for _ in range(5):
            p = step(p, CORRIDOR, LevelState(), InputFrame())
        for _ in range(8):
            p = step(
                p,
                CORRIDOR,
                LevelState(),
                InputFrame(command=PlayerCommand.RIGHT, walk_modifier=True),
            )
        assert p.action is Action.WALK


class TestFeatureFlag:
    def test_disabled_by_default(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        monkeypatch.delenv("POP2026_PHYSICS_V2", raising=False)
        assert not is_v2_enabled()

    def test_truthy_values_enable(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        for val in ("1", "true", "yes", "on", "TRUE"):
            monkeypatch.setenv("POP2026_PHYSICS_V2", val)
            assert is_v2_enabled(), f"valor truthy {val!r} no activa el flag"

    def test_falsy_values_keep_disabled(self, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        for val in ("0", "false", "no", "off", ""):
            monkeypatch.setenv("POP2026_PHYSICS_V2", val)
            assert not is_v2_enabled(), f"valor falsy {val!r} activa el flag"


def test_module_import_is_side_effect_free() -> None:
    # Importar el módulo no debe leer la env var en tiempo de import.
    os.environ.pop("POP2026_PHYSICS_V2", None)
    import importlib

    from pop2026.domain import physics_prince

    importlib.reload(physics_prince)
    assert not physics_prince.is_v2_enabled()
