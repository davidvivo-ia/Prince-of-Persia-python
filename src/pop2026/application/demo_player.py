"""Reproductor de demo determinista.

Genera una secuencia de :class:`InputFrame` a partir de una seed y una
política sencilla, en orden de prioridad:

1. Si hay guardia adyacente: alterna ``STRIKE`` y ``PARRY`` con
   probabilidad influida por el RNG.
2. Si la celda de delante es sólida (pared o cornisa): pide ``UP`` para
   trepar.
3. Si la celda inmediatamente delante es sólida y la de delante-arriba
   también, intenta saltar.
4. En cualquier otro caso, ``RIGHT``.

La misma seed produce la misma demo, lo que permite tests E2E y
reproducción de partidas grabadas.
"""

from __future__ import annotations

from collections.abc import Iterable

from pop2026.domain.actions import Action, duration_ticks
from pop2026.domain.game import Game, advance
from pop2026.domain.geometry import Facing, Position
from pop2026.domain.input import InputFrame, PlayerCommand
from pop2026.domain.level import Level, LevelState, effective_tile
from pop2026.domain.ports import Rng
from pop2026.domain.tiles import SOLID, Tile


def _front_solid(game: Game) -> bool:
    target = game.prince.pos.step(game.prince.facing)
    return effective_tile(game.level, game.state, target) in SOLID


def _can_climb_up_from(level: Level, state: LevelState, pos: Position, facing: Facing) -> bool:
    """¿Hay una cornisa accesible delante para trepar desde ``pos``?"""
    fwd = pos.step(facing)
    above_fwd = fwd.shifted(drow=-1)
    above = pos.shifted(drow=-1)
    landing = fwd.shifted(drow=-2)
    eff = effective_tile
    return (
        eff(level, state, above_fwd) in SOLID
        and eff(level, state, fwd) not in SOLID
        and eff(level, state, above) not in SOLID
        and eff(level, state, landing) not in SOLID
    )


def _can_climb_up(game: Game) -> bool:
    return _can_climb_up_from(game.level, game.state, game.prince.pos, game.prince.facing)


def _climb_after_step(game: Game) -> bool:
    """¿Tendrá oportunidad de trepar tras avanzar un paso?"""
    next_pos = game.prince.pos.step(game.prince.facing)
    return _can_climb_up_from(game.level, game.state, next_pos, game.prince.facing)


def _front_is_spike(game: Game) -> bool:
    target = game.prince.pos.step(game.prince.facing)
    return effective_tile(game.level, game.state, target) is Tile.SPIKES


def _gap_under_front(game: Game) -> bool:
    """¿No hay suelo bajo la celda inmediatamente delante?"""
    target = game.prince.pos.step(game.prince.facing)
    below = Position(target.row + 1, target.col)
    return effective_tile(game.level, game.state, below) not in SOLID


def _guard_in_strike_range(game: Game) -> bool:
    """``True`` si hay un guardia dentro de `attack_reach` (distancia continua)."""
    p = game.prince
    return any(
        g.alive and g.pos.row == p.pos.row and abs(p.body.pos.x - (g.pos.col + 0.5)) <= 1.0
        for g in game.guards
    )


def _guard_in_combat_range(game: Game) -> bool:
    """``True`` si hay un guardia a ≤ 2 celdas (zona ADVANCE/RETREAT)."""
    p = game.prince
    return any(
        g.alive and g.pos.row == p.pos.row and abs(p.body.pos.x - (g.pos.col + 0.5)) <= 2.0
        for g in game.guards
    )


def _guard_dir(game: Game) -> int:
    """Signo (+1/-1) del guardia más cercano en la misma fila."""
    p = game.prince
    best_dir = 1
    best = float("inf")
    for g in game.guards:
        if not g.alive or g.pos.row != p.pos.row:
            continue
        dx = (g.pos.col + 0.5) - p.body.pos.x
        if abs(dx) < best:
            best = abs(dx)
            best_dir = 1 if dx >= 0 else -1
    return best_dir


def _guard_adjacent(game: Game) -> bool:
    """Compat: alias de `_guard_in_strike_range`."""
    return _guard_in_strike_range(game)


def decide(game: Game, rng: Rng) -> InputFrame:
    """Decide el siguiente input según el estado y un RNG determinista."""
    p = game.prince

    if p.action is Action.DEAD:
        return InputFrame()

    # Si está colgado, sube a la repisa para no quedarse pendiendo.
    if p.action is Action.HANG:
        return InputFrame(command=PlayerCommand.UP)

    if _guard_in_strike_range(game) and p.has_sword:
        # Si algún guardia dentro del alcance está atacando, parar.
        from pop2026.domain.actions import is_within_window

        for gd in game.guards:
            if (
                gd.alive
                and gd.pos.row == p.pos.row
                and abs(p.body.pos.x - (gd.pos.col + 0.5)) <= 1.0
                and is_within_window(gd.action, gd.ticks_in_action)
            ):
                return InputFrame(command=PlayerCommand.PARRY)
        if rng.coin(0.75):
            return InputFrame(command=PlayerCommand.STRIKE)
        return InputFrame(command=PlayerCommand.PARRY)

    # Guardia en zona de combate (≤2 celdas) pero aún fuera del sable:
    # avanza con LEFT/RIGHT para activar ADVANCE y cerrar la distancia.
    if _guard_in_combat_range(game) and p.has_sword:
        direction = _guard_dir(game)
        cmd = PlayerCommand.RIGHT if direction > 0 else PlayerCommand.LEFT
        return InputFrame(command=cmd)

    # Pinchos, pared o hueco delante: salta SIN soltar el avance.
    # Pasamos `jump_pressed=True` para activar el buffer en paralelo a
    # la dirección, manteniendo el momento horizontal en el aire.
    needs_jump = _front_is_spike(game) or _front_solid(game) or _gap_under_front(game)
    if needs_jump:
        return _step_command(game, jump=True)

    return _step_command(game)


def _step_command(game: Game, *, jump: bool = False) -> InputFrame:
    """Comando direccional. Si ``jump=True``, dispara JUMP en paralelo."""
    p = game.prince
    cmd = PlayerCommand.RIGHT if p.facing.value > 0 else PlayerCommand.LEFT
    return InputFrame(command=cmd, jump_pressed=jump, jump_held=jump)


def play(
    game: Game,
    rng: Rng,
    *,
    max_frames: int = 6_000,
) -> Iterable[Game]:
    """Itera ticks hasta que el juego termine o se alcance ``max_frames``."""
    yield game
    for _ in range(max_frames):
        if not game.running:
            return
        inp = decide(game, rng)
        game = advance(game, inp, rng)
        yield game


def run_to_completion(
    game: Game,
    rng: Rng,
    *,
    max_frames: int = 6_000,
) -> Game:
    """Ejecuta la demo y devuelve el último estado."""
    last = game
    for g in play(game, rng, max_frames=max_frames):
        last = g
    return last
