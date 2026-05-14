"""Property tests del generador procedural con hypothesis."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from pop2026.application.level_generator import GeneratorConfig, generate
from pop2026.domain.reachability import is_reachable

PROCEDURAL_LEVELS = st.integers(min_value=13, max_value=100)
SEEDS = st.integers(min_value=0, max_value=255)


@given(level_index=PROCEDURAL_LEVELS, seed=SEEDS)
@settings(max_examples=80, deadline=None)
def test_every_generated_level_is_reachable(level_index: int, seed: int) -> None:
    """Para cualquier (nivel procedural, seed), el nivel es reachable."""
    lv = generate(GeneratorConfig(level_index=level_index, seed=seed))
    assert is_reachable(lv), f"L{level_index} seed={seed} no reachable"


@given(level_index=PROCEDURAL_LEVELS, seed=SEEDS)
@settings(max_examples=40, deadline=None)
def test_same_input_same_output(level_index: int, seed: int) -> None:
    """Determinismo total."""
    a = generate(GeneratorConfig(level_index=level_index, seed=seed))
    b = generate(GeneratorConfig(level_index=level_index, seed=seed))
    assert a.grid == b.grid
    assert a.guard_spawns == b.guard_spawns


@given(level_index=PROCEDURAL_LEVELS)
@settings(max_examples=20, deadline=None)
def test_different_seeds_yield_variety(level_index: int) -> None:
    """Para un mismo nivel, distintas seeds producen variedad razonable."""
    grids = {
        generate(GeneratorConfig(level_index=level_index, seed=s)).grid
        for s in (1, 7, 42, 100, 200)
    }
    # Al menos 3 layouts distintos de 5 (60 % de variedad)
    assert len(grids) >= 3, f"L{level_index}: solo {len(grids)} layouts únicos en 5 seeds"


@given(level_index=PROCEDURAL_LEVELS, seed=SEEDS)
@settings(max_examples=30, deadline=None)
def test_has_exactly_one_spawn_and_at_least_one_exit(level_index: int, seed: int) -> None:
    """Invariantes estructurales del nivel."""
    from pop2026.domain.tiles import Tile

    lv = generate(GeneratorConfig(level_index=level_index, seed=seed))
    assert lv.prince_spawn is not None
    exits = sum(1 for r in range(lv.rows) for c in range(lv.cols) if lv.grid[r][c] is Tile.EXIT)
    assert exits >= 1, f"L{level_index} seed={seed}: sin exit"
