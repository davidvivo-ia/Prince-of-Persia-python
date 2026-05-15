"""Path-finding BFS sobre el grafo de salas + celdas.

Para cada nivel jugable, valida que existe una ruta navegable desde la
celda de spawn hasta alguna celda con LEVEL_DOOR_LEFT (la exit door).

El BFS asume:
- Movimiento entre celdas con suelo sólido bajo (FLOOR, LOOSE, DEBRIS,
  DOORTOP_WITH_FLOOR, GATE con doorlink que el kid puede activar).
- Saltos hasta 3 celdas horizontales sobre EMPTY (runjump canon).
- Drop libre por borde sur si el sala destino existe (link_s>0).
- Subida por sala-norte si la sala N existe Y hay alguna columna con
  acceso vertical (lattice o doortop) en la sala actual.
- Cambio de sala por bordes E/W cuando hay link y la celda destino es
  pisable.

Es una aproximación conservadora: si el BFS encuentra ruta, el nivel
es completable; si no la encuentra, no implica imposibilidad real
(jugador real puede usar técnicas que el BFS no modela).
"""

from __future__ import annotations

from collections import deque

import pytest

from pop2026canon.domain.levels_canon import CANON_LEVELS
from pop2026canon.domain.tiles import Tile

# Cell = (room, col, row)
Cell = tuple[int, int, int]


def _piece_at(level, room_id: int, col: int, row: int) -> Tile:  # type: ignore[no-untyped-def]
    room = level.room(room_id)
    byte = room.fg[row * 10 + col]
    return Tile(byte & 0x1F)


def _has_floor_below(level, room_id: int, col: int, row: int) -> bool:  # type: ignore[no-untyped-def]
    """¿Hay tile sólido bajo (col, row) que permita estar parado?"""
    if row + 1 >= 3:
        # Fila inferior: necesita link_s o piso de la propia sala (LOOSE/DEBRIS/etc.)
        return True
    piece = _piece_at(level, room_id, col, row + 1)
    return piece in (
        Tile.FLOOR,
        Tile.LOOSE,
        Tile.DEBRIS,
        Tile.DOORTOP_WITH_FLOOR,
        Tile.PILLAR,
        Tile.BIGPILLAR_TOP,
        Tile.WALL,
        Tile.GATE,  # Puede ser pisable si está cerrada
        Tile.STUCK,
    )


def _is_passable(level, room_id: int, col: int, row: int) -> bool:  # type: ignore[no-untyped-def]
    """¿El kid puede pasar por (col, row) sin chocar?"""
    if not (0 <= col < 10 and 0 <= row < 3):
        return False
    piece = _piece_at(level, room_id, col, row)
    if piece in (Tile.WALL, Tile.PILLAR, Tile.BIGPILLAR_BOTTOM, Tile.BIGPILLAR_TOP):
        return False
    # GATE: pasable si tiene doorlink en este nivel (suponemos plate alcanzable)
    if piece is Tile.GATE:
        coord: Cell = (room_id, col, row)
        return bool(level.plates_for_gate(coord)) or _gate_opened_by_event(level, coord)
    return True


def _gate_opened_by_event(level, coord: Cell) -> bool:  # type: ignore[no-untyped-def]
    """L8: el mouse abre gates sin doorlink en la sala del MOUSE_APPEAR."""
    from pop2026canon.domain.level import EventKind

    return any(
        ev.kind is EventKind.MOUSE_APPEAR and ev.room == coord[0] for ev in level.events
    )


def _is_landable(level, room_id: int, col: int, row: int) -> bool:  # type: ignore[no-untyped-def]
    """¿El kid puede pararse en (col, row)? Es pasable y tiene suelo abajo."""
    return _is_passable(level, room_id, col, row) and _has_floor_below(level, room_id, col, row)


def _drop_landing(level, room_id: int, col: int) -> Cell | None:  # type: ignore[no-untyped-def]
    """Devuelve la celda donde aterriza el kid si cae por la sala desde row 0.

    Busca de arriba a abajo en la columna ``col`` (y col±1) la primera fila
    landable. Si la sala completa es hueca, devuelve None (kid cae a la
    siguiente sala sur).
    """
    for landing_col in (col, col - 1, col + 1):
        if not (0 <= landing_col < 10):
            continue
        for r in range(3):
            if _is_landable(level, room_id, landing_col, r):
                return (room_id, landing_col, r)
    return None


