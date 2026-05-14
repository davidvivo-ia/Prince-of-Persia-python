"""Tests del generador procedural de niveles."""

from __future__ import annotations

import pytest

from pop2026.application.level_generator import (
    NARROW_COLS,
    ROWS,
    WIDE_COLS,
    GeneratorConfig,
    generate,
)
from pop2026.domain.reachability import is_reachable
from pop2026.domain.tiles import Tile


class TestDeterminism:
    def test_same_seed_same_level(self) -> None:
        cfg = GeneratorConfig(level_index=42, seed=7)
        a = generate(cfg)
        b = generate(cfg)
        assert a.grid == b.grid
        assert a.prince_spawn == b.prince_spawn
        assert a.guard_spawns == b.guard_spawns
        assert a.time_limit_ticks == b.time_limit_ticks

    def test_different_seeds_can_differ(self) -> None:
        a = generate(GeneratorConfig(level_index=42, seed=1))
        b = generate(GeneratorConfig(level_index=42, seed=999))
        # Al menos uno de varios atributos cambia.
        assert a.grid != b.grid or a.guard_spawns != b.guard_spawns

    def test_different_levels_differ(self) -> None:
        a = generate(GeneratorConfig(level_index=13, seed=42))
        b = generate(GeneratorConfig(level_index=99, seed=42))
        assert a.grid != b.grid


class TestStructure:
    def test_has_six_rows(self) -> None:
        lv = generate(GeneratorConfig(level_index=20, seed=1))
        assert lv.rows == ROWS

    def test_width_is_narrow_or_wide(self) -> None:
        for lv in (15, 30, 60, 90):
            level = generate(GeneratorConfig(level_index=lv, seed=1))
            assert level.cols in (NARROW_COLS, WIDE_COLS)

    def test_has_spawn_and_exit(self) -> None:
        lv = generate(GeneratorConfig(level_index=50, seed=1))
        # La parser ya asegura prince_spawn no None
        assert lv.prince_spawn is not None
        # Cuenta exits
        exit_count = sum(
            1 for r in range(lv.rows) for c in range(lv.cols) if lv.grid[r][c] is Tile.EXIT
        )
        assert exit_count >= 1

    def test_time_limit_set(self) -> None:
        lv = generate(GeneratorConfig(level_index=1, seed=1))
        assert lv.time_limit_ticks is not None
        assert lv.time_limit_ticks > 0


class TestReachability:
    @pytest.mark.parametrize("level_index", [13, 25, 26, 50, 51, 75, 76, 88, 100])
    def test_generated_level_is_reachable(self, level_index: int) -> None:
        lv = generate(GeneratorConfig(level_index=level_index, seed=42))
        assert is_reachable(lv), f"L{level_index} con seed=42 no es reachable"

    def test_multiple_seeds_all_reachable(self) -> None:
        # Para nivel 50 con varias seeds, todas deben ser reachable.
        for seed in (1, 7, 42, 100, 200):
            lv = generate(GeneratorConfig(level_index=50, seed=seed))
            assert is_reachable(lv), f"L50 seed={seed} no reachable"


class TestActors:
    def test_act_4_has_more_guards_than_act_1(self) -> None:
        a1 = generate(GeneratorConfig(level_index=5, seed=1))
        a4 = generate(GeneratorConfig(level_index=80, seed=1))
        # Acto 4 tiene base_guards=2, acto 1 tiene base_guards=0
        assert len(a4.guard_spawns) > len(a1.guard_spawns)

    def test_boss_only_at_local_24(self) -> None:
        # Nivel 25 (último de acto 1) debe tener boss; nivel 26 (primer de acto 2) no.
        boss_level = generate(GeneratorConfig(level_index=25, seed=1))
        non_boss = generate(GeneratorConfig(level_index=26, seed=1))
        has_boss = any(skill == 2 for _, skill in boss_level.guard_spawns)
        has_non_boss = any(skill == 2 for _, skill in non_boss.guard_spawns)
        assert has_boss, "L25 debería tener jefe"
        assert not has_non_boss, "L26 no debería tener jefe"
