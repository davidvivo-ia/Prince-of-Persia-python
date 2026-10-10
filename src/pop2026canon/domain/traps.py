"""Máquinas de estado de las trampas canónicas.

Cuatro trampas con timing replicado:

- **Loose floor**: 11 ticks de presión consecutiva → cae (delay canon).
- **Chomper**: ciclo de 15 ticks (4 estados visibles + cerrado letal).
- **Spike**: siempre extendido por defecto; letal al pisar con vy alta.
- **Gate**: 8 estados (0 cerrado..7 abierto) animado por plate/closer.

Los estados se guardan en ``LevelState.tile_states: dict[(room, col, row), int]``.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import IntEnum

from pop2026canon.domain.constants import (
    CHOMPER_SPEED,
    LOOSE_FLOOR_DELAY,
)
from pop2026canon.domain.tiles import Tile

# ---------------------------------------------------------------------------
# Estado dinámico del nivel
# ---------------------------------------------------------------------------

TileCoord = tuple[int, int, int]
"""(room, col, row). Identifica univocamente una celda en el level."""


@dataclass(frozen=True, slots=True)
class LevelState:
    """Estado dinámico del nivel: trampas, gates abiertas, potions
    consumidas, etc.

    Inmutable — cada tick produce un nuevo `LevelState`.
    """

    tile_states: tuple[tuple[TileCoord, int], ...] = ()
    """Estado por celda: (coord, state). Sin entrada = estado 0 (idle)."""

    consumed_potions: frozenset[TileCoord] = field(default_factory=frozenset)
    """Pociones bebidas — el tile queda invisible/inactivo."""

    fallen_floors: frozenset[TileCoord] = field(default_factory=frozenset)
    """Loose floors que ya cayeron — el tile pasa a DEBRIS."""

    open_gates: frozenset[TileCoord] = field(default_factory=frozenset)
    """Gates lo bastante abiertas para pasar (canon ``modifier >> 2 >= 6``)."""

    opening_gates: frozenset[TileCoord] = field(default_factory=frozenset)
    """Gates cuya apertura está en marcha (canon: el *trob* de apertura
    sigue aunque el kid deje la plate)."""

    def state_at(self, coord: TileCoord) -> int:
        """Devuelve el state actual de la trampa en `coord`, o 0 si no hay."""
        for c, s in self.tile_states:
            if c == coord:
                return s
        return 0

    def with_state(self, coord: TileCoord, new_state: int) -> LevelState:
        """Set/reset del state en `coord`. Si new_state == 0, lo elimina."""
        other = tuple((c, s) for c, s in self.tile_states if c != coord)
        new_states = (*other, (coord, new_state)) if new_state != 0 else other
        return replace(self, tile_states=new_states)

    def with_floor_fallen(self, coord: TileCoord) -> LevelState:
        """Marca un loose floor como caído (DEBRIS persistente)."""
        return replace(self, fallen_floors=self.fallen_floors | {coord})

    def with_gate_open(self, coord: TileCoord) -> LevelState:
        return replace(self, open_gates=self.open_gates | {coord})

    def with_gate_closed(self, coord: TileCoord) -> LevelState:
        return replace(self, open_gates=self.open_gates - {coord})

    def with_gate_opening(self, coord: TileCoord, opening: bool) -> LevelState:
        if opening:
            return replace(self, opening_gates=self.opening_gates | {coord})
        return replace(self, opening_gates=self.opening_gates - {coord})

    def with_potion_consumed(self, coord: TileCoord) -> LevelState:
        return replace(self, consumed_potions=self.consumed_potions | {coord})


# ---------------------------------------------------------------------------
# Loose floor — state machine (delay canon = 11)
# ---------------------------------------------------------------------------


class LooseState(IntEnum):
    IDLE = 0
    CRACKING = 1  # estados 1..LOOSE_FLOOR_DELAY representan el shake
    # FALLEN = LOOSE_FLOOR_DELAY + 1 indica que ya cayó


def tick_loose(
    state: LevelState,
    coord: TileCoord,
    kid_pressing: bool,
) -> tuple[LevelState, bool]:
    """Avanza el state de un loose floor en `coord`.

    Si el kid lleva pisando consecutivamente `LOOSE_FLOOR_DELAY` ticks,
    el tile cae. Si deja de pisar, el contador se reinicia (a 0).

    Returns:
        ``(new_state, fell_now)`` — `fell_now=True` si cayó en este tick.
    """
    if coord in state.fallen_floors:
        return state, False

    current = state.state_at(coord)

    if not kid_pressing:
        # Reset si no hay presión
        if current != 0:
            return state.with_state(coord, 0), False
        return state, False

    new_value = current + 1
    if new_value >= LOOSE_FLOOR_DELAY:
        # Cayó
        new_state = state.with_floor_fallen(coord)
        new_state = new_state.with_state(coord, 0)
        return new_state, True

    return state.with_state(coord, new_value), False


# ---------------------------------------------------------------------------
# Chomper — ciclo de 15 ticks
# ---------------------------------------------------------------------------


class ChomperPhase(IntEnum):
    """Estados visibles del chomper en un ciclo de `CHOMPER_SPEED=15` ticks."""

    OPEN = 0
    CLOSING_1 = 1
    CLOSING_2 = 2
    CLOSED = 3  # ¡letal!
    OPENING_1 = 4
    OPENING_2 = 5


# Reparto canónico del ciclo de 15 ticks entre fases.
# OPEN (1-7, 7 ticks) → CLOSING (8-9, 2) → CLOSED (10-12, 3 letales) → OPENING (13-15, 3)
def chomper_phase(tick_in_cycle: int) -> ChomperPhase:
    """Devuelve la fase del chomper según su tick en el ciclo (0..14)."""
    t = tick_in_cycle % CHOMPER_SPEED
    if t < 7:
        return ChomperPhase.OPEN
    if t < 9:
        return ChomperPhase.CLOSING_1 if t == 7 else ChomperPhase.CLOSING_2
    if t < 12:
        return ChomperPhase.CLOSED
    return ChomperPhase.OPENING_1 if t == 12 else ChomperPhase.OPENING_2


def tick_chomper(state: LevelState, coord: TileCoord) -> LevelState:
    """Avanza el state del chomper (0..14) un tick."""
    current = state.state_at(coord)
    new_value = (current + 1) % CHOMPER_SPEED
    return state.with_state(coord, new_value)


def chomper_is_lethal(state: LevelState, coord: TileCoord) -> bool:
    """``True`` si el chomper está en fase CLOSED — letal al pisarlo."""
    return chomper_phase(state.state_at(coord)) is ChomperPhase.CLOSED


# ---------------------------------------------------------------------------
# Spike — siempre extendido por defecto, letal con caída
# ---------------------------------------------------------------------------

SPIKE_LETHAL_FALL_Y: int = 10
"""Si el kid aterriza con fall_y >= 10, el spike instakill."""


def spike_kills_on_land(fall_y: int) -> bool:
    """``True`` si aterrizar con esta velocidad sobre spike mata."""
    return fall_y >= SPIKE_LETHAL_FALL_Y


# ---------------------------------------------------------------------------
# Gate — 8 estados (cerrado 0 → abierto 7)
# ---------------------------------------------------------------------------


class GatePhase(IntEnum):
    CLOSED = 0
    FULLY_OPEN = 188
    """Canon: a partir de 188 la gate está del todo arriba."""
    OPEN = 238
    """Canon ``animate_door``: al terminar de abrir, el modifier salta a 238
    y baja 1 por frame; sigue del todo abierta hasta 188 y es
    franqueable mientras ``modifier >> 2 >= 6`` (≥ 24)."""


GATE_OPEN_SPEED: int = 4
"""Unidades de apertura por tick (canon ``door_delta[1]`` = 4): 47 ticks
(~4 s) hasta estar del todo abierta."""

GATE_CLOSE_SPEED: int = 1
"""Unidades de cierre por tick (canon ``door_delta[0]`` = -1): desde 238
la gate tarda 214 ticks (~18 s) en dejar de ser franqueable. Es el
margen canon para cruzar desde una plate a varias salas (L3)."""

GATE_PASSABLE_MIN: int = 24
"""Por debajo de este state la gate ya no deja pasar el cuerpo (canon:
``modifier >> 2 < 6``)."""


def trigger_gate_open(state: LevelState, coord: TileCoord) -> LevelState:
    """Canon ``trigger_gate`` con un OPENER: si ya está del todo abierta
    se recarga a 238 (sigue abierta un rato más); si no, arranca la
    apertura, que continúa sola aunque se suelte la plate."""
    if state.state_at(coord) >= int(GatePhase.FULLY_OPEN):
        return state.with_state(coord, int(GatePhase.OPEN)).with_gate_opening(coord, False)
    return state.with_gate_opening(coord, True)


def trigger_gate_close(state: LevelState, coord: TileCoord) -> LevelState:
    """Canon ``trigger_gate`` con un CLOSER: cierre rápido."""
    return state.with_state(coord, 0).with_gate_opening(coord, False).with_gate_closed(coord)


def tick_gate(
    state: LevelState,
    coord: TileCoord,
    plate_pressed: bool = False,
) -> LevelState:
    """Avanza un tick el estado de una gate (canon ``animate_door``).

    - ``plate_pressed`` dispara la apertura (:func:`trigger_gate_open`).
    - Abriéndose: +4 por tick; al llegar a 188 salta a 238 y empieza a
      bajar sola.
    - Si no, baja 1 por tick hasta 0.

    La gate es atravesable mientras ``state >= GATE_PASSABLE_MIN`` —
    el set ``open_gates`` de :class:`LevelState` refleja eso.
    """
    if plate_pressed:
        state = trigger_gate_open(state, coord)
    current = state.state_at(coord)
    if coord in state.opening_gates:
        new_value = current + GATE_OPEN_SPEED
        if new_value >= int(GatePhase.FULLY_OPEN):
            new_value = int(GatePhase.OPEN)
            state = state.with_gate_opening(coord, False)
    else:
        new_value = max(int(GatePhase.CLOSED), current - GATE_CLOSE_SPEED)

    new_state = state.with_state(coord, new_value)
    if new_value >= GATE_PASSABLE_MIN:
        return new_state.with_gate_open(coord)
    return new_state.with_gate_closed(coord)


def gate_is_passable(state: LevelState, coord: TileCoord) -> bool:
    """``True`` si la gate está lo bastante abierta para pasar."""
    return coord in state.open_gates


def gate_phase(state: LevelState, coord: TileCoord) -> int:
    """Altura visual 0..7 de la gate en `coord` (para el renderer)."""
    return (state.state_at(coord) * 7) // int(GatePhase.OPEN)


# ---------------------------------------------------------------------------
# Detección genérica de trampa letal
# ---------------------------------------------------------------------------


def trap_kills(
    state: LevelState,
    coord: TileCoord,
    tile: Tile,
    fall_y: int = 0,
) -> bool:
    """Resuelve si una trampa mata al char en la celda `coord`.

    - SPIKE: letal si fall_y >= SPIKE_LETHAL_FALL_Y
    - CHOMPER: letal si está en fase CLOSED
    - Resto: no letal por sí mismo (loose, gate gestionados aparte)
    """
    if tile is Tile.SPIKE:
        return spike_kills_on_land(fall_y)
    if tile is Tile.CHOMPER:
        return chomper_is_lethal(state, coord)
    return False
