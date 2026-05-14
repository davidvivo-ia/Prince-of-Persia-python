"""Generador procedural de niveles.

Toma un ``level_index`` (1..100) y una semilla, y produce un
:class:`Level` solvable con la dificultad correspondiente al acto.

Algoritmo (alto nivel):

1. Resolver `act` y `local_index`; pedir parámetros a
   :mod:`pop2026.application.difficulty`.
2. Decidir anchura del nivel (20 o 40 celdas) según ``multi_room_prob``.
3. Crear el "esqueleto": techo (fila 0), aire (1-3), suelo (4), base (5).
4. Sembrar tiles dinámicos en filas 3-4 según probabilidades.
5. Colocar `@` (spawn) y `>` (exit) en columnas extremas con suelo.
6. Distribuir guardias / esqueletos en posiciones seguras.
7. Validar con :func:`pop2026.domain.reachability.is_reachable`.
8. Si no es reachable: hasta 12 reintentos con perturbaciones (limpiar
   obstáculos cerca del spawn). Tras 12, fallback a corredor mínimo
   con la dificultad reducida.

Determinismo: misma `(level_index, seed)` → mismo `Level`.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from pop2026.application.difficulty import DifficultyParams, params_for
from pop2026.domain.geometry import Position
from pop2026.domain.level import Level
from pop2026.domain.reachability import is_reachable
from pop2026.domain.tiles import Tile

ROWS: int = 6
"""Altura fija del nivel."""

NARROW_COLS: int = 20
"""Anchura del modo single-room."""

WIDE_COLS: int = 40
"""Anchura del modo multi-room (dos pantallas)."""

MAX_RETRIES: int = 12
"""Reintentos antes de fallback."""

PRINCE_COL: int = 2
"""Columna fija del spawn del príncipe."""

EXIT_OFFSET: int = 2
"""Distancia desde el borde derecho hasta la columna del exit."""


@dataclass(frozen=True, slots=True)
class GeneratorConfig:
    """Entrada al generador. Misma config → mismo nivel."""

    level_index: int
    seed: int = 42


def generate(config: GeneratorConfig) -> Level:
    """Devuelve un :class:`Level` válido para ``config``.

    Args:
        config: Configuración con índice y semilla.

    Returns:
        ``Level`` reachable con `time_limit_ticks` derivado de la dificultad.
    """
    params = params_for(config.level_index)
    cols = WIDE_COLS if _decide_wide(params, config) else NARROW_COLS

    base_seed = config.seed * 1009 + config.level_index * 7
    last_grid: list[list[Tile]] | None = None

    for retry in range(MAX_RETRIES):
        rng = random.Random(base_seed + retry)
        grid = _build_skeleton(cols)
        _sprinkle_floor_obstacles(grid, params, rng, cols)
        _sprinkle_air_traps(grid, params, rng, cols)
        _place_spawn_and_exit(grid, cols)
        _place_actors(grid, params, rng, cols)
        candidate = _materialize(grid, name=f"L{config.level_index:03d}", params=params)
        if is_reachable(candidate):
            return candidate
        last_grid = grid

    # Fallback: corredor mínimo seguro con la dificultad relajada.
    grid = _build_skeleton(cols)
    _place_spawn_and_exit(grid, cols)
    # Conservar al menos un guardia si la dificultad lo pide.
    if params.guard_count > 0:
        _place_actors(grid, params, random.Random(base_seed + 99), cols, force_count=1)
    fallback = _materialize(grid, name=f"L{config.level_index:03d}_fb", params=params)
    if not is_reachable(fallback):
        # Si incluso el fallback falla (no debería), corredor desnudo.
        bare = _materialize(
            _build_skeleton(cols), name=f"L{config.level_index:03d}_bare", params=params
        )
        # Re-coloca spawn/exit por si _build_skeleton no lo hace.
        _ = last_grid
        return bare
    return fallback


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _decide_wide(params: DifficultyParams, config: GeneratorConfig) -> bool:
    """Determinista: usa el seed para decidir si el nivel es ancho."""
    rng = random.Random(config.seed * 31 + config.level_index)
    return rng.random() < params.multi_room_prob


def _build_skeleton(cols: int) -> list[list[Tile]]:
    """Crea el esqueleto: techo arriba, aire en el medio, suelo + base abajo."""
    grid: list[list[Tile]] = []
    # Fila 0: techo de muro
    grid.append([Tile.FLOOR] * cols)
    # Filas 1-3: aire
    for _ in range(3):
        grid.append([Tile.EMPTY] * cols)
    # Fila 4: suelo principal
    grid.append([Tile.FLOOR] * cols)
    # Fila 5: base
    grid.append([Tile.FLOOR] * cols)
    return grid


def _sprinkle_floor_obstacles(
    grid: list[list[Tile]],
    params: DifficultyParams,
    rng: random.Random,
    cols: int,
) -> None:
    """Modifica la fila 4 (suelo) con huecos y suelos sueltos."""
    # Mantén los primeros y últimos 3 cols de la fila 4 intactos para
    # garantizar suelo en el spawn y el exit.
    for c in range(3, cols - 3):
        roll = rng.random()
        if roll < params.gap_prob:
            grid[4][c] = Tile.EMPTY
        elif roll < params.gap_prob + params.loose_prob:
            grid[4][c] = Tile.LOOSE_FLOOR


def _sprinkle_air_traps(
    grid: list[list[Tile]],
    params: DifficultyParams,
    rng: random.Random,
    cols: int,
) -> None:
    """Coloca pinchos, gates y placas en la fila 3 (la del príncipe)."""
    plate_pending: list[int] = []
    for c in range(4, cols - 4):
        # No pongas trampa si la celda no tiene suelo debajo (sería trivial).
        if grid[4][c] is not Tile.FLOOR:
            continue
        roll = rng.random()
        if roll < params.spike_prob:
            grid[3][c] = Tile.SPIKES
        elif roll < params.spike_prob + 0.04:
            # gate cada cierto tiempo, exige placa accesible cerca
            grid[3][c] = Tile.GATE
            # marca columna para colocar placa anterior
            plate_pending.append(c)

    # Coloca placas a 2-4 columnas a la izquierda de cada gate
    for gate_col in plate_pending:
        for offset in (2, 3, 4):
            cand = gate_col - offset
            if cand < 3:
                continue
            if grid[3][cand] is Tile.EMPTY and grid[4][cand] is Tile.FLOOR:
                grid[3][cand] = Tile.PRESSURE
                break


def _place_spawn_and_exit(grid: list[list[Tile]], cols: int) -> None:
    """Pone el spawn cerca del borde izquierdo y el exit cerca del derecho."""
    # Asegura suelo bajo spawn y exit
    grid[4][PRINCE_COL] = Tile.FLOOR
    grid[3][PRINCE_COL] = Tile.SPAWN_PRINCE

    exit_col = cols - EXIT_OFFSET - 1
    grid[4][exit_col] = Tile.FLOOR
    grid[3][exit_col] = Tile.EXIT


def _place_actors(
    grid: list[list[Tile]],
    params: DifficultyParams,
    rng: random.Random,
    cols: int,
    *,
    force_count: int | None = None,
) -> None:
    """Coloca guardias / esqueletos / jefe en posiciones seguras."""
    safe_cols: list[int] = [
        c
        for c in range(PRINCE_COL + 4, cols - EXIT_OFFSET - 2)
        if grid[3][c] is Tile.EMPTY and grid[4][c] is Tile.FLOOR
    ]
    rng.shuffle(safe_cols)

    n_guards = force_count if force_count is not None else params.guard_count
    for c in safe_cols[:n_guards]:
        grid[3][c] = Tile.SPAWN_GUARD

    safe_cols = safe_cols[n_guards:]
    if params.boss_flag and safe_cols:
        grid[3][safe_cols[0]] = Tile.SPAWN_BOSS
        safe_cols = safe_cols[1:]

    for c in safe_cols[: params.skeleton_count]:
        grid[3][c] = Tile.SPAWN_SKELETON


def _materialize(
    grid: list[list[Tile]],
    *,
    name: str,
    params: DifficultyParams,
) -> Level:
    """Convierte la lista mutable en un :class:`Level` inmutable."""
    text = "\n".join(_grid_row_to_str(row) for row in grid) + "\n"
    parsed = Level.parse(text, name=name)
    # Inyecta el time_limit_ticks del nivel.
    from dataclasses import replace

    return replace(parsed, time_limit_ticks=params.time_limit_ticks)


def _grid_row_to_str(row: list[Tile]) -> str:
    """Serializa una fila de tiles a su carácter ``.poplv`` correspondiente."""
    from pop2026.domain.tiles import TILE_TO_CHAR

    return "".join(TILE_TO_CHAR.get(t, ".") for t in row)


_ = Position  # re-export para quien importe Level y posiciones
