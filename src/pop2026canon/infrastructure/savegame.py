"""Save slots — formato JSON simple para snapshot/load del juego."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from pop2026canon.domain.actions import SwordStatus
from pop2026canon.domain.game import Game, GameFlags, GameStatus, TimeRemaining
from pop2026canon.domain.levels_canon import load_canon

SAVE_VERSION = 2


@dataclass(frozen=True, slots=True)
class SaveSlot:
    """Snapshot canónico del juego."""

    version: int
    level: int
    kid_room: int
    kid_col: int
    kid_row: int
    kid_direction: int
    kid_hp_curr: int
    kid_hp_max: int
    kid_sword: int
    minutes_left: int
    ticks_left: int
    sword_picked: bool
    shadow_initialized: bool
    shadow_stole_potion: bool
    shadow_fused: bool
    skeleton_woke: bool
    mouse_appeared: bool
    deaths: int = 0
    """Muertes acumuladas de la campaña (estadística de sesión)."""


def save_game(game: Game, *, deaths: int = 0) -> SaveSlot:
    """Construye un SaveSlot a partir del Game actual."""
    return SaveSlot(
        version=SAVE_VERSION,
        deaths=deaths,
        level=game.level.number,
        kid_room=game.kid.room,
        kid_col=game.kid.curr_col,
        kid_row=game.kid.curr_row,
        kid_direction=game.kid.direction,
        kid_hp_curr=game.kid.hp_curr,
        kid_hp_max=game.kid.hp_max,
        kid_sword=int(game.kid.sword),
        minutes_left=game.time.minutes,
        ticks_left=game.time.ticks,
        sword_picked=game.flags.sword_picked,
        shadow_initialized=game.flags.shadow_initialized,
        shadow_stole_potion=game.flags.shadow_stole_potion,
        shadow_fused=game.flags.shadow_fused,
        skeleton_woke=game.flags.skeleton_woke,
        mouse_appeared=game.flags.mouse_appeared,
    )


def load_save(slot: SaveSlot) -> Game:
    """Restaura un Game a partir de un SaveSlot."""
    from dataclasses import replace as _replace

    from pop2026canon.domain.game import new_game

    level = load_canon(slot.level)
    game = new_game(level, starting_hp=slot.kid_hp_max)
    new_kid = _replace(
        game.kid,
        room=slot.kid_room,
        curr_col=slot.kid_col,
        curr_row=slot.kid_row,
        direction=slot.kid_direction,
        hp_curr=slot.kid_hp_curr,
        hp_max=slot.kid_hp_max,
        sword=SwordStatus(slot.kid_sword),
    )
    flags = GameFlags(
        sword_picked=slot.sword_picked,
        shadow_initialized=slot.shadow_initialized,
        shadow_stole_potion=slot.shadow_stole_potion,
        shadow_fused=slot.shadow_fused,
        skeleton_woke=slot.skeleton_woke,
        mouse_appeared=slot.mouse_appeared,
    )
    return _replace(
        game,
        kid=new_kid,
        time=TimeRemaining(minutes=slot.minutes_left, ticks=slot.ticks_left),
        flags=flags,
        status=GameStatus.PLAYING,
    )


def write_to_disk(slot: SaveSlot, path: Path) -> None:
    """Persiste el slot en disco como JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(slot), indent=2), encoding="utf-8")


def read_from_disk(path: Path) -> SaveSlot:
    """Carga un slot desde JSON. Lanza si la versión no es compatible."""
    data = json.loads(path.read_text(encoding="utf-8"))
    version = data.get("version")
    if version == 1:
        # v1 no tenía contador de muertes — migra sobre la marcha.
        data["version"] = SAVE_VERSION
        data.setdefault("deaths", 0)
    elif version != SAVE_VERSION:
        raise ValueError(f"save version {version} != {SAVE_VERSION}")
    return SaveSlot(**data)


def default_save_path() -> Path:
    """Ubicación XDG estándar para el save slot por defecto."""
    home = Path.home()
    xdg = Path(home / ".local" / "share" / "pop2026canon")
    return xdg / "save.json"
