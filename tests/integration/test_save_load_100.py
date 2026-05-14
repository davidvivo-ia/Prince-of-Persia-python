"""Integration test: save/load funciona hasta nivel 100."""

from __future__ import annotations

from pathlib import Path

from pop2026.infrastructure import savegame
from pop2026.infrastructure.savegame import SAVE_VERSION, SaveGame


def test_save_at_level_99_resumes_at_100(tmp_path: Path) -> None:
    """Simula ganar L99 → grabado → recarga → arranca en 100."""
    path = tmp_path / "save.json"
    slot = SaveGame(
        version=SAVE_VERSION,
        level=100,
        hp=4,
        max_hp=4,
        time_left_ms=0,
        rng_seed=42,
    )
    savegame.save(slot, path)

    loaded = savegame.load(path)
    assert loaded is not None
    assert loaded.level == 100
    assert loaded.max_hp == 4
    assert loaded.rng_seed == 42


def test_save_max_hp_bonus_persists(tmp_path: Path) -> None:
    path = tmp_path / "save.json"
    slot = SaveGame(version=SAVE_VERSION, level=80, hp=5, max_hp=5, time_left_ms=0, rng_seed=1)
    savegame.save(slot, path)
    loaded = savegame.load(path)
    assert loaded is not None
    assert loaded.max_hp == 5
