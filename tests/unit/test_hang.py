"""Tests de la mecánica de colgarse (HANG) en la FSM del príncipe."""

from __future__ import annotations

from pop2026.domain.actions import Action, duration_ticks
from pop2026.domain.geometry import Facing, Position
from pop2026.domain.input import InputFrame, PlayerCommand
from pop2026.domain.level import Level, LevelState
from pop2026.domain.prince import Prince, step

# Mapa con una repisa en el centro: prince en row 3 corriendo a la derecha,
# el suelo (fila 4) acaba en col 5 → al cruzar el borde se cuelga.
LEDGE = Level.parse(
    "####################\n"
    "....................\n"
    "....................\n"
    "..@.................\n"
    "######..............\n"
    "####################\n"
)


def _make(action: Action = Action.RUN, *, col: int = 5, row: int = 3) -> Prince:
    return Prince(
        pos=Position(row, col),
        facing=Facing.RIGHT,
        action=action,
        ticks_in_action=duration_ticks(action) - 1,
    )


class TestHangTransition:
    def test_run_off_ledge_grabs(self) -> None:
        # Príncipe a punto de salir del borde (col 5 era el último suelo).
        p = _make(Action.RUN, col=5)
        # Al completar la acción, el efecto mueve a col 6 (sin suelo) → cuelga.
        p2 = step(p, LEDGE, LevelState(), InputFrame(command=PlayerCommand.RIGHT))
        assert p2.action is Action.HANG
        assert p2.pos.col == 6  # ya está en la celda sin suelo

    def test_stand_in_air_falls_not_hangs(self) -> None:
        # Príncipe parado sin facing-back con suelo (caída pura).
        p = Prince(pos=Position(2, 10), facing=Facing.RIGHT, action=Action.STAND)
        p2 = step(p, LEDGE, LevelState(), InputFrame())
        # No hay borde detrás → FALL directo
        assert p2.action is Action.FALL


class TestHangFromState:
    def _hang(self) -> Prince:
        # Crea un prince colgado en col 6 de LEDGE.
        return Prince(
            pos=Position(3, 6),
            facing=Facing.RIGHT,
            action=Action.HANG,
            ticks_in_action=duration_ticks(Action.HANG) - 1,
        )

    def test_up_climbs_back_to_ledge(self) -> None:
        p = self._hang()
        p2 = step(p, LEDGE, LevelState(), InputFrame(command=PlayerCommand.UP))
        # Sube a la celda anterior (col 5) y queda en STAND mirando hacia atrás
        assert p2.pos == Position(3, 5)
        assert p2.action is Action.STAND
        assert p2.facing is Facing.LEFT

    def test_down_drops_to_fall(self) -> None:
        p = self._hang()
        p2 = step(p, LEDGE, LevelState(), InputFrame(command=PlayerCommand.DOWN))
        assert p2.action is Action.FALL

    def test_no_input_keeps_hanging(self) -> None:
        p = self._hang()
        p2 = step(p, LEDGE, LevelState(), InputFrame())
        # Sin tecla, sigue colgado (vuelve a HANG ticks=0)
        assert p2.action is Action.HANG
        assert p2.ticks_in_action == 0
        assert p2.pos == p.pos

    def test_ledge_gone_makes_fall(self) -> None:
        p = self._hang()
        # Borramos la repisa de detrás (col 5, row 4) artificialmente
        # creando un mapa nuevo sin ese suelo.
        broken = Level.parse(
            "####################\n"
            "....................\n"
            "....................\n"
            "..@.................\n"
            "###.................\n"
            "####################\n"
        )
        p2 = step(p, broken, LevelState(), InputFrame())
        assert p2.action is Action.FALL


class TestHangAnimOffset:
    def test_hang_offset_is_below_logical_row(self) -> None:
        from pop2026.domain.anim import offset_for

        _, dy = offset_for(action=Action.HANG, ticks=0, facing_value=1)
        # El cuerpo cuelga: debe quedar visualmente por debajo de la fila lógica
        assert dy > 0.5

    def test_hang_offset_consistent_left(self) -> None:
        from pop2026.domain.anim import offset_for

        dx_r, _ = offset_for(action=Action.HANG, ticks=0, facing_value=1)
        dx_l, _ = offset_for(action=Action.HANG, ticks=0, facing_value=-1)
        # El offset horizontal depende del facing
        assert (dx_r > 0) != (dx_l > 0)


def test_hang_action_has_long_duration() -> None:
    # La duración de HANG debe ser suficiente para que el jugador reaccione.
    from pop2026.domain.actions import duration_ticks as dt

    assert dt(Action.HANG) >= 15  # al menos 0.25 s a 60 Hz
