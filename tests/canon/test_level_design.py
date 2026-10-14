"""Diseño de los niveles: cada sala usa sus tres filas, las salas de un
nivel no se repiten, hay cornisas que trepar, y la geometría vertical es
coherente (nadie cae dentro de un muro)."""

from __future__ import annotations

import pytest

from pop2026canon.domain.level import Level
from pop2026canon.domain.levels_canon import CANON_LEVELS, _ascii
from pop2026canon.domain.tiles import SOLID, Tile

LEVELS = CANON_LEVELS
_IDS = [f"L{lv.number}" for lv in LEVELS]


def _rows(level: Level, room_id: int) -> tuple[tuple[Tile, ...], ...]:
    room = level.room(room_id)
    return tuple(tuple(room.tile_at(c, r)[0] for c in range(10)) for r in range(3))


def _floorish(t: Tile) -> bool:
    return t in SOLID and t is not Tile.WALL


@pytest.mark.parametrize("level", LEVELS, ids=_IDS)
def test_rooms_use_their_height(level: Level) -> None:
    """Una sala no es sólo techo corrido + suelo corrido: hay algo en las
    filas altas (muros, cornisas, plataformas, celosías...)."""
    flat = 0
    for room in level.rooms:
        top, mid, _ = _rows(level, room.id)
        plain_top = all(t is Tile.FLOOR for t in top)
        empty_mid = all(t is Tile.EMPTY for t in mid)
        if plain_top and empty_mid:
            flat += 1
    assert flat == 0, f"L{level.number}: {flat} salas planas"


@pytest.mark.parametrize("level", LEVELS, ids=_IDS)
def test_rooms_are_not_copies(level: Level) -> None:
    layouts = [_rows(level, room.id) for room in level.rooms]
    distinct = len(set(layouts))
    assert distinct >= len(layouts) - 1, f"L{level.number}: {distinct}/{len(layouts)} distintas"


@pytest.mark.parametrize("level", [lv for lv in LEVELS if lv.number < 14], ids=_IDS[:13])
def test_levels_have_ledges_to_climb(level: Level) -> None:
    """Cornisas trepables: suelo en la fila 1 con aire encima de la celda
    vecina y suelo debajo de esa vecina (de pie en la fila 2, se salta y
    se agarra)."""
    ledges = 0
    for room in level.rooms:
        _top, mid, bot = _rows(level, room.id)
        for c in range(10):
            if not _floorish(mid[c]):
                continue
            for n in (c - 1, c + 1):
                if 0 <= n < 10 and mid[n] is Tile.EMPTY and _floorish(bot[n]):
                    ledges += 1
                    break
    assert ledges >= 4, f"L{level.number}: sólo {ledges} cornisas trepables"


@pytest.mark.parametrize("level", LEVELS, ids=_IDS)
def test_nobody_falls_into_a_wall(level: Level) -> None:
    """Bajo cada hueco del suelo (o losa suelta) de una sala, la sala de
    abajo deja pasar o recoge: nunca un muro."""
    for room in level.rooms:
        south = room.link_s
        if not (1 <= south <= len(level.rooms)):
            continue
        _, _, bot = _rows(level, room.id)
        s_top, s_mid, _ = _rows(level, south)
        for c in range(10):
            if bot[c] in (Tile.EMPTY, Tile.LOOSE):
                assert s_top[c] is not Tile.WALL, (
                    f"L{level.number}: el hueco de la sala {room.id} col {c} da a un muro"
                )
                if s_top[c] is Tile.EMPTY:
                    assert s_mid[c] is not Tile.WALL, (
                        f"L{level.number}: la caída de la sala {room.id} col {c} acaba en un muro"
                    )


@pytest.mark.parametrize("level", LEVELS, ids=_IDS)
def test_room_edges_meet(level: Level) -> None:
    """Entre salas vecinas el pasillo principal (fila 2) continúa: no hay
    un muro de un lado frente a suelo del otro."""
    for room in level.rooms:
        east = room.link_e
        if not (1 <= east <= len(level.rooms)):
            continue
        a = room.tile_at(9, 2)[0]
        b = level.room(east).tile_at(0, 2)[0]
        assert not (a is Tile.WALL and _floorish(b)), (room.id, east)
        assert not (b is Tile.WALL and _floorish(a)), (room.id, east)


