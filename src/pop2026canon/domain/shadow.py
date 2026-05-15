"""Shadow man — char especial con 4 encuentros canónicos.

| Nivel | Evento | Acción |
|---|---|---|
| 4 | SHADOW_MIRROR | Nace al cruzar el espejo, corre al oeste y desaparece |
| 5 | SHADOW_STEAL | Roba la poción del kid (la consume) |
| 6 | SHADOW_STEP | Aparece cuando kid en frame 43 (mid-runjump) |
| 12 | SHADOW_FUSION | Imita al kid; al tocarse, +1 HP máximo |
"""

from __future__ import annotations

from dataclasses import replace

from pop2026canon.domain.actions import Action, Direction, Seq
from pop2026canon.domain.chars import Char, CharId
from pop2026canon.domain.game import Game
from pop2026canon.domain.level import EventKind


def trigger_shadow_encounters(game: Game) -> Game:
    """Evalúa cada evento shadow del nivel actual y actúa si procede."""
    new_game = game
    for event in game.level.events:
        if event.kind is EventKind.SHADOW_MIRROR:
            new_game = _handle_mirror(new_game, event)
        elif event.kind is EventKind.SHADOW_STEAL:
            new_game = _handle_steal(new_game, event)
        elif event.kind is EventKind.SHADOW_STEP:
            new_game = _handle_step(new_game, event)
        elif event.kind is EventKind.SHADOW_FUSION:
            new_game = _handle_fusion(new_game, event)
    return new_game


def _spawn_shadow(game: Game, room: int, col: int, row: int, direction: int) -> Game:
    """Spawnea un char SHADOW si aún no existe."""
    if game.find_char(CharId.SHADOW) is not None:
        return game
    shadow = Char(
        charid=CharId.SHADOW,
        room=room,
        curr_col=col,
        curr_row=row,
        direction=direction,
        curr_seq_id=int(Seq.RUN),
        action=Action.RUN_JUMP,
        hp_curr=3,
        hp_max=3,
    )
    return replace(game, others=(*game.others, shadow))


def _remove_shadow(game: Game) -> Game:
    """Elimina el char SHADOW del juego si existe."""
    return replace(
        game,
        others=tuple(c for c in game.others if c.charid is not CharId.SHADOW),
    )


def _handle_mirror(game: Game, event: object) -> Game:
    """L4: shadow nace al cruzar el espejo, corre al oeste y desaparece."""
    e_room = event.room  # type: ignore[attr-defined]
    e_col = event.col  # type: ignore[attr-defined]

    if not game.flags.shadow_initialized:
        # Trigger: kid está en la sala del mirror, sobre o cerca del tile
        if game.kid.room == e_room and abs(game.kid.curr_col - e_col) <= 1:
            new_flags = replace(game.flags, shadow_initialized=True)
            game = replace(game, flags=new_flags)
            game = _spawn_shadow(game, e_room, e_col, game.kid.curr_row, int(Direction.LEFT))
        return game

    # Shadow ya activo: lo movemos al oeste hasta desaparecer
    shadow = game.find_char(CharId.SHADOW)
    if shadow is None:
        return game
    if shadow.curr_col <= 0:
        return _remove_shadow(game)
    new_shadow = replace(shadow, curr_col=shadow.curr_col - 1)
    new_others = tuple(new_shadow if c.charid is CharId.SHADOW else c for c in game.others)
    return replace(game, others=new_others)


def _handle_steal(game: Game, event: object) -> Game:
    """L5: shadow roba la poción del kid en la sala objetivo."""
    e_room = event.room  # type: ignore[attr-defined]
    if game.flags.shadow_stole_potion:
        return game
    # Trigger: kid en la sala donde está la poción robable
    if game.kid.room != e_room:
        return game
    # Marca todas las potions de esa sala como consumidas
    from pop2026canon.domain.tiles import Tile

    room = game.level.room(e_room)
    new_state = game.state
    consumed_any = False
    for r in range(3):
        for c in range(10):
            tile, _ = room.tile_at(c, r)
            if tile is Tile.POTION:
                new_state = new_state.with_potion_consumed((e_room, c, r))
                consumed_any = True
    if consumed_any:
        new_flags = replace(game.flags, shadow_stole_potion=True)
        return replace(game, state=new_state, flags=new_flags)
    return game


def _handle_step(game: Game, event: object) -> Game:
    """L6: shadow aparece cuando el kid está en frame_43 (mid runjump)."""
    e_room = event.room  # type: ignore[attr-defined]
    e_frame = event.extra  # type: ignore[attr-defined]
    if game.kid.room != e_room:
        return game
    if game.kid.frame != e_frame:
        return game
    if game.flags.shadow_initialized:
        return game
    new_flags = replace(game.flags, shadow_initialized=True)
    game = replace(game, flags=new_flags)
    return _spawn_shadow(game, e_room, 5, game.kid.curr_row, int(Direction.LEFT))


def _handle_fusion(game: Game, event: object) -> Game:
    """L12: shadow imita al kid; al tocarse, +1 HP máximo."""
    e_room = event.room  # type: ignore[attr-defined]
    if game.kid.room != e_room:
        return game
    if game.flags.shadow_fused:
        return game

    shadow = game.find_char(CharId.SHADOW)
    if shadow is None:
        # Spawn shadow en el lado opuesto del kid
        spawn_col = 10 - game.kid.curr_col - 1
        new_flags = replace(game.flags, shadow_initialized=True)
        game = replace(game, flags=new_flags)
        return _spawn_shadow(
            game,
            e_room,
            spawn_col,
            game.kid.curr_row,
            int(Direction.LEFT)
            if game.kid.direction == int(Direction.RIGHT)
            else int(Direction.RIGHT),
        )

    # Detecta tocarse (mismo col±0)
    if shadow.curr_col == game.kid.curr_col and shadow.curr_row == game.kid.curr_row:
        new_kid = replace(game.kid, hp_max=game.kid.hp_max + 1, hp_curr=game.kid.hp_max + 1)
        new_flags = replace(game.flags, shadow_fused=True)
        new_game = _remove_shadow(game)
        return replace(new_game, kid=new_kid, flags=new_flags)
    return game
