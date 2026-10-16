"""Fantasma del récord: la mejor carrera de cada nivel, grabada tick a
tick como entradas del jugador y reproducida con el motor real como un
kid translúcido que corre a tu lado.

- :func:`encode_commands` / :func:`decode_commands`: un token por tick
  (``L R U D S A``, ``.`` = nada). Es el mismo formato que los replays
  de los tests.
- :class:`GhostRecorder`: acumula las entradas de la partida en curso.
  Rebobinar quita ticks; morir (reaparecer en la sala o reiniciar el
  nivel) invalida la grabación: el fantasma sólo nace de una carrera
  limpia desde la entrada del nivel hasta la salida.
- :class:`GhostRun`: la carrera guardada (nivel, condiciones iniciales
  y entradas) con su fichero de texto.
- :class:`GhostPlayer`: avanza su propio ``Game`` con las entradas
  grabadas, un tick por tick del jugador; expone el kid para dibujarlo.

Todo puro salvo ``load``/``save``.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path

from pop2026canon.application.controller import Command
from pop2026canon.application.tick import advance
from pop2026canon.domain.chars import Char
from pop2026canon.domain.game import Game, GameStatus, new_game
from pop2026canon.domain.level import Level

FLAGS: tuple[tuple[str, str], ...] = (
    ("left", "L"),
    ("right", "R"),
    ("up", "U"),
    ("down", "D"),
    ("shift", "S"),
    ("strike", "A"),
)
NOOP = Command()
FORMAT_VERSION = 1


def encode_commands(cmds: list[Command]) -> str:
    out = []
    for c in cmds:
        token = "".join(ch for attr, ch in FLAGS if getattr(c, attr))
        out.append(token or ".")
    return " ".join(out)


def decode_commands(text: str) -> list[Command]:
    cmds = []
    for token in text.split():
        if token == ".":
            cmds.append(NOOP)
            continue
        cmds.append(Command(**{attr: ch in token for attr, ch in FLAGS}))
    return cmds


# ---------------------------------------------------------------------------
# Grabación
# ---------------------------------------------------------------------------


@dataclass
class GhostRecorder:
    """Entradas de la carrera en curso. ``valid`` se apaga al morir."""

    commands: list[Command] = field(default_factory=list)
    valid: bool = True

    def record(self, cmd: Command) -> None:
        self.commands.append(cmd)

    def rewind(self, ticks: int = 1) -> None:
        """Al rebobinar un tick se olvida la última entrada."""
        for _ in range(min(ticks, len(self.commands))):
            self.commands.pop()

    def invalidate(self) -> None:
        self.valid = False

    def reset(self) -> None:
        self.commands.clear()
        self.valid = True

    @property
    def ticks(self) -> int:
        return len(self.commands)


# ---------------------------------------------------------------------------
# Carrera guardada
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GhostRun:
    level: int
    hp: int
    has_sword: bool
    hard: bool
    commands: tuple[Command, ...]

    @property
    def ticks(self) -> int:
        return len(self.commands)

    @property
    def clock(self) -> str:
        s = self.ticks // 12
        return f"{s // 60:d}:{s % 60:02d}"

    def to_text(self) -> str:
        head = (
            f"pop2026canon-ghost v{FORMAT_VERSION} level={self.level} hp={self.hp} "
            f"sword={int(self.has_sword)} hard={int(self.hard)} ticks={self.ticks}"
        )
        return head + "\n" + encode_commands(list(self.commands)) + "\n"

    @classmethod
    def from_text(cls, text: str) -> GhostRun | None:
        lines = text.strip().splitlines()
        if len(lines) < 2 or not lines[0].startswith("pop2026canon-ghost"):
            return None
        fields: dict[str, str] = {}
        for tok in lines[0].split()[2:]:
            if "=" in tok:
                k, v = tok.split("=", 1)
                fields[k] = v
        try:
            level = int(fields["level"])
            hp = int(fields.get("hp", 3))
            has_sword = fields.get("sword", "0") == "1"
            hard = fields.get("hard", "0") == "1"
        except (KeyError, ValueError):
            return None
        cmds = decode_commands(" ".join(lines[1:]))
        if not cmds:
            return None
        return cls(level, hp, has_sword, hard, tuple(cmds))


def ghost_path(level_number: int, base: Path | None = None) -> Path:
    root = base if base is not None else Path.home() / ".local" / "share" / "pop2026canon"
    return root / "ghosts" / f"L{level_number:02d}.txt"


def load_ghost(level_number: int, base: Path | None = None) -> GhostRun | None:
    try:
        return GhostRun.from_text(ghost_path(level_number, base).read_text(encoding="utf-8"))
    except OSError:
        return None


def save_ghost(run: GhostRun, base: Path | None = None) -> None:
    p = ghost_path(run.level, base)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(run.to_text(), encoding="utf-8")


def better_run(current: GhostRun | None, candidate: GhostRun) -> bool:
    """Un fantasma nuevo sustituye al guardado si es más rápido (o no hay)."""
    return current is None or candidate.ticks < current.ticks


# ---------------------------------------------------------------------------
# Reproducción
# ---------------------------------------------------------------------------


def _start_game(level: Level, run: GhostRun) -> Game:
    game = new_game(level, starting_hp=run.hp, has_sword=run.has_sword)
    if run.hard:
        from pop2026canon.application.session import HARD_MAX_SKILL, HARD_SKILL_BONUS

        game = replace(
            game,
            others=tuple(
                replace(c, skill=min(HARD_MAX_SKILL, c.skill + HARD_SKILL_BONUS))
                for c in game.others
            ),
        )
    return game


@dataclass
class GhostPlayer:
    """Reproduce ``run`` sobre ``level`` en paralelo a la partida."""

    level: Level
    run: GhostRun
    game: Game = field(init=False)
    prev: Game = field(init=False)
    tick: int = 0

    def __post_init__(self) -> None:
        self.game = _start_game(self.level, self.run)
        self.prev = self.game

    def step(self) -> None:
        """Un tick del jugador = un tick del fantasma (hasta agotar la cinta)."""
        if self.finished:
            return
        self.prev = self.game
        self.game = advance(self.game, self.run.commands[self.tick])
        self.tick += 1

    def step_back(self) -> None:
        """Al rebobinar, el fantasma se recoloca recalculando desde el
        principio (barato: las carreras duran uno o dos minutos)."""
        target = max(0, self.tick - 1)
        self.game = _start_game(self.level, self.run)
        self.prev = self.game
        self.tick = 0
        while self.tick < target:
            self.step()

    def seek(self, tick: int) -> None:
        if tick < self.tick:
            self.game = _start_game(self.level, self.run)
            self.prev = self.game
            self.tick = 0
        while self.tick < min(tick, self.run.ticks):
            self.step()

    @property
    def finished(self) -> bool:
        return self.tick >= self.run.ticks or not self.game.running

    @property
    def kid(self) -> Char:
        return self.game.kid

    @property
    def prev_kid(self) -> Char:
        return self.prev.kid

    def visible_in(self, room: int) -> bool:
        return not self.finished and self.game.kid.room == room and self.game.kid.alive < 0


def run_from_recording(
    level: Level, rec: GhostRecorder, *, hp: int, has_sword: bool, hard: bool
) -> GhostRun | None:
    """La carrera grabada como :class:`GhostRun`, si es válida y gana."""
    if not rec.valid or not rec.commands:
        return None
    run = GhostRun(level.number, hp, has_sword, hard, tuple(rec.commands))
    player = GhostPlayer(level, run)
    while not player.finished:
        player.step()
    if player.game.status not in (GameStatus.WON_LEVEL, GameStatus.WON_GAME):
        return None
    return run


def delta_text(ticks: int, record: int | None) -> str:
    """``"-4.2 s"`` / ``"+1.0 s"`` respecto al récord (vacío si no hay)."""
    if record is None:
        return ""
    d = (ticks - record) / 12
    sign = "+" if d > 0 else "-"
    return f"{sign}{abs(d):.1f} s"


__all__: list[str] = [
    "FLAGS",
    "NOOP",
    "GhostPlayer",
    "GhostRecorder",
    "GhostRun",
    "better_run",
    "decode_commands",
    "delta_text",
    "encode_commands",
    "ghost_path",
    "load_ghost",
    "run_from_recording",
    "save_ghost",
]
