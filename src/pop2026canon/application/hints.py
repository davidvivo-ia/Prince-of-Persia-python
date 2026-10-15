"""Pistas contextuales: enseñan los verbos del original justo cuando
hacen falta, una sola vez cada una (como un tutorial de 2026, sin
pantallas de texto previas).

``detect_hint`` es pura: mira el estado del juego y devuelve la pista
que aplica ahora (o ``None``). Quién la muestra y cuántas veces es
cosa de la capa de presentación.
"""

from __future__ import annotations

from dataclasses import dataclass

from pop2026canon.domain.actions import Action, Direction
from pop2026canon.domain.combat import char_opp_dist, is_hostile
from pop2026canon.domain.game import Game
from pop2026canon.domain.physics import Terrain, can_grab, climb_down, has_floor_at, jump_up
from pop2026canon.domain.tiles import Tile


@dataclass(frozen=True, slots=True)
class Hint:
    key: str
    text: str
    pad_text: str


HINTS: dict[str, Hint] = {
    h.key: h
    for h in (
        Hint(
            "jump_up",
            "↑ junto a una cornisa: salta y agárrate · ↑ otra vez para trepar",
            "A junto a una cornisa: salta y agárrate · A otra vez para trepar",
        ),
        Hint(
            "grab",
            "Mantén SHIFT en el aire para agarrarte al borde",
            "Mantén RB en el aire para agarrarte al borde",
        ),
        Hint(
            "edge",
            "SHIFT + dirección: paso corto sin caer · de espaldas al borde, ↓ para descolgarte",
            "RB + dirección: paso corto sin caer · de espaldas al borde, B para descolgarte",
        ),
        Hint(
            "running_jump",
            "Corriendo, ↑ hace un salto largo · ↑ + dirección parado salta 3 celdas",
            "Corriendo, A hace un salto largo · A + dirección parado salta 3 celdas",
        ),
        Hint(
            "duel",
            "ESPACIO ataca · ↑ para parar justo cuando él ataca · para y replica",
            "X ataca · A para parar justo cuando él ataca · para y replica",
        ),
        Hint(
            "unarmed",
            "Sin espada, un guardia te mata de una estocada. Busca la espada",
            "Sin espada, un guardia te mata de una estocada. Busca la espada",
        ),
        Hint(
            "loose",
            "¡Suelo suelto! No te pares encima",
            "¡Suelo suelto! No te pares encima",
        ),
        Hint(
            "plate",
            "Las placas abren rejas durante un tiempo: ¡corre!",
            "Las placas abren rejas durante un tiempo: ¡corre!",
        ),
        Hint(
            "rewind",
            "Mantén R para rebobinar el tiempo",
            "Mantén LB para rebobinar el tiempo",
        ),
    )
}


def _enemy_in_sight(game: Game) -> bool:
    k = game.kid
    return any(
        is_hostile(c)
        and c.alive < 0
        and c.room == k.room
        and c.curr_row == k.curr_row
        and abs(char_opp_dist(k, c)) < 100
        for c in game.others
    )


def detect_hint(game: Game, *, died: bool = False) -> str | None:
    """Pista aplicable en este momento (la más urgente), o ``None``."""
    if died:
        return "rewind"
    k = game.kid
    if k.alive >= 0 or not (1 <= k.room <= len(game.level.rooms)):
        return None
    if _enemy_in_sight(game):
        return "duel" if k.has_sword else "unarmed"
    terrain = Terrain(game.level, game.state.open_gates, game.state.fallen_floors)
    if k.action in (Action.IN_FREEFALL, Action.IN_MIDAIR):
        if can_grab(k, terrain, shift_held=True) is not None:
            return "grab"
        return None
    if not (0 <= k.curr_col < 10 and 0 <= k.curr_row < 3):
        return None
    tile, _ = game.level.room(k.room).tile_at(k.curr_col, k.curr_row)
    coord = (k.room, k.curr_col, k.curr_row)
    if tile is Tile.LOOSE and game.state.state_at(coord) != 0:
        return "loose"
    if tile is Tile.OPENER and k.action is Action.STAND:
        return "plate"
    if k.action is not Action.STAND:
        return None
    if jump_up(k, terrain) is not None:
        return "jump_up"
    fwd = 1 if k.direction == int(Direction.RIGHT) else -1
    ahead = k.curr_col + fwd
    if 0 <= ahead < 10 and not has_floor_at(
        game.level, k.room, ahead, k.curr_row, game.state.fallen_floors
    ):
        two = ahead + fwd
        if 0 <= two < 10 and has_floor_at(
            game.level, k.room, two, k.curr_row, game.state.fallen_floors
        ):
            return "running_jump"
        if climb_down(k, terrain) is None:
            return "edge"
    return None
