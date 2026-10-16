"""Fantasma del récord, música por ambiente, poses de la princesa y
resumen de campaña."""

from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import numpy as np
import pygame
import pytest

from pop2026canon.application import ghost as gh
from pop2026canon.application.controller import Command
from pop2026canon.application.session import Session
from pop2026canon.application.stats import LevelStats
from pop2026canon.application.tick import advance
from pop2026canon.domain.game import GameStatus, new_game
from pop2026canon.domain.levels_canon import CANON_LEVELS
from pop2026canon.infrastructure import audio
from pop2026canon.infrastructure.settings import Settings
from pop2026canon.presentation import poses
from pop2026canon.presentation.layout import LAYOUT
from pop2026canon.presentation.scene import Scene
from pop2026canon.presentation.screens import cinematic, cutscene, ending
from pop2026canon.presentation.themes import theme_for

REPLAYS = Path(__file__).parent / "replays"


@pytest.fixture(scope="module", autouse=True)
def _pygame() -> None:
    pygame.init()


def _l1_run() -> gh.GhostRun:
    cmds = gh.decode_commands((REPLAYS / "L1.txt").read_text(encoding="utf-8"))
    return gh.GhostRun(level=1, hp=3, has_sword=False, hard=False, commands=tuple(cmds))


class TestEncoding:
    def test_round_trip(self) -> None:
        cmds = [
            Command(),
            Command(right=True),
            Command(right=True, up=True),
            Command(shift=True, strike=True),
            Command(left=True, down=True),
        ]
        text = gh.encode_commands(cmds)
        assert text == ". R RU SA LD"
        assert gh.decode_commands(text) == cmds

    def test_run_text_round_trip(self) -> None:
        run = gh.GhostRun(7, 5, True, True, (Command(right=True), Command()))
        back = gh.GhostRun.from_text(run.to_text())
        assert back == run
        assert run.clock == "0:00"
        assert gh.GhostRun.from_text("basura") is None
        assert gh.GhostRun.from_text("pop2026canon-ghost v1 level=x\nR") is None

    def test_save_and_load(self, tmp_path: Path) -> None:
        run = gh.GhostRun(3, 4, True, False, (Command(left=True),) * 5)
        assert gh.load_ghost(3, tmp_path) is None
        gh.save_ghost(run, tmp_path)
        assert gh.ghost_path(3, tmp_path).exists()
        assert gh.load_ghost(3, tmp_path) == run

    def test_better_run_and_delta(self) -> None:
        short = gh.GhostRun(1, 3, False, False, (Command(),) * 24)
        long = gh.GhostRun(1, 3, False, False, (Command(),) * 36)
        assert gh.better_run(None, long)
        assert gh.better_run(long, short)
        assert not gh.better_run(short, long)
        assert gh.delta_text(36, 24) == "+1.0 s"
        assert gh.delta_text(24, 36) == "-1.0 s"
        assert gh.delta_text(24, None) == ""


class TestRecorder:
    def test_rewind_pops_and_death_invalidates(self) -> None:
        rec = gh.GhostRecorder()
        for _ in range(5):
            rec.record(Command(right=True))
        rec.rewind(2)
        assert rec.ticks == 3
        rec.rewind(10)
        assert rec.ticks == 0
        rec.record(Command())
        rec.invalidate()
        assert not rec.valid
        rec.reset()
        assert rec.valid
        assert rec.ticks == 0


