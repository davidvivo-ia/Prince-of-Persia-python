"""Tests del módulo de física continua (cimientos para F-1)."""

from __future__ import annotations

from pop2026.domain.geometry import PositionF, Velocity
from pop2026.domain.level import Level, LevelState
from pop2026.domain.physics import (
    GRAVITY,
    MAX_FALL_VEL,
    BodyState,
    integrate,
    is_grounded,
)

CORRIDOR = Level.parse(
    "####################\n"
    "....................\n"
    "####################\n"
    "..@.................\n"
    "####################\n"
    "####################\n"
)


def _body(x: float, y: float, vx: float = 0.0, vy: float = 0.0) -> BodyState:
    return BodyState(pos=PositionF(x, y), vel=Velocity(vx, vy))


class TestIntegrator:
    def test_falling_body_accelerates(self) -> None:
        # Aire pleno (fila 1 con techo en 0 y suelo en 2): cuerpo poco antes
        # de tocar el suelo, con bastante margen para que la gravedad actúe.
        # Usamos un cuerpo "puntual" (h≈0.2) para no tocar suelo en el primer tick.
        b0 = _body(10.0, 1.2)
        r1 = integrate(b0, CORRIDOR, LevelState(), half_h=0.1)
        assert r1.state.vel.vy > b0.vel.vy
        assert r1.state.pos.y > b0.pos.y

    def test_terminal_velocity(self) -> None:
        b = _body(10.0, 1.2, vy=10.0)
        r = integrate(b, CORRIDOR, LevelState(), half_h=0.1)
        assert r.state.vel.vy <= MAX_FALL_VEL

    def test_horizontal_move_in_open(self) -> None:
        # Fila 3 es aire amplio. Cuerpo estrecho para no rozar techo/suelo.
        b0 = _body(5.0, 3.5, vx=0.1)
        r1 = integrate(b0, CORRIDOR, LevelState(), accel_y=0.0, accel_x=0.0, half_w=0.2, half_h=0.2)
        assert r1.state.pos.x > b0.pos.x
        assert not r1.hit_wall

    def test_horizontal_blocked_by_wall(self) -> None:
        # Cuerpo cerca de la pared derecha (col 19 es '#').
        b0 = _body(18.5, 3.5, vx=2.0)
        r1 = integrate(b0, CORRIDOR, LevelState(), accel_y=0.0, accel_x=0.0, half_w=0.2, half_h=0.2)
        assert r1.hit_wall
        assert r1.state.vel.vx == 0.0

    def test_lands_on_floor(self) -> None:
        # Cuerpo cerca del suelo (fila 4 es solid), cayendo rápido.
        b0 = _body(5.0, 3.7, vy=0.5)
        r1 = integrate(b0, CORRIDOR, LevelState(), half_h=0.2)
        assert r1.hit_ground
        assert r1.state.vel.vy == 0.0


class TestIsGrounded:
    def test_grounded_on_floor(self) -> None:
        # Cuerpo justo sobre fila 4 (suelo), sin solaparse.
        b = _body(5.0, 3.7)
        assert is_grounded(b, CORRIDOR, LevelState(), half_h=0.25)

    def test_not_grounded_in_air(self) -> None:
        b = _body(5.0, 1.2)
        assert not is_grounded(b, CORRIDOR, LevelState(), half_h=0.1)


class TestConstants:
    def test_gravity_is_positive(self) -> None:
        assert GRAVITY > 0

    def test_max_fall_velocity_reasonable(self) -> None:
        # Más rápido que la gravedad por tick pero menos que una celda entera.
        assert GRAVITY < MAX_FALL_VEL < 1.0
