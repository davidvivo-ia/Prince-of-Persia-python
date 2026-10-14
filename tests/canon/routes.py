"""Ruta prevista de cada nivel: salas clave en orden.

Los resolutores (``test_completability`` y ``test_playability_human``)
encadenan una búsqueda A* por tramo — llegar a cada sala clave, abrir la
puerta de salida, cruzarla — en vez de buscar el nivel entero de una
vez: con rejas, placas y losas el espacio de estados es enorme y la
heurística por salas no sabe que una reja cerrada se abre desde otra
sala. Cada tramo se juega con el motor real tick a tick: si un tramo no
tiene solución, el nivel no es completable y el test falla.
"""

from __future__ import annotations

OPEN_EXIT = 0
"""Marca en la ruta: aquí se pisa la placa de la puerta de salida (el
tramo siguiente no empieza hasta que la puerta está abierta)."""

ROUTE_HINTS: dict[int, tuple[int, ...]] = {
    1: (8, 9, 10, 11, 17, 16, 15, 13, OPEN_EXIT),
    2: (2, 5, 15, 16, 18, 20, 10, 9, OPEN_EXIT),
    3: (4, 6, 7, 9, 17, 18, OPEN_EXIT, 16),
    4: (5, 7, 8, 9, 17, 20, OPEN_EXIT, 19, 18),
    5: (5, 7, 14, 17, 20, OPEN_EXIT, 14, 7, 8, 9),
    6: (2, 4, 6, 7, 12, 15, 18, OPEN_EXIT, 12, 7, 8, 9),
    7: (4, 6, 7, 14, 11, OPEN_EXIT, 18, 19, 21),
    8: (11, 14, OPEN_EXIT, 15, 19, 20),
    9: (3, 5, 6, 8, 17, 16, OPEN_EXIT, 17, 8, 9),
    10: (2, 4, 11, 15, OPEN_EXIT, 5, 8, 9),
    11: (3, 8, 13, 15, 20, OPEN_EXIT, 13, 5),
    12: (3, 5, 7, 8, 9, 14, 15, 20, 21, OPEN_EXIT, 16, 14, 9, 8),
    13: (7, 15, OPEN_EXIT),
}