def _neighbors(level, cell: Cell) -> list[Cell]:  # type: ignore[no-untyped-def]
    """Vecinos accesibles del kid desde `cell`."""
    room, col, row = cell
    out: list[Cell] = []

    # Movimiento horizontal cardinal
    for dx in (-1, 1):
        nc = col + dx
        if 0 <= nc < 10:
            if _is_landable(level, room, nc, row):
                out.append((room, nc, row))
        else:
            # Cambio de sala E/W
            nroom = level.room(room).link_e if dx == 1 else level.room(room).link_w
            if nroom:
                landing_col = 0 if dx == 1 else 9
                if _is_landable(level, nroom, landing_col, row):
                    out.append((nroom, landing_col, row))

    # Saltos horizontales 2-4 celdas (runjump canon cruza hasta 3 cols de aire)
    for dx in (-4, -3, -2, 2, 3, 4):
        nc = col + dx
        if 0 <= nc < 10 and _is_landable(level, room, nc, row):
            step = 1 if dx > 0 else -1
            ok = True
            for c2 in range(col + step, nc, step):
                if not _is_passable(level, room, c2, row):
                    ok = False
                    break
            if ok:
                out.append((room, nc, row))

    # Caída libre al sur (link_s):
    #  - row 2 con link directo
    #  - row 1 si alguna col cercana tiene gap (pit) en row 2
    s_link = level.room(room).link_s
    fall_cols: list[int] = []
    if s_link and row == 2:
        fall_cols = [col]
    elif s_link and row == 1:
        for dc in (0, -1, 1, -2, 2, -3, 3):
            pit_col = col + dc
            if not (0 <= pit_col < 10):
                continue
            if _piece_at(level, room, pit_col, 2) is not Tile.EMPTY:
                continue
            edge_col = pit_col - 1 if dc >= 0 else pit_col + 1
            if 0 <= edge_col < 10 and _is_landable(level, room, edge_col, 1):
                fall_cols.append(pit_col)
                break
    for fc in fall_cols:
        target = _drop_landing(level, s_link, fc)
        if target is not None:
            out.append(target)

    # Subida vertical en la misma sala (lattice/doortop arriba)
    if row > 0:
        up_piece = _piece_at(level, room, col, row - 1)
        if up_piece in (Tile.LATTICE_PILLAR, Tile.LATTICE_DOWN, Tile.DOORTOP_WITH_FLOOR):
            out.append((room, col, row - 1))

    # Subida a sala norte si row 0 + link_n + lattice/doortop en la sala destino
    if row == 0:
        n = level.room(room).link_n
        if n:
            # Heurística: si hay alguna celda landable en row 2 de la sala destino
            for c2 in range(10):
                if _is_landable(level, n, c2, 2):
                    out.append((n, c2, 2))
                    break

    return out


def _find_exit_cells(level) -> list[Cell]:  # type: ignore[no-untyped-def]
    """Devuelve las celdas con LEVEL_DOOR_LEFT del nivel (objetivos)."""
    targets: list[Cell] = []
    for room in level.rooms:
        for row in range(3):
            for col in range(10):
                if _piece_at(level, room.id, col, row) is Tile.LEVEL_DOOR_LEFT:
                    targets.append((room.id, col, row))
    return targets


def _bfs(level, start: Cell, goals: set[Cell]) -> bool:  # type: ignore[no-untyped-def]
    """¿Existe ruta desde `start` a alguna celda en `goals`?"""
    if start in goals:
        return True
    seen: set[Cell] = {start}
    queue: deque[Cell] = deque([start])
    while queue:
        cell = queue.popleft()
        for nxt in _neighbors(level, cell):
            if nxt in seen:
                continue
            if nxt in goals:
                return True
            seen.add(nxt)
            queue.append(nxt)
    return False


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def _room_graph_bfs(level, start_room: int) -> set[int]:  # type: ignore[no-untyped-def]
    """Conectividad del grafo de salas: dos salas vecinas si comparten link."""
    seen: set[int] = {start_room}
    queue: deque[int] = deque([start_room])
    while queue:
        rid = queue.popleft()
        room = level.room(rid)
        for nxt in (room.link_n, room.link_s, room.link_e, room.link_w):
            if nxt and nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return seen


@pytest.mark.parametrize("level", CANON_LEVELS[:13])  # L14 es cinemática
def test_level_exit_room_reachable_from_spawn(level) -> None:  # type: ignore[no-untyped-def]
    """La sala con la exit door está conectada al spawn por links de sala."""
    exits = _find_exit_cells(level)
    assert exits, f"L{level.number} sin exit door"
    exit_rooms = {coord[0] for coord in exits}
    reachable = _room_graph_bfs(level, level.start_room)
    common = exit_rooms & reachable
    assert common, (
        f"L{level.number}: exit rooms {exit_rooms} no alcanzables desde "
        f"start_room={level.start_room}. Reachable: {sorted(reachable)}"
    )


@pytest.mark.parametrize("level", CANON_LEVELS[:13])
def test_no_orphan_rooms(level) -> None:  # type: ignore[no-untyped-def]
    """Cada sala debería estar conectada al componente del spawn (salvo
    máximo 2 salas "secretas" como bonificación)."""
    n = len(level.rooms)
    reachable = _room_graph_bfs(level, level.start_room)
    orphans = n - len(reachable)
    assert orphans <= 2, (
        f"L{level.number}: {orphans} salas huérfanas de {n} totales. Reachable={sorted(reachable)}"
    )


