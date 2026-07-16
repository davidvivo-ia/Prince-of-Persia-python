"""Física de caídas y colisiones: aterrizaje, daño por altura, muros.

Cubre el ciclo completo que faltaba en el motor: walk-off (pisar el
vacío inicia caída), aterrizaje (soft / med / mortal según fall_y),
muerte en abismo, colisión horizontal contra muros y gates cerradas,
y caída-pluma (poción FLOAT).
"""

from __future__ import annotations

from dataclasses import replace

from pop2026canon.application.controller import Command
from pop2026canon.application.tick import advance
from pop2026canon.domain.actions import Action, Seq
from pop2026canon.domain.chars import Char, CharId
from pop2026canon.domain.game import GameStatus, new_game
from pop2026canon.domain.level import Level
from pop2026canon.domain.physics import blocks_body_at, step_physics
from pop2026canon.domain.room import Room
from pop2026canon.domain.tiles import PotionType, Tile, encode_tile


def _room(rows: list[list[Tile]], room_id: int = 1, **links: int) -> Room:
    fg = tuple(encode_tile(t, 0) for row in rows for t in row)
    return Room(id=room_id, fg=fg, bg=tuple([0] * 30), **links)


E, F, W, G = Tile.EMPTY, Tile.FLOOR, Tile.WALL, Tile.GATE


def _corridor_level(*, pit_cols: tuple[int, ...] = (), wall_col: int | None = None) -> Level:
    """Sala única: suelo en row 2 (menos pits), muro opcional en row 1."""
    top = [E] * 10
    mid = [E] * 10
    bot = [F] * 10
    for c in pit_cols:
        bot[c] = E
    if wall_col is not None:
        mid[wall_col] = W
    room = _room([top, mid, bot])
    return Level(number=1, name="test", rooms=(room,), start_room=1, start_col=1, start_row=1)


def _stacked_level(stories: int) -> Level:
    """``stories`` salas apiladas: todas huecas con pit menos la última,
    que tiene suelo completo. El kid cae desde la sala 1 hasta abajo."""
    rooms = []
    for i in range(1, stories + 1):
        is_last = i == stories
        bot = [F] * 10 if is_last else [F] * 4 + [E, E] + [F] * 4
        rooms.append(
            _room(
                [[E] * 10, [E] * 10, bot],
                room_id=i,
                link_s=0 if is_last else i + 1,
                link_n=i - 1,
            )
        )
    return Level(number=1, name="test", rooms=tuple(rooms), start_room=1, start_col=1, start_row=1)


def _kid(level: Level, **kw: object) -> Char:
    defaults: dict[str, object] = {
        "charid": CharId.KID,
        "room": 1,
        "curr_col": 1,
        "curr_row": 1,
        "hp_curr": 3,
        "hp_max": 3,
        "curr_seq_id": int(Seq.STAND),
    }
    defaults.update(kw)
    return Char(**defaults)  # type: ignore[arg-type]


class TestWalkOff:
    def test_standing_over_pit_starts_fall(self) -> None:
        level = _corridor_level(pit_cols=(5,))
        kid = _kid(level, curr_col=5)
        kid = step_physics(kid, level)
        assert kid.action is Action.IN_FREEFALL, "El kid no cae al pisar el vacío"

    def test_standing_on_floor_stays(self) -> None:
        level = _corridor_level()
        kid = _kid(level, curr_col=5)
        kid = step_physics(kid, level)
        assert kid.action is Action.STAND


def _drop_kid(level: Level, *, float_ticks: int = 0) -> Char:
    """Suelta al kid sobre el pit de la sala 1 y simula hasta aterrizar."""
    kid = _kid(level, curr_col=4, curr_row=1, float_ticks=float_ticks)
    for _ in range(200):
        kid = step_physics(kid, level, has_feather=kid.float_ticks > 0)
        if kid.action is not Action.IN_FREEFALL:
            break
    return kid


class TestLanding:
    def test_in_room_fall_soft_lands(self) -> None:
        level = _corridor_level()
        kid = _kid(level, curr_row=0, action=Action.IN_FREEFALL, curr_seq_id=int(Seq.FALL))
        for _ in range(10):
            kid = step_physics(kid, level)
            if kid.action is not Action.IN_FREEFALL:
                break
        assert kid.action is Action.STAND
        assert kid.hp_curr == 3, "Una caída dentro de la sala no debería hacer daño"
        assert kid.curr_row == 1, "Debería quedar de pie sobre el suelo de row 2"

    def test_one_story_fall_is_safe(self) -> None:
        kid = _drop_kid(_stacked_level(2))
        assert kid.room == 2
        assert kid.action is Action.STAND
        assert kid.hp_curr == 3, "1 piso de caída es seguro (canon)"

    def test_two_story_fall_hurts(self) -> None:
        kid = _drop_kid(_stacked_level(3))
        assert kid.room == 3
        assert kid.alive < 0
        assert kid.hp_curr == 2, "2 pisos de caída cuestan 1 HP (canon)"

    def test_three_story_fall_kills(self) -> None:
        kid = _drop_kid(_stacked_level(4))
        assert kid.alive >= 0, "3 pisos de caída matan (canon)"
        assert kid.hp_curr == 0

    def test_feather_fall_saves_any_height(self) -> None:
        kid = _drop_kid(_stacked_level(4), float_ticks=500)
        assert kid.alive < 0, "Con FLOAT activa ninguna caída mata"
        assert kid.hp_curr == 3

    def test_landing_records_impact_speed(self) -> None:
        kid = _drop_kid(_stacked_level(3))
        assert kid.landed_fall_y > 0, "landed_fall_y debe registrar la velocidad de impacto"