class TestPlayer:
    def test_replay_wins_level_1(self) -> None:
        run = _l1_run()
        player = gh.GhostPlayer(CANON_LEVELS[0], run)
        while not player.finished:
            player.step()
        assert player.game.status is GameStatus.WON_LEVEL
        assert player.tick <= run.ticks

    def test_step_back_and_seek_are_consistent(self) -> None:
        run = _l1_run()
        a = gh.GhostPlayer(CANON_LEVELS[0], run)
        for _ in range(60):
            a.step()
        pos60 = (a.kid.room, a.kid.curr_col, a.kid.x, a.kid.frame)
        a.step()
        a.step_back()
        assert (a.kid.room, a.kid.curr_col, a.kid.x, a.kid.frame) == pos60
        b = gh.GhostPlayer(CANON_LEVELS[0], run)
        b.seek(60)
        assert (b.kid.room, b.kid.curr_col, b.kid.x, b.kid.frame) == pos60
        b.seek(30)
        assert b.tick == 30

    def test_recording_becomes_a_run_only_if_it_wins(self) -> None:
        run = _l1_run()
        rec = gh.GhostRecorder(commands=list(run.commands))
        out = gh.run_from_recording(CANON_LEVELS[0], rec, hp=3, has_sword=False, hard=False)
        assert out is not None
        assert out.ticks == run.ticks
        bad = gh.GhostRecorder(commands=[Command()] * 40)
        assert (
            gh.run_from_recording(CANON_LEVELS[0], bad, hp=3, has_sword=False, hard=False) is None
        )
        rec.invalidate()
        assert (
            gh.run_from_recording(CANON_LEVELS[0], rec, hp=3, has_sword=False, hard=False) is None
        )

    def test_hard_runs_bump_guard_skill(self) -> None:
        run = gh.GhostRun(2, 3, True, True, (Command(),))
        normal = gh.GhostPlayer(CANON_LEVELS[1], gh.GhostRun(2, 3, True, False, (Command(),)))
        hard = gh.GhostPlayer(CANON_LEVELS[1], run)
        assert max(c.skill for c in hard.game.others) > max(c.skill for c in normal.game.others)


class TestSceneGhost:
    def test_ghost_is_drawn_when_in_the_same_room(self) -> None:
        run = _l1_run()
        lv = CANON_LEVELS[0]
        g = new_game(lv)
        player = gh.GhostPlayer(lv, run)
        for _ in range(12):
            player.step()
        assert player.visible_in(g.kid.room)
        sc = Scene(Settings(lighting=False, cinematic=False, bloom=False, particles=False))
        sc.on_level_start(g)
        canvas = pygame.Surface((LAYOUT.window_w, LAYOUT.window_h))
        sc.draw(canvas, g, g, 1.0, 0.1, sand=None, rewinding=False, show_time=False)
        plain = pygame.surfarray.array3d(canvas).copy()
        sc.draw(canvas, g, g, 1.0, 0.1, sand=None, rewinding=False, show_time=False, ghost=player)
        with_ghost = pygame.surfarray.array3d(canvas)
        assert (plain != with_ghost).any()
        assert not player.visible_in(g.kid.room + 1)


@pytest.fixture
def app_factory(tmp_path: Path):  # type: ignore[no-untyped-def]
    from pop2026canon.presentation import app as app_mod

    def make() -> app_mod.GameApp:
        app = app_mod.GameApp(
            session=Session(level_number=1, levels=CANON_LEVELS),
            campaign_levels=CANON_LEVELS,
            autosave_enabled=False,
            skip_intro=True,
            settings_path=tmp_path / "s.json",
            save_path=tmp_path / "save.json",
            progress_path=tmp_path / "p.json",
        )
        app.input.rewind_held = lambda: False  # type: ignore[method-assign]
        return app

    return make


