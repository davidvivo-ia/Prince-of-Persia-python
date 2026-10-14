"""Progreso: medallas, récords, desbloqueo, persistencia tolerante y
navegación de la pantalla de niveles."""

from __future__ import annotations

from pathlib import Path

from pop2026canon.application.session import new_session
from pop2026canon.application.stats import LevelStats
from pop2026canon.domain.levels_canon import CANON_LEVELS
from pop2026canon.infrastructure import progress as pio
from pop2026canon.infrastructure.progress import (
    MEDALS,
    PAR_SECONDS,
    LevelRecord,
    Progress,
    medals_for,
    record_campaign_won,
    record_level,
)
from pop2026canon.presentation.input_device import UiAction
from pop2026canon.presentation.screens.levels import LevelSelect


def _stats(
    level: int, *, ticks: int, deaths: int = 0, rewound: int = 0, visited: int = 1
) -> LevelStats:
    st = LevelStats(level=level, ticks=ticks, deaths=deaths, rewound_ticks=rewound)
    st.visited = set(range(1, visited + 1))
    return st


class TestMedals:
    def test_perfect_run_gets_everything(self) -> None:
        st = _stats(1, ticks=12 * 100, visited=18)
        assert medals_for(st, 18) == MEDALS

    def test_dying_or_rewinding_loses_flawless(self) -> None:
        assert "flawless" not in medals_for(_stats(1, ticks=1, deaths=1), 18)
        assert "flawless" not in medals_for(_stats(1, ticks=1, rewound=5), 18)

    def test_slow_run_is_not_swift(self) -> None:
        slow = _stats(3, ticks=12 * (PAR_SECONDS[3] + 1))
        assert "swift" not in medals_for(slow, 18)
        assert "completed" in medals_for(slow, 18)

    def test_every_level_has_a_par_time(self) -> None:
        assert set(PAR_SECONDS) == set(range(1, 15))


class TestRecords:
    def test_record_unlocks_next_and_keeps_best(self) -> None:
        p = Progress()
        p, earned, new = record_level(p, _stats(1, ticks=2400, deaths=2), 18)
        assert p.unlocked == 2
        assert earned == ("completed",) or "completed" in earned
        assert new == earned
        rec = p.record(1)
        assert rec.completed
        assert rec.best_ticks == 2400
        assert rec.best_deaths == 2
        p, earned, new = record_level(p, _stats(1, ticks=1200, deaths=0, visited=18), 18)
        rec = p.record(1)
        assert rec.best_ticks == 1200
        assert rec.best_deaths == 0
        assert set(rec.medals) == set(MEDALS)
        assert "completed" not in new
        assert "flawless" in new

    def test_medals_are_never_lost(self) -> None:
        p = Progress(levels={2: LevelRecord(True, 100, 0, ("completed", "flawless"))})
        p, _, new = record_level(p, _stats(2, ticks=99999, deaths=3), 20)
        assert "flawless" in p.record(2).medals
        assert new == ()

    def test_campaign_won_unlocks_all(self) -> None:
        p = record_campaign_won(Progress())
        assert p.unlocked == 14
        assert p.campaigns_won == 1


class TestPersistence:
    def test_round_trip(self, tmp_path: Path) -> None:
        p = Progress(
            unlocked=5,
            levels={3: LevelRecord(True, 777, 1, ("completed", "swift"))},
            campaigns_won=1,
        )
        pio.save(p, tmp_path / "progress.json")
        assert pio.load(tmp_path / "progress.json") == p

    def test_garbage_is_ignored(self) -> None:
        assert pio.from_json("not json") == Progress()
        assert pio.from_json(
            '{"unlocked": "x", "levels": {"99": {}, "a": {}, "2": {"medals": ["bogus", "swift"]}}}'
        ).record(2).medals == ("swift",)
        assert pio.from_json('{"unlocked": 99}').unlocked == 14

    def test_missing_file(self, tmp_path: Path) -> None:
        assert pio.load(tmp_path / "nope.json") == Progress()


class TestLevelSelect:
    def test_navigation_wraps_and_respects_locks(self) -> None:
        ui = LevelSelect(Progress(unlocked=3))
        assert ui.handle(UiAction.LEFT) == "_move"
        assert ui.level == 14
        assert ui.handle(UiAction.RIGHT) == "_move"
        assert ui.level == 1
        assert ui.handle(UiAction.DOWN) == "_move"
        assert ui.level == 8
        assert ui.handle(UiAction.CONFIRM) == "locked"
        ui.index = 2
        assert ui.handle(UiAction.CONFIRM) == "start"
        assert ui.handle(UiAction.BACK) == "back"

    def test_new_session_scales_hp_and_hard_mode(self) -> None:
        s = new_session(7)
        assert s.hp_max == 6
        assert s.time.minutes == 60
        assert not s.hard
        hard = new_session(1, hard=True)
        g = hard.start_game()
        assert hard.time.minutes == 45
        base = new_session(1).start_game()
        for a, b in zip(base.others, g.others, strict=True):
            assert b.skill == min(11, a.skill + 2)
        assert len(CANON_LEVELS) == 14