class TestAbyss:
    def test_falling_without_south_room_dies(self) -> None:
        level = _corridor_level(pit_cols=(5,))
        kid = _kid(level, curr_col=5)
        for _ in range(30):
            kid = step_physics(kid, level)
            if kid.alive >= 0:
                break
        assert kid.alive >= 0, "Caer al abismo (sin link sur) debería matar"


class TestHorizontalCollision:
    def test_wall_blocks_body(self) -> None:
        level = _corridor_level(wall_col=4)
        room = level.room(1)
        assert blocks_body_at(room, 4, 1)
        kid = _kid(level, curr_col=3, curr_seq_id=int(Seq.RUN), action=Action.RUN_JUMP)
        for _ in range(20):
            kid = step_physics(kid, level)
            if kid.action is Action.BUMPED:
                break
        assert kid.curr_col < 4, f"El kid atravesó el muro (col={kid.curr_col})"

    def test_pillar_does_not_block(self) -> None:
        top = [E] * 10
        mid = [E] * 10
        bot = [F] * 10
        mid[4] = Tile.BIGPILLAR_TOP
        room = _room([top, mid, bot])
        assert not blocks_body_at(room, 4, 1), "Los pilares son decorado — no bloquean"

    def test_closed_gate_blocks_open_gate_does_not(self) -> None:
        level = _corridor_level()
        room = level.room(1)
        fg = list(room.fg)
        fg[1 * 10 + 4] = encode_tile(G, 0)
        room2 = Room(id=1, fg=tuple(fg), bg=room.bg)
        assert blocks_body_at(room2, 4, 1)
        assert not blocks_body_at(room2, 4, 1, frozenset({(1, 4, 1)}))


class TestFeatherFall:
    def test_float_potion_slows_fall(self) -> None:
        level = _corridor_level()
        kid_normal = _kid(level, curr_row=0, action=Action.IN_FREEFALL, curr_seq_id=int(Seq.FALL))
        kid_feather = replace(kid_normal, float_ticks=100)
        kid_normal = step_physics(kid_normal, level)
        kid_feather = step_physics(kid_feather, level, has_feather=True)
        assert kid_feather.fall_y < kid_normal.fall_y


class TestPotionEffects:
    def test_float_potion_sets_float_ticks(self) -> None:
        from pop2026canon.domain.levels_canon import LEVEL_4

        # L4 sala 18 col 5 row 1 tiene la potion FLOAT
        coord = None
        for rm in LEVEL_4.rooms:
            for r in range(3):
                for c in range(10):
                    tile, mod = rm.tile_at(c, r)
                    if tile is Tile.POTION and mod == int(PotionType.FLOAT):
                        coord = (rm.id, c, r)
        assert coord is not None
        g = new_game(LEVEL_4)
        g = replace(g, kid=replace(g.kid, room=coord[0], curr_col=coord[1], curr_row=coord[2]))
        g = advance(g, Command())
        assert g.kid.float_ticks > 0, "La poción FLOAT debe activar caída-pluma"

    def test_time_potion_adds_time(self) -> None:
        from pop2026canon.domain.levels_canon import LEVEL_5

        coord = None
        for rm in LEVEL_5.rooms:
            for r in range(3):
                for c in range(10):
                    tile, mod = rm.tile_at(c, r)
                    if tile is Tile.POTION and mod == int(PotionType.TIME):
                        coord = (rm.id, c, r)
        assert coord is not None
        from pop2026canon.domain.game import TimeRemaining

        g = new_game(LEVEL_5)
        # Con el reloj a tope el bonus se recorta (nunca sobre 60 min);
        # reducimos el reloj para ver el efecto.
        g = replace(g, time=TimeRemaining(minutes=30, ticks=0))
        before = g.time.minutes * 720 + g.time.ticks
        g = replace(g, kid=replace(g.kid, room=coord[0], curr_col=coord[1], curr_row=coord[2]))
        g = advance(g, Command())
        after = g.time.minutes * 720 + g.time.ticks
        assert after > before, "La poción TIME debe añadir tiempo al reloj"

    def test_max_hp_potion_caps_at_10(self) -> None:
        from pop2026canon.domain.combat import heal_max

        kid = Char(charid=CharId.KID, room=1, curr_col=1, curr_row=1, hp_curr=10, hp_max=10)
        kid = heal_max(kid)
        assert kid.hp_max == 10, "MAX_HITP_ALLOWED es 10"


class TestPrincessReunionWins:
    def test_reaching_princess_wins_game(self) -> None:
        from pop2026canon.domain.levels_canon import LEVEL_14

        g = new_game(LEVEL_14)
        g = advance(g, Command())  # spawn princesa
        princess = g.find_char(CharId.PRINCESS)
        assert princess is not None
        g = replace(
            g,
            kid=replace(
                g.kid,
                room=princess.room,
                curr_col=princess.curr_col - 1,
                curr_row=princess.curr_row,
            ),
        )
        g = advance(g, Command())
        assert g.status is GameStatus.WON_GAME, "Alcanzar a la princesa debe ganar el juego"
