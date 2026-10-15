"""Geometría de los niveles: los links deben describir un mapa planar.

Inspirado en el diseño de los remakes clásicos (p.ej. el port C++ de
VictorBusque, donde cada nivel es UN tilemap continuo y las salas son
ventanas de 10x3 sobre él): la geometría coherente se garantiza por
construcción. Aquí las salas se declaran en un grid 2D y los links se
derivan de la adyacencia — estos tests aseguran que ningún cambio
futuro reintroduzca geometría imposible.
"""

from __future__ import annotations

from collections import deque

import pytest

from pop2026canon.domain.levels_canon import CANON_LEVELS, _grid_links


class TestGridLinksHelper:
    def test_simple_grid(self) -> None:
        links = _grid_links("1 2\n3 .", 3)
        assert links[1] == (0, 3, 2, 0)  # n, s, e, w
        assert links[2] == (0, 0, 0, 1)
        assert links[3] == (1, 0, 0, 0)

    def test_duplicate_id_raises(self) -> None:
        with pytest.raises(ValueError, match="dos veces"):
            _grid_links("1 1", 1)

    def test_missing_id_raises(self) -> None:
        with pytest.raises(ValueError, match="ids incorrectos"):
            _grid_links("1 3", 3)


@pytest.mark.parametrize("level", CANON_LEVELS)
def test_links_are_reciprocal(level) -> None:  # type: ignore[no-untyped-def]
    """Si A enlaza a B por una dirección, B enlaza a A por la opuesta."""
    issues = []
    for room in level.rooms:
        for d, link, opposite in (
            ("e", room.link_e, "link_w"),
            ("w", room.link_w, "link_e"),
            ("n", room.link_n, "link_s"),
            ("s", room.link_s, "link_n"),
        ):
            if link:
                other = level.room(link)
                if getattr(other, opposite) != room.id:
                    issues.append(
                        f"L{level.number} room {room.id}.{d}={link} pero "
                        f"room {link}.{opposite}={getattr(other, opposite)}"
                    )
    assert not issues, issues


@pytest.mark.parametrize("level", CANON_LEVELS)
def test_planar_embedding(level) -> None:  # type: ignore[no-untyped-def]
    """Los links definen coordenadas 2D únicas y consistentes por sala.

    Detecta geometría Escher: una sala en dos posiciones a la vez, o dos
    salas compartiendo la misma posición.
    """
    coords: dict[int, tuple[int, int]] = {level.start_room: (0, 0)}
    occupied: dict[tuple[int, int], int] = {(0, 0): level.start_room}
    queue: deque[int] = deque([level.start_room])
    while queue:
        rid = queue.popleft()
        room = level.room(rid)
        x, y = coords[rid]
        for link, (dx, dy) in (
            (room.link_e, (1, 0)),
            (room.link_w, (-1, 0)),
            (room.link_n, (0, -1)),
            (room.link_s, (0, 1)),
        ):
            if not link:
                continue
            pos = (x + dx, y + dy)
            if link in coords:
                assert coords[link] == pos, (
                    f"L{level.number}: room {link} en {coords[link]} y {pos} a la vez"
                )
            else:
                assert pos not in occupied, (
                    f"L{level.number}: rooms {occupied[pos]} y {link} comparten {pos}"
                )
                coords[link] = pos
                occupied[pos] = link
                queue.append(link)


@pytest.mark.parametrize("level", CANON_LEVELS)
def test_all_rooms_connected(level) -> None:  # type: ignore[no-untyped-def]
    """Ninguna sala queda desconectada del componente del spawn.

    (Antes del grid, L3 tenía sus dos salas secretas huérfanas por un
    link asimétrico.)
    """
    seen: set[int] = {level.start_room}
    queue: deque[int] = deque([level.start_room])
    while queue:
        rid = queue.popleft()
        room = level.room(rid)
        for link in (room.link_n, room.link_s, room.link_e, room.link_w):
            if link and link not in seen:
                seen.add(link)
                queue.append(link)
    orphans = {r.id for r in level.rooms} - seen
    assert not orphans, f"L{level.number}: salas desconectadas del spawn: {sorted(orphans)}"
