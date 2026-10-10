"""Máquinas de estado de las trampas, calcadas de ``seg007.c`` (SDLPoP).

Cada trampa guarda su ``modifier`` canon en ``LevelState.tile_states``:

- **Losa suelta** (``animate_loose``): al pisarla (o al golpearla desde
  abajo saltando) el modifier pasa a 1 y sube un punto por tick; en 11
  cae — el kid ya no tiene que estar encima. Si la "sacude" otra losa
  al estrellarse en su fila (``do_knock``) sólo tiembla (0x80..0x84).
  La losa que cae es un *mob* (``FallingTile``) que acelera +3 por tick
  hasta 29, arrastra las losas sueltas que atraviesa, y al estrellarse
  contra el primer suelo deja escombros (``debris_cells``), sacude las
  losas de esa fila, aplasta al kid si le cae encima y, si cae sobre un
  botón, lo acciona (un OPENER queda abierto para siempre).
- **Pinchos** (``animate_spike``): recogidos (0) hasta que el kid se
  acerca por encima; entonces salen (1..4), se quedan fuera 15 ticks
  (0x8F..0x80), se recogen (6..8) y vuelven a 0. Un kid que corre
  mientras salen muere; aterrizar de un salto o de una caída con los
  pinchos fuera o saliendo, también. Andar con ellos fuera es seguro.
  0xFF = pinchos con un cuerpo clavado (inactivos).
- **Cuchillas** (``animate_chomper``): arrancan cuando el kid llega a su
  fila (``start_chompers``: 15, 12, 9, 6, 13, 10... ticks de desfase
  entre cuchillas vecinas) y ciclan 1..15; muerden en el frame 2. Se
  paran al irse el kid de la fila. 0x80 = sangre.
- **Gates** (``animate_door``): ver ``tick_gate``.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import IntEnum

from pop2026canon.domain.constants import (
    CHOMPER_SPEED,
    LOOSE_FLOOR_DELAY,
    TILE_SIZE_Y,
)
from pop2026canon.domain.tiles import Tile

# ---------------------------------------------------------------------------
# Estado dinámico del nivel
# ---------------------------------------------------------------------------

TileCoord = tuple[int, int, int]
"""(room, col, row). Identifica univocamente una celda en el level."""


@dataclass(frozen=True, slots=True)
class FallingTile:
    """Una losa suelta cayendo (canon ``mob_type``)."""

    room: int
    col: int
    row: int
    y: int = 0
    """Altura dentro de la fila (0 arriba)."""
    speed: int = 0
    hit_kid: bool = False
    """Ya golpeó al kid (una losa sólo golpea una vez)."""


@dataclass(frozen=True, slots=True)
class LevelState:
    """Estado dinámico del nivel: trampas, gates abiertas, potions
    consumidas, etc. Inmutable — cada tick produce un nuevo `LevelState`.
    """

    tile_states: tuple[tuple[TileCoord, int], ...] = ()
    """Modifier canon por celda: (coord, state). Sin entrada = 0."""

    consumed_potions: frozenset[TileCoord] = field(default_factory=frozenset)
    """Pociones bebidas (y espada recogida) — el tile queda inactivo."""

    fallen_floors: frozenset[TileCoord] = field(default_factory=frozenset)
    """Losas sueltas que ya cayeron — la celda es un agujero."""

    open_gates: frozenset[TileCoord] = field(default_factory=frozenset)
    """Gates lo bastante abiertas para pasar (canon ``modifier >> 2 >= 6``)."""

    opening_gates: frozenset[TileCoord] = field(default_factory=frozenset)
    """Gates cuya apertura está en marcha (canon: el *trob* de apertura
    sigue aunque el kid deje la plate)."""

    permanent_gates: frozenset[TileCoord] = field(default_factory=frozenset)
    """Gates abiertas para siempre (canon modifier 0xFF: una losa cayó
    sobre su OPENER, o alguien murió encima)."""

    falling_tiles: tuple[FallingTile, ...] = ()
    """Losas en caída libre (mobs)."""

    debris_cells: frozenset[TileCoord] = field(default_factory=frozenset)
    """Celdas donde se estrelló una losa: escombros encima (los pinchos
    de esa celda quedan inutilizados; un OPENER deja de ser botón)."""

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
        """Marca un loose floor como caído (agujero persistente)."""
        return replace(self, fallen_floors=self.fallen_floors | {coord})

    def with_gate_open(self, coord: TileCoord) -> LevelState:
        return replace(self, open_gates=self.open_gates | {coord})

    def with_gate_closed(self, coord: TileCoord) -> LevelState:
        return replace(self, open_gates=self.open_gates - {coord})

    def with_gate_opening(self, coord: TileCoord, opening: bool) -> LevelState:
        if opening:
            return replace(self, opening_gates=self.opening_gates | {coord})
        return replace(self, opening_gates=self.opening_gates - {coord})

    def with_gate_permanent(self, coord: TileCoord) -> LevelState:
        return replace(
            self,
            permanent_gates=self.permanent_gates | {coord},
            open_gates=self.open_gates | {coord},
        ).with_state(coord, int(GatePhase.OPEN))

    def with_potion_consumed(self, coord: TileCoord) -> LevelState:
        return replace(self, consumed_potions=self.consumed_potions | {coord})

    def with_debris(self, coord: TileCoord) -> LevelState:
        return replace(self, debris_cells=self.debris_cells | {coord})


# ---------------------------------------------------------------------------
# Losa suelta — canon animate_loose / make_loose_fall / loose_make_shake
# ---------------------------------------------------------------------------

LOOSE_SHAKE: int = 0x80
"""Bit "sólo tiembla" del modifier de una losa suelta."""


class LooseState(IntEnum):
    IDLE = 0
    CRACKING = 1  # 1..LOOSE_FLOOR_DELAY-1: cuenta atrás hasta caer


def loose_press(state: LevelState, coord: TileCoord) -> LevelState:
    """Canon ``make_loose_fall(1)``: algo pisa (o golpea desde abajo) la
    losa. Si estaba quieta o sólo temblando, arranca la cuenta atrás."""
    if coord in state.fallen_floors:
        return state
    current = state.state_at(coord)
    if current == 0 or current & LOOSE_SHAKE:
        return state.with_state(coord, 1)
    return state


def loose_shake(state: LevelState, coord: TileCoord) -> LevelState:
    """Canon ``loose_make_shake``: una losa estrellada en la fila la
    sacude (sin caer)."""
    if coord in state.fallen_floors or state.state_at(coord) != 0:
        return state
    return state.with_state(coord, LOOSE_SHAKE)


def tick_loose(state: LevelState, coord: TileCoord) -> tuple[LevelState, bool]:
    """Canon ``animate_loose``: avanza un tick la losa en ``coord``.
    Devuelve ``(estado, cayó_ahora)``."""
    current = state.state_at(coord)
    if current == 0 or coord in state.fallen_floors:
        return state, False
    current += 1
    if current & LOOSE_SHAKE:
        if current >= LOOSE_SHAKE + 4:
            return state.with_state(coord, 0), False
        return state.with_state(coord, current), False
    if current >= LOOSE_FLOOR_DELAY:
        new_state = state.with_floor_fallen(coord).with_state(coord, 0)
        mob = FallingTile(room=coord[0], col=coord[1], row=coord[2])
        return replace(new_state, falling_tiles=(*new_state.falling_tiles, mob)), True
    return state.with_state(coord, current), False


FALLING_TILE_ACCEL: int = 3
FALLING_TILE_MAX_SPEED: int = 29
"""Canon ``move_loose``: +3 por tick hasta 29."""


def is_loose_shaking(state: LevelState, coord: TileCoord) -> bool:
    return state.state_at(coord) != 0 and coord not in state.fallen_floors


# ---------------------------------------------------------------------------
# Pinchos — canon animate_spike / start_anim_spike / is_spike_harmful
# ---------------------------------------------------------------------------

SPIKE_OUT: int = 0x8F
"""Pinchos del todo fuera: cuentan atrás 15 ticks hasta recogerse."""

SPIKE_DISABLED: int = 0xFF
"""Pinchos con un cuerpo clavado: ya no se mueven."""


def spike_trigger(state: LevelState, coord: TileCoord) -> LevelState:
    """Canon ``start_anim_spike``: el kid se acerca por encima."""
    if coord in state.debris_cells:
        return state
    current = state.state_at(coord)
    if current == 0:
        return state.with_state(coord, 1)
    if current & 0x80 and current != SPIKE_DISABLED:
        return state.with_state(coord, SPIKE_OUT)
    return state


def tick_spike(state: LevelState, coord: TileCoord) -> LevelState:
    """Canon ``animate_spike``: 1..4 saliendo → 0x8F..0x80 fuera →
    6..8 recogiéndose → 0."""
    current = state.state_at(coord)
    if current in (0, SPIKE_DISABLED):
        return state
    if current & 0x80:
        current -= 1
        if current & 0x7F == 0:
            current = 6
        return state.with_state(coord, current)
    current += 1
    if current == 5:
        current = SPIKE_OUT
    elif current == 9:
        current = 0
    return state.with_state(coord, current)


def spike_harm(state_value: int) -> int:
    """Canon ``is_spike_harmful``: 0 inofensivos (recogidos, recogiéndose
    o con cuerpo), 1 fuera, 2 saliendo."""
    if state_value in (0, SPIKE_DISABLED):
        return 0
    if state_value & 0x80:
        return 1
    if state_value < 5:
        return 2
    return 0


def spike_kills(state: LevelState, coord: TileCoord, *, running: bool, landing: bool) -> bool:
    """Canon ``check_spiked`` + ``land``: corriendo (o arrancando un
    salto con carrerilla) sólo matan mientras SALEN; aterrizando de un
    salto o de una caída, siempre que estén fuera o saliendo."""
    if coord in state.debris_cells:
        return False
    harm = spike_harm(state.state_at(coord))
    if harm == 2 and running:
        return True
    return landing and harm != 0


def spike_kills_on_land(fall_y: int) -> bool:
    """Compatibilidad: aterrizar con velocidad sobre pinchos activos mata."""
    return fall_y > 0


def spike_disable(state: LevelState, coord: TileCoord) -> LevelState:
    """Canon ``spiked``: el cuerpo queda clavado; los pinchos se paran."""
    return state.with_state(coord, SPIKE_DISABLED)


# ---------------------------------------------------------------------------
# Cuchillas — canon animate_chomper / start_chompers
# ---------------------------------------------------------------------------

CHOMPER_BLOOD: int = 0x80
CHOMPER_BITE_FRAME: int = 2
"""Frame en el que las cuchillas están cerradas y muerden."""


class ChomperPhase(IntEnum):
    """Fases visibles de las cuchillas a partir del frame canon 1..15."""

    OPEN = 0
    CLOSING = 1
    CLOSED = 2
    OPENING = 3


def chomper_phase(frame: int) -> ChomperPhase:
    f = frame & 0x7F
    if f == 0:
        return ChomperPhase.OPEN
    if f == 1:
        return ChomperPhase.CLOSING
    if f == CHOMPER_BITE_FRAME:
        return ChomperPhase.CLOSED
    if f <= 5:
        return ChomperPhase.OPENING
    return ChomperPhase.OPEN


def next_chomper_timing(timing: int) -> int:
    """Canon: 15 → 12 → 9 → 6 → 13 → 10 → 7 → 14 → 11 → 8 → ..."""
    timing -= 3
    if timing < 6:
        timing += 10
    return timing


def chomper_start(state: LevelState, coord: TileCoord, timing: int) -> LevelState:
    """Canon ``start_anim_chomper``: sólo si está parada (0) o abierta
    (frame >= 6); conserva la sangre."""
    current = state.state_at(coord)
    frame = current & 0x7F
    if frame == 0 or frame >= 6:
        return state.with_state(coord, (current & CHOMPER_BLOOD) | timing)
    return state


def start_chompers(
    state: LevelState, room_id: int, row: int, chomper_cols: list[int]
) -> LevelState:
    """Canon ``start_chompers``: arranca las cuchillas de la fila del kid
    con desfases decrecientes de izquierda a derecha."""
    timing = CHOMPER_SPEED
    for col in chomper_cols:
        coord = (room_id, col, row)
        before = state.state_at(coord) & 0x7F
        if before == 0 or before >= 6:
            state = chomper_start(state, coord, timing)
            timing = next_chomper_timing(timing)
    return state


def tick_chomper(state: LevelState, coord: TileCoord) -> LevelState:
    """Canon ``animate_chomper``: frame 1..15 cíclico (si está activa)."""
    current = state.state_at(coord)
    frame = current & 0x7F
    if frame == 0:
        return state
    frame += 1
    if frame > CHOMPER_SPEED:
        frame = 1
    return state.with_state(coord, (current & CHOMPER_BLOOD) | frame)


def chomper_stop(state: LevelState, coord: TileCoord) -> LevelState:
    """Canon: al irse el kid de la fila, la cuchilla se para abierta
    (sólo a partir del frame 6: si está mordiendo termina el mordisco)."""
    current = state.state_at(coord)
    if (current & 0x7F) >= 6:
        return state.with_state(coord, current & CHOMPER_BLOOD)
    return state


def chomper_is_lethal(state: LevelState, coord: TileCoord) -> bool:
    """``True`` en el frame 2: las cuchillas cerradas."""
    return (state.state_at(coord) & 0x7F) == CHOMPER_BITE_FRAME


def chomper_blood(state: LevelState, coord: TileCoord) -> LevelState:
    return state.with_state(coord, state.state_at(coord) | CHOMPER_BLOOD)


# ---------------------------------------------------------------------------
# Gate — canon animate_door
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
    if coord in state.permanent_gates:
        return state
    if state.state_at(coord) >= int(GatePhase.FULLY_OPEN):
        return state.with_state(coord, int(GatePhase.OPEN)).with_gate_opening(coord, False)
    return state.with_gate_opening(coord, True)


def trigger_gate_close(state: LevelState, coord: TileCoord) -> LevelState:
    """Canon ``trigger_gate`` con un CLOSER: cierre rápido."""
    if coord in state.permanent_gates:
        return state
    return state.with_state(coord, 0).with_gate_opening(coord, False).with_gate_closed(coord)


def trigger_gate_permanent(state: LevelState, coord: TileCoord) -> LevelState:
    """Canon ``trigger_gate`` con escombros (``tiles_14_debris``): la gate
    queda abierta para siempre (modifier 0xFF)."""
    return state.with_gate_permanent(coord)


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
    if coord in state.permanent_gates:
        return state.with_state(coord, int(GatePhase.OPEN)).with_gate_open(coord)
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
    """Resuelve si una trampa mata al char que ATERRIZA en ``coord``.

    - SPIKE: letal si los pinchos están fuera o saliendo.
    - CHOMPER: letal en el frame de mordisco.
    """
    if tile is Tile.SPIKE:
        return spike_kills(state, coord, running=False, landing=fall_y > 0)
    if tile is Tile.CHOMPER:
        return chomper_is_lethal(state, coord)
    return False


ROW_HEIGHT: int = TILE_SIZE_Y