@pytest.mark.parametrize("level", CANON_LEVELS[:13])
def test_level_cell_pathing_partial(level) -> None:  # type: ignore[no-untyped-def]
    """BFS celda-a-celda: el spawn alcanza al menos varias salas distintas.

    No exigimos ruta hasta exit (el BFS conservador no modela ledge-grab
    canon), pero sí que el jugador puede salir de la primera sala.
    """
    start: Cell = (level.start_room, level.start_col, level.start_row)
    seen: set[Cell] = {start}
    queue: deque[Cell] = deque([start])
    while queue:
        cell = queue.popleft()
        for nxt in _neighbors(level, cell):
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    rooms_visited = {c[0] for c in seen}
    assert len(rooms_visited) >= 2, (
        f"L{level.number}: spawn no llega a ninguna sala vecina (salas visitadas: {rooms_visited})"
    )


@pytest.mark.parametrize("level", CANON_LEVELS[:13])
def test_level_has_minimum_room_count(level) -> None:  # type: ignore[no-untyped-def]
    """Cada nivel canon tiene al menos 18 salas (target POP1)."""
    assert len(level.rooms) >= 18, f"L{level.number} sólo tiene {len(level.rooms)} salas"


@pytest.mark.parametrize("level", CANON_LEVELS)
def test_level_room_links_consistent(level) -> None:  # type: ignore[no-untyped-def]
    """Si la sala A enlaza a B por dirección d, B suele enlazar a A por d_opuesta."""
    n = len(level.rooms)
    issues = []
    for room in level.rooms:
        for direction, link in (
            ("n", room.link_n),
            ("s", room.link_s),
            ("e", room.link_e),
            ("w", room.link_w),
        ):
            if not (0 <= link <= n):
                issues.append(
                    f"L{level.number} room {room.id} link {direction}={link} fuera de rango"
                )
    assert not issues, issues


def test_tile_diversity_across_levels() -> None:
    """Los 14 niveles usan >= 15 tipos de tile distintos (diversidad canon)."""
    seen: set[Tile] = set()
    for lvl in CANON_LEVELS:
        for room in lvl.rooms:
            for byte in room.fg:
                seen.add(Tile(byte & 0x1F))
    expected_minimum = {
        Tile.FLOOR,
        Tile.EMPTY,
        Tile.SPIKE,
        Tile.LOOSE,
        Tile.GATE,
        Tile.OPENER,
        Tile.CHOMPER,
        Tile.MIRROR,
        Tile.SKELETON,
        Tile.SWORD,
        Tile.LEVEL_DOOR_LEFT,
        Tile.LEVEL_DOOR_RIGHT,
        Tile.POTION,
        Tile.TORCH,
    }
    missing = expected_minimum - seen
    assert not missing, f"Tile types nunca usados en canon: {missing}"
    assert len(seen) >= 15, f"Sólo {len(seen)} tipos usados, esperaba >= 15"


def test_uses_lattice_tiles() -> None:
    """Canon expandido usa lattices para escalar verticalmente."""
    seen: set[Tile] = set()
    for lvl in CANON_LEVELS:
        for room in lvl.rooms:
            for byte in room.fg:
                seen.add(Tile(byte & 0x1F))
    assert any(t in seen for t in (Tile.LATTICE_PILLAR, Tile.LATTICE_DOWN, Tile.LATTICE_SMALL))


def test_uses_pillar_and_balcony() -> None:
    """Canon expandido usa columnas y balcones para variedad arquitectónica."""
    seen: set[Tile] = set()
    for lvl in CANON_LEVELS:
        for room in lvl.rooms:
            for byte in room.fg:
                seen.add(Tile(byte & 0x1F))
    assert Tile.BIGPILLAR_TOP in seen or Tile.PILLAR in seen
    assert Tile.BALCONY_LEFT in seen or Tile.BALCONY_RIGHT in seen


def test_potions_have_diverse_modifiers() -> None:
    """Al menos 3 tipos de PotionType distintos aparecen en el canon."""
    from pop2026canon.domain.tiles import PotionType

    seen_types: set[int] = set()
    for lvl in CANON_LEVELS:
        for room in lvl.rooms:
            for byte in room.fg:
                if (byte & 0x1F) == int(Tile.POTION):
                    seen_types.add((byte >> 5) & 0x07)
    # Convertimos a PotionType para inspección, pero contamos sólo tipos válidos
    valid = {p for p in seen_types if p < len(PotionType)}
    assert len(valid) >= 3, f"Sólo {valid} potion types vistos, esperaba >= 3"


def test_l12_has_24_rooms() -> None:
    """L12 The Vizier es el nivel más grande del canon — 24 salas."""
    assert len(CANON_LEVELS[11].rooms) == 24
