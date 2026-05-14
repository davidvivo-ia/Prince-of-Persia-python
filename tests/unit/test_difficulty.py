"""Tests de la curva de dificultad."""

from __future__ import annotations

import pytest

from pop2026.application.difficulty import (
    ACT_THEMES,
    DifficultyParams,
    act_for_level,
    local_index_for_level,
    params_for,
)


class TestActMapping:
    @pytest.mark.parametrize(
        ("level", "act"),
        [
            (1, 0),
            (12, 0),
            (25, 0),
            (26, 1),
            (50, 1),
            (51, 2),
            (75, 2),
            (76, 3),
            (100, 3),
        ],
    )
    def test_act_for_level(self, level: int, act: int) -> None:
        assert act_for_level(level) == act

    @pytest.mark.parametrize(
        ("level", "local"),
        [
            (1, 0),
            (25, 24),
            (26, 0),
            (50, 24),
            (76, 0),
            (100, 24),
        ],
    )
    def test_local_index(self, level: int, local: int) -> None:
        assert local_index_for_level(level) == local

    def test_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError, match="fuera de rango"):
            act_for_level(0)
        with pytest.raises(ValueError, match="fuera de rango"):
            act_for_level(101)
        with pytest.raises(ValueError, match="fuera de rango"):
            local_index_for_level(-1)


class TestParamsForLevel:
    def test_returns_dataclass(self) -> None:
        p = params_for(1)
        assert isinstance(p, DifficultyParams)

    def test_act_field_matches(self) -> None:
        for lv in (1, 26, 51, 76):
            assert params_for(lv).act == act_for_level(lv)

    def test_boss_only_at_local_24(self) -> None:
        for lv in range(1, 101):
            local = local_index_for_level(lv)
            p = params_for(lv)
            assert p.boss_flag == (local == 24), f"L{lv} (local={local}) boss_flag={p.boss_flag}"

    def test_time_limit_is_positive(self) -> None:
        for lv in range(1, 101):
            assert params_for(lv).time_limit_seconds > 0

    def test_act_step_up(self) -> None:
        # Compara el primer nivel de cada acto con el primero del anterior.
        for act in range(1, 4):
            prev = params_for(act * 25)  # último del acto anterior (no boss base)
            curr = params_for(act * 25 + 1)  # primero del acto nuevo
            # Al menos una métrica de obstáculos sube en el escalón.
            assert (
                curr.gap_prob >= prev.gap_prob
                or curr.spike_prob >= prev.spike_prob
                or curr.loose_prob >= prev.loose_prob
                or curr.guard_count >= prev.guard_count
            ), f"acto {act} no escala respecto al anterior"

    def test_params_monotonic_within_act(self) -> None:
        # Comparando primero y último de cada acto, las métricas no decrecen.
        for act in range(4):
            first = params_for(act * 25 + 1)
            last_non_boss = params_for(act * 25 + 24)
            assert last_non_boss.gap_prob >= first.gap_prob
            assert last_non_boss.spike_prob >= first.spike_prob
            assert last_non_boss.loose_prob >= first.loose_prob
            assert last_non_boss.guard_count >= first.guard_count

    def test_act_4_skeletons_after_local_12(self) -> None:
        # Los esqueletos solo aparecen en el acto 4 a partir del local 12.
        for lv in range(1, 88):
            assert params_for(lv).skeleton_count == 0
        assert params_for(76 + 12).skeleton_count >= 1

    def test_time_limit_ticks_property(self) -> None:
        p = params_for(1)
        assert p.time_limit_ticks == p.time_limit_seconds * 60


class TestActThemes:
    def test_four_themes_defined(self) -> None:
        assert len(ACT_THEMES) == 4

    def test_themes_are_distinct(self) -> None:
        assert len(set(ACT_THEMES)) == 4
