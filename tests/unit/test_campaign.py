"""Tests de la campaña de 100 niveles."""

from __future__ import annotations

import pytest

from pop2026.application.campaign import (
    CAMPAIGN,
    TOTAL_LEVELS,
    LevelInfo,
    get,
    total_levels,
)
from pop2026.application.difficulty import ACT_THEMES, act_for_level


class TestSize:
    def test_total_is_100(self) -> None:
        assert TOTAL_LEVELS == 100
        assert total_levels() == 100
        assert len(CAMPAIGN) == 100


class TestHandCraftedFirst12:
    @pytest.mark.parametrize(
        ("idx", "slug"),
        [
            (1, "01_cell"),
            (2, "02_sword"),
            (3, "03_guard"),
            (12, "12_jaffar"),
        ],
    )
    def test_hand_crafted_slugs_match(self, idx: int, slug: str) -> None:
        assert CAMPAIGN[idx - 1].slug == slug


class TestProceduralEntries:
    @pytest.mark.parametrize("idx", [13, 25, 26, 50, 51, 75, 76, 100])
    def test_titles_use_act_theme(self, idx: int) -> None:
        info = CAMPAIGN[idx - 1]
        theme = ACT_THEMES[act_for_level(idx)]
        assert theme in info.title

    def test_all_procedural_have_unique_slugs(self) -> None:
        slugs = [info.slug for info in CAMPAIGN]
        assert len(slugs) == len(set(slugs))

    def test_all_have_subtitle(self) -> None:
        for info in CAMPAIGN:
            assert isinstance(info, LevelInfo)
            assert info.subtitle, f"{info.slug} sin subtítulo"


class TestGet:
    def test_get_returns_levelinfo(self) -> None:
        assert isinstance(get(1), LevelInfo)
        assert isinstance(get(100), LevelInfo)

    def test_get_out_of_range_raises(self) -> None:
        with pytest.raises(IndexError):
            get(0)
        with pytest.raises(IndexError):
            get(101)
