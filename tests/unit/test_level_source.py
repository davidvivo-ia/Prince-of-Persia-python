"""Tests del source unificado de niveles."""

from __future__ import annotations

import pytest

from pop2026.application.level_source import HAND_CRAFTED_COUNT, load_level
from pop2026.domain.errors import LevelLoadError


class TestRange:
    def test_level_0_raises(self) -> None:
        with pytest.raises(LevelLoadError, match="fuera de rango"):
            load_level(0)

    def test_level_101_raises(self) -> None:
        with pytest.raises(LevelLoadError, match="fuera de rango"):
            load_level(101)


class TestHandCrafted:
    @pytest.mark.parametrize("idx", range(1, HAND_CRAFTED_COUNT + 1))
    def test_loads_builtin(self, idx: int) -> None:
        lv = load_level(idx)
        assert lv.prince_spawn is not None
        assert lv.cols > 0
        assert lv.rows > 0


class TestProcedural:
    @pytest.mark.parametrize("idx", [16, 25, 50, 75, 88, 100])
    def test_loads_procedural(self, idx: int) -> None:
        lv = load_level(idx, seed=42)
        assert lv.prince_spawn is not None
        assert lv.time_limit_ticks is not None
        assert lv.time_limit_ticks > 0

    def test_seed_changes_procedural_output(self) -> None:
        a = load_level(50, seed=1)
        b = load_level(50, seed=2)
        # Pueden coincidir por azar pero al menos una métrica suele diferir
        assert a.grid != b.grid or a.guard_spawns != b.guard_spawns

    def test_load_level_100_works(self) -> None:
        lv = load_level(100, seed=42)
        assert lv is not None
        assert lv.cols > 0
