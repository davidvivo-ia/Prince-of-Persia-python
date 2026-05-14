"""Comprobación de alcanzabilidad por BFS.

Modelo simplificado del movimiento del príncipe usado para validar que
un nivel generado tenga al menos un camino del spawn a una salida.

Movimientos modelados:

- Caminar a celda contigua si tiene suelo debajo.
- Caer hasta la primera celda con suelo (caída limitada por
  ``MAX_FALL_DROP``).
- Saltar direccionalmente hasta ``JUMP_REACH`` celdas hacia adelante,
  saltando huecos pequeños.
- Trepar una repisa de una celda (subir +1 fila, +1 columna).

Las placas de presión se "asumen pulsadas" si son alcanzables: la
puerta más cercana se considera abierta. Esto evita modelar el
estado dinámico completo y es suficiente para validar layouts
generados.
"""

from __future__ import annotations

from collections import deque

from pop2026.domain.geometry import Position
from pop2026.domain.level import Level
from pop2026.domain.tiles import SOLID, Tile

MAX_FALL_DROP: int = 8
"""Caída máxima en celdas que se considera supervivible para BFS.

Con física continua, caer sobre suelo regular no daña — solo los
pinchos matan al impactar a más de ``SPIKE_LETHAL_VY``. Por eso
elevamos el rango respecto al modelo discreto antiguo (3).
"""

JUMP_REACH: int = 4
"""Celdas horizontales que cubre un salto con la nueva parábola.

Con ``JUMP_VEL=-0.55`` y ``GRAVITY=0.06``, el príncipe permanece en el
aire ~18 ticks. A ``RUN_SPEED=0.22`` eso son ~4 celdas horizontales.
"""


def _is_solid_static(level: Level, pos: Position, open_gates: frozenset[Position]) -> bool:
    """¿Es la celda sólida considerando gates abiertas?"""
    tile = level.tile_at(pos)
    if tile is Tile.GATE and pos in open_gates:
        return False
    return tile in SOLID


def _has_floor(level: Level, pos: Position, open_gates: frozenset[Position]) -> bool:
    """¿Hay suelo justo debajo de ``pos``?"""
    return _is_solid_static(level, Position(pos.row + 1, pos.col), open_gates)


def _nearest_gate(level: Level, plate: Position) -> Position | None:
    """Gate más cercana en distancia Manhattan (igual que ``game._nearest_gate``)."""
    best: Position | None = None
    best_d = 10**9
    for r in range(level.rows):
        for c in range(level.cols):
            if level.grid[r][c] is Tile.GATE:
                d = abs(r - plate.row) + abs(c - plate.col)
                if d < best_d:
                    best_d = d
                    best = Position(r, c)
    return best


def _expand(level: Level, pos: Position, open_gates: frozenset[Position]) -> list[Position]:
    """Devuelve celdas alcanzables en un solo "movimiento" desde ``pos``."""
    out: list[Position] = []

    for d in (-1, 1):
        target = Position(pos.row, pos.col + d)
        # Caminar a vecino con suelo
        if (
            0 <= target.col < level.cols
            and not _is_solid_static(level, target, open_gates)
            and _has_floor(level, target, open_gates)
        ):
            out.append(target)

        # Saltar direccional sobre un hueco. La trayectoria es horizontal:
        # si una celda intermedia es sólida (gate cerrada o pared), bloquea.
        for span in range(2, JUMP_REACH + 1):
            blocked = False
            for inter in range(1, span):
                if _is_solid_static(level, Position(pos.row, pos.col + d * inter), open_gates):
                    blocked = True
                    break
            if blocked:
                break
            j = Position(pos.row, pos.col + d * span)
            if not (0 <= j.col < level.cols):
                break
            if _is_solid_static(level, j, open_gates):
                break
            if _has_floor(level, j, open_gates):
                out.append(j)
                break

        # Trepar repisa una celda
        ledge = Position(pos.row - 1, pos.col + d)
        landing = Position(pos.row - 2, pos.col + d)
        head = Position(pos.row - 1, pos.col)
        if (
            ledge.row >= 0
            and 0 <= ledge.col < level.cols
            and _is_solid_static(level, ledge, open_gates)
            and not _is_solid_static(level, landing, open_gates)
            and not _is_solid_static(level, head, open_gates)
            and _has_floor(level, landing, open_gates)
        ):
            out.append(landing)

    # Caer recto: simula caer hasta MAX_FALL_DROP buscando una celda con suelo
    for drop in range(1, MAX_FALL_DROP + 1):
        below = Position(pos.row + drop, pos.col)
        if not (0 <= below.row < level.rows):
            break
        if _is_solid_static(level, below, open_gates):
            break
        if _has_floor(level, below, open_gates):
            out.append(below)
            break

    return out


def _collect_open_gates(level: Level, reachable: set[Position]) -> frozenset[Position]:
    """Si alguna placa es alcanzable, abre la gate más cercana."""
    gates: set[Position] = set()
    for r in range(level.rows):
        for c in range(level.cols):
            pos = Position(r, c)
            if level.grid[r][c] is Tile.PRESSURE and pos in reachable:
                g = _nearest_gate(level, pos)
                if g is not None:
                    gates.add(g)
    return frozenset(gates)


def reachable_cells(level: Level) -> set[Position]:
    """Conjunto de celdas accesibles para el príncipe desde su spawn."""
    open_gates: frozenset[Position] = frozenset()
    seen: set[Position] = set()
    queue: deque[Position] = deque()
    queue.append(level.prince_spawn)
    seen.add(level.prince_spawn)

    while queue:
        # Bucle anidado: re-expandimos cuando se abren gates nuevas.
        while queue:
            pos = queue.popleft()
            for nxt in _expand(level, pos, open_gates):
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        # ¿Alguna placa nueva activa una gate cerrada?
        new_open = _collect_open_gates(level, seen)
        if new_open - open_gates:
            open_gates = open_gates | new_open
            # Vuelve a expandir todas las celdas conocidas con las gates nuevas.
            queue.extend(seen)
    return seen


def is_reachable(level: Level) -> bool:
    """``True`` si el spawn alcanza al menos una celda ``EXIT``."""
    cells = reachable_cells(level)
    return any(level.tile_at(pos) is Tile.EXIT for pos in cells)