class TestAsciiRooms:
    def test_legend_round_trip(self) -> None:
        spec = _ascii("#__.LSG_P_", "..s_....h.", "XT_kM_Dd__")
        top, mid, bot = spec.rows
        assert top[0] is Tile.WALL
        assert top[3] is Tile.EMPTY
        assert top[6] is Tile.GATE
        assert mid[2] is Tile.SWORD
        assert mid[8] is Tile.POTION
        assert bot[0] is Tile.CHOMPER
        assert bot[6] is Tile.LEVEL_DOOR_LEFT
        assert spec.canonical
        assert ((8, 1), 1) in spec.fg_modifiers  # poción de vida

    def test_bad_rows_are_rejected(self) -> None:
        with pytest.raises(ValueError, match="3 caracteres"):
            _ascii("___", "..........", "__________")
        with pytest.raises(ValueError, match="desconocido"):
            _ascii("____Q_____", "..........", "__________")


# ---------------------------------------------------------------------------
# Puzles: lo que convierte una sala en un nivel
# ---------------------------------------------------------------------------


def _room_hops(level: Level, a: int, b: int) -> int:
    """Salas que hay que cruzar para ir de ``a`` a ``b`` (por enlaces)."""
    from collections import deque

    seen = {a: 0}
    q = deque([a])
    while q:
        r = q.popleft()
        rm = level.room(r)
        for nb in (rm.link_n, rm.link_s, rm.link_e, rm.link_w):
            if 1 <= nb <= len(level.rooms) and nb not in seen:
                seen[nb] = seen[r] + 1
                q.append(nb)
    return seen.get(b, 99)


PLAYABLE = [lv for lv in LEVELS if lv.number < 14]
_PIDS = _IDS[:13]


@pytest.mark.parametrize("level", PLAYABLE, ids=_PIDS)
def test_exit_door_needs_a_far_plate(level: Level) -> None:
    """La puerta de salida está cerrada: la abre una placa a varias salas
    de distancia (hay que buscarla y volver), como en el original."""
    exits = [
        (rm.id, c, r)
        for rm in level.rooms
        for r in range(3)
        for c in range(10)
        if rm.tile_at(c, r)[0] is Tile.LEVEL_DOOR_LEFT
    ]
    assert exits, f"L{level.number}: sin puerta de salida"
    plates = level.plates_for_gate(exits[0])
    assert plates, f"L{level.number}: la puerta de salida no tiene placa"
    hops = _room_hops(level, plates[0][0], exits[0][0])
    assert hops >= 2, f"L{level.number}: la placa de la salida está demasiado cerca ({hops})"


@pytest.mark.parametrize("level", PLAYABLE, ids=_PIDS)
def test_levels_have_a_gate_puzzle(level: Level) -> None:
    """Además de la salida, cada nivel tiene al menos una reja con su
    mecanismo (placa, placa de cierre o losa que cae sobre la placa), o
    la reja que abre el ratón (L8)."""
    from pop2026canon.domain.level import EventKind

    gates = [
        (rm.id, c, r)
        for rm in level.rooms
        for r in range(3)
        for c in range(10)
        if rm.tile_at(c, r)[0] is Tile.GATE
    ]
    assert gates, f"L{level.number}: sin rejas"
    linked = [g for g in gates if level.plates_for_gate(g)]
    mouse = any(e.kind is EventKind.MOUSE_APPEAR for e in level.events)
    assert linked or mouse, f"L{level.number}: ninguna reja tiene mecanismo"


@pytest.mark.parametrize("level", PLAYABLE, ids=_PIDS)
def test_levels_have_traps_and_rewards(level: Level) -> None:
    traps = sum(
        1
        for rm in level.rooms
        for b in rm.fg
        if Tile(b & 0x1F) in (Tile.SPIKE, Tile.CHOMPER, Tile.LOOSE)
    )
    potions = sum(1 for rm in level.rooms for b in rm.fg if Tile(b & 0x1F) is Tile.POTION)
    assert traps >= 5, f"L{level.number}: sólo {traps} trampas"
    assert potions >= 1, f"L{level.number}: sin pociones"


def test_closer_plates_and_loose_on_plates_exist() -> None:
    """Los dos mecanismos clásicos aparecen en la campaña: placas de
    cierre que hay que saltar y losas que caen sobre una placa."""
    closers = 0
    loose_on_plate = 0
    for level in PLAYABLE:
        for rm in level.rooms:
            for r in range(3):
                for c in range(10):
                    t = rm.tile_at(c, r)[0]
                    if t is Tile.CLOSER and level.gates_for_plate((rm.id, c, r)):
                        closers += 1
                    if t is Tile.LOOSE and r == 2 and 1 <= rm.link_s <= len(level.rooms):
                        south = level.room(rm.link_s)
                        if (
                            south.tile_at(c, 0)[0] is Tile.EMPTY
                            and south.tile_at(c, 1)[0] is Tile.EMPTY
                            and south.tile_at(c, 2)[0] is Tile.OPENER
                        ):
                            loose_on_plate += 1
    assert closers >= 4
    assert loose_on_plate >= 3