class TestAppGhost:
    def _tick(self, app, cmd: Command) -> None:  # type: ignore[no-untyped-def]
        app.input.command = lambda: cmd  # type: ignore[method-assign]
        for _ in range(5):
            app._playing([])

    def test_recording_follows_play_and_rewind(self, app_factory) -> None:  # type: ignore[no-untyped-def]
        app = app_factory()
        app._start_level()
        app.phase = "playing"
        assert app.ghost is None, "sin récord guardado no hay fantasma"
        for _ in range(6):
            self._tick(app, Command(right=True))
        assert app.recorder.ticks == 6
        app.rewind_frames = 1
        app.input.rewind_held = lambda: True  # type: ignore[method-assign]
        app._playing([])
        assert app.recorder.ticks == 5

    def test_winning_run_is_saved_and_replayed_next_time(self, app_factory, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
        app = app_factory()
        app._start_level()
        app.phase = "playing"
        run = _l1_run()
        app.recorder = gh.GhostRecorder(commands=list(run.commands))
        # Simula el final del nivel: el juego termina en WON_LEVEL
        player = gh.GhostPlayer(CANON_LEVELS[0], run)
        while not player.finished:
            player.step()
        app.game = player.game
        app.stats = LevelStats(level=1)
        app._on_level_end()
        assert app.new_record
        assert gh.load_ghost(1, tmp_path) is not None
        # Al empezar el nivel otra vez, el fantasma corre al lado
        app.game = app.session.start_game()
        app._start_level()
        assert app.ghost is not None
        assert app.record is not None
        assert app.record.ticks == run.ticks
        self._tick(app, Command())
        assert app.ghost.tick == 1

    def test_ghost_setting_can_be_switched_off(self, app_factory, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
        gh.save_ghost(_l1_run(), tmp_path)
        app = app_factory()
        app._start_level()
        assert app.ghost is not None
        app.phase = "playing"
        app._apply_settings(app.settings.with_(ghost=False))
        assert app.ghost is None
        app._apply_settings(app.settings.with_(ghost=True))
        assert app.ghost is not None


class TestMusicStyles:
    def test_every_theme_music_exists(self) -> None:
        for n in range(1, 15):
            key = theme_for(n).music
            assert key in audio.MUSIC_STYLES, f"L{n}: {key}"
        assert len({theme_for(n).music for n in range(1, 15)}) >= 8

    @pytest.mark.parametrize("name", sorted(audio.MUSIC_STYLES))
    def test_style_generates_a_seamless_loop(self, name: str) -> None:
        base, combat = audio.music_layers(name)
        assert len(base) == len(combat)
        assert len(base) / audio.SR > 12
        assert float(np.max(np.abs(base))) <= 0.6
        assert float(np.sqrt(np.mean(base**2))) > 0.04

    def test_styles_differ(self) -> None:
        a, _ = audio.music_layers("tomb")
        b, _ = audio.music_layers("escape")
        assert len(a) != len(b), "tempos distintos → bucles de distinta longitud"
        assert audio.MUSIC_STYLES["escape"].bpm > audio.MUSIC_STYLES["tomb"].bpm

    def test_unknown_style_falls_back(self) -> None:
        assert audio.music_style_for("???") is audio.MUSIC_STYLES["dungeon"]


class TestPrincessAndScreens:
    def test_princess_poses_exist_and_differ(self) -> None:
        from pop2026canon.presentation.char_atlas import CharPalette, sprite

        frames = (poses.PRINCESS_WAIT, poses.PRINCESS_STARTLE, poses.PRINCESS_JOY)
        distinct = {poses.pose_for(f) for f in frames}
        assert len(distinct) == 3
        assert (
            poses.pose_for(poses.PRINCESS_JOY).uarm_n > poses.pose_for(poses.PRINCESS_WAIT).uarm_n
        )
        for f in (*frames, poses.PRINCESS_GLIDE_FIRST, poses.PRINCESS_GLIDE_LAST):
            img, _ = sprite(f, CharPalette.PRINCESS, -1)
            assert img.get_width() > 0

    @pytest.mark.parametrize("t", [9.0, 11.5, 2.5, 4.0, 7.0])
    def test_cinematics_still_draw(self, t: float) -> None:
        surf = pygame.Surface((LAYOUT.window_w, LAYOUT.window_h))
        cinematic.draw_intro(surf, t)
        cinematic.draw_ending(surf, t)

    def test_level_card_shows_the_record(self) -> None:
        surf = pygame.Surface((LAYOUT.window_w, LAYOUT.window_h))
        font = pygame.font.Font(None, 24)
        cutscene.draw_level_card(surf, CANON_LEVELS[0], font, font, 1.0)
        a = pygame.surfarray.array3d(surf).copy()
        cutscene.draw_level_card(surf, CANON_LEVELS[0], font, font, 1.0, record="1:23")
        assert (a != pygame.surfarray.array3d(surf)).any()

    def test_level_complete_and_victory_summaries(self) -> None:
        surf = pygame.Surface((LAYOUT.window_w, LAYOUT.window_h))
        stats = LevelStats(level=1, ticks=600)
        ending.draw_level_complete(
            surf,
            stats,
            "L1",
            10,
            2.0,
            medals=("completed", "swift"),
            delta="-2.0 s",
            new_record=True,
        )
        ending.draw_victory(surf, t=1.0, deaths=2, time_left="40:00", time_used="19:59", medals=12)
        assert pygame.surfarray.array3d(surf).mean() > 3


def test_session_step_matches_player_step() -> None:
    """El fantasma avanza con el mismo motor que la partida: tras los
    mismos comandos, el kid del fantasma está donde estaría el jugador."""
    run = _l1_run()
    g = new_game(CANON_LEVELS[0])
    player = gh.GhostPlayer(CANON_LEVELS[0], run)
    for cmd in run.commands[:80]:
        g = advance(g, cmd)
        player.step()
    assert (g.kid.room, g.kid.curr_col, g.kid.x, g.kid.frame) == (
        player.kid.room,
        player.kid.curr_col,
        player.kid.x,
        player.kid.frame,
    )
