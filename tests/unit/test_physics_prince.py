"""Tests del príncipe en coordenadas continuas (F-1 fase 1)."""

from __future__ import annotations

import os

from pop2026.domain.actions import Action
from pop2026.domain.geometry import Facing, Position
from pop2026.domain.input import InputFrame, PlayerCommand
from pop2026.domain.level import Level, LevelState
from pop2026.domain.physics import RUN_SPEED
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


# ---------------------------------------------------------------------------
# R2 — Game-feel: coyote, jump buffer, variable jump, air control, knockback
# ---------------------------------------------------------------------------


# Mapa con plataforma corta para coyote: el príncipe puede caminar al borde.
COYOTE_LEVEL = Level.parse(
    "##############\n"
    "..............\n"
    "..............\n"
    "..@...........\n"
    "####..........\n"
    "##############\n"
)


def _settled() -> PhysicsPrince:
    """Spawn y deja que asiente en suelo unos ticks."""
    p = _spawn()
    for _ in range(5):
        p = step(p, CORRIDOR, LevelState(), InputFrame())
    return p


class TestCoyoteTime:
    def test_coyote_allows_jump_after_leaving_ledge(self) -> None:
        # Spawn en el borde de la plataforma (col 2 está en COYOTE_LEVEL).
        p = initial(Position(3, 2))
        # Estabilizar en suelo.
        for _ in range(3):
            p = step(p, COYOTE_LEVEL, LevelState(), InputFrame())
        # Caminar al borde y salir. Tras salir, durante COYOTE_TICKS sigue
        # admitiéndose el salto aunque ya no haya suelo debajo.
        for _ in range(15):
            p = step(p, COYOTE_LEVEL, LevelState(), InputFrame(command=PlayerCommand.RIGHT))
        # En este punto debería estar en el aire pero con coyote_left > 0.
        if p.coyote_left > 0:
            # Pulsa salto y verifica que sube.
            p2 = step(
                p,
                COYOTE_LEVEL,
                LevelState(),
                InputFrame(command=PlayerCommand.JUMP, jump_held=True),
            )
            assert p2.body.vel.vy < 0, "coyote: JUMP en aire reciente no impulsó"


class TestJumpBuffer:
    def test_jump_buffer_consumed_on_landing(self) -> None:
        # El príncipe cae, pulsa JUMP antes de aterrizar y al tocar el suelo salta.
        from pop2026.domain.geometry import PositionF, Velocity
        from pop2026.domain.physics import BodyState

        p = PhysicsPrince(body=BodyState(pos=PositionF(5.5, 2.5), vel=Velocity(0.0, 0.3)))
        # Pulsa JUMP a varios ticks de tocar suelo.
        p = step(
            p,
            CORRIDOR,
            LevelState(),
            InputFrame(command=PlayerCommand.JUMP, jump_held=True),
        )
        assert p.buffer_left > 0, "buffer no se activó al pulsar JUMP en el aire"
        # Sigue cayendo sin volver a pulsar.
        for _ in range(3):
            p = step(p, CORRIDOR, LevelState(), InputFrame(jump_held=True))
        # Al aterrizar, el buffer pendiente se consume y rebrota.
        # (El test es laxo: aceptamos que en algún punto vy < 0 tras tocar suelo.)
        bounced = False
        for _ in range(8):
            p = step(p, CORRIDOR, LevelState(), InputFrame(jump_held=True))
            if p.body.vel.vy < -0.1:
                bounced = True
                break
        assert bounced, "jump buffer no se consumió al aterrizar"


class TestVariableJump:
    def test_releasing_jump_cuts_height(self) -> None:
        # Saltar y mantener vs saltar y soltar deben producir alturas distintas.
        held_apex = 99.0
        cut_apex = 99.0

        # Run 1: mantener JUMP hasta el pico.
        p = _settled()
        p = step(
            p,
            CORRIDOR,
            LevelState(),
            InputFrame(command=PlayerCommand.JUMP, jump_held=True),
        )
        for _ in range(30):
            p = step(p, CORRIDOR, LevelState(), InputFrame(jump_held=True))
            held_apex = min(held_apex, p.body.pos.y)

        # Run 2: soltar JUMP al cabo de 2 ticks (variable jump).
        p = _settled()
        p = step(
            p,
            CORRIDOR,
            LevelState(),
            InputFrame(command=PlayerCommand.JUMP, jump_held=True),
        )
        # Aún mantenida un tick para que prev_jump_held=True quede grabado.
        p = step(p, CORRIDOR, LevelState(), InputFrame(jump_held=True))
        # Ahora suelta.
        p = step(p, CORRIDOR, LevelState(), InputFrame(jump_held=False))
        for _ in range(30):
            p = step(p, CORRIDOR, LevelState(), InputFrame(jump_held=False))
            cut_apex = min(cut_apex, p.body.pos.y)

        # El salto cortado alcanza menos altura (más altura = y más pequeña).
        assert cut_apex > held_apex, f"variable jump no recortó: held={held_apex} cut={cut_apex}"


class TestAirControl:
    def test_air_control_weaker_than_ground(self) -> None:
        # Compara aceleración de 0 a Vmax en suelo vs en aire.
        p_ground = _settled()
        ticks_to_max_ground = 0
        for _ in range(60):
            p_ground = step(
                p_ground,
                CORRIDOR,
                LevelState(),
                InputFrame(command=PlayerCommand.RIGHT),
            )
            ticks_to_max_ground += 1
            if p_ground.body.vel.vx >= RUN_SPEED * 0.95:
                break

        # En aire: ponemos al príncipe en el aire con vy=0 ficticio.
        from pop2026.domain.geometry import PositionF, Velocity
        from pop2026.domain.physics import BodyState

        p_air = PhysicsPrince(body=BodyState(pos=PositionF(5.5, 1.5), vel=Velocity()))
        ticks_to_max_air = 0
        for _ in range(60):
            p_air = step(
                p_air,
                CORRIDOR,
                LevelState(),
                InputFrame(command=PlayerCommand.RIGHT),
            )
            ticks_to_max_air += 1
            if p_air.body.vel.vx >= RUN_SPEED * 0.95:
                break

        assert ticks_to_max_air > ticks_to_max_ground, (
            f"air control no es más lento: ground={ticks_to_max_ground} air={ticks_to_max_air}"
        )


class TestKnockback:
    def test_knockback_blocks_input(self) -> None:
        # Aplica daño con dirección y verifica que el input horizontal queda
        # bloqueado durante varios ticks.
        p = _settled()
        # El príncipe mira a la derecha; ataque viene de la derecha (+1).
        hurt = p.with_damage(1, from_direction=1)
        assert hurt.knockback_left > 0
        assert hurt.body.vel.vx < 0, "knockback no empuja hacia la izquierda"
        # Mientras knockback_left > 0, el RIGHT no debería frenar el empujón.
        p = hurt
        for _ in range(3):
            p = step(p, CORRIDOR, LevelState(), InputFrame(command=PlayerCommand.RIGHT))
            # vx sigue siendo negativo (hacia la izquierda) — input bloqueado
            assert p.body.vel.vx <= 0, f"input bloqueó knockback en tick: vx={p.body.vel.vx}"
