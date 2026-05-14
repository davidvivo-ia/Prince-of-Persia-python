"""Tests de la capa de infraestructura."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pop2026.domain.errors import LevelLoadError, SaveCorruptedError
from pop2026.infrastructure import levels, savegame
from pop2026.infrastructure.rng import LfsrRng
from pop2026.infrastructure.savegame import SaveGame


class TestLfsrRng:
    def test_seed_zero_is_safe(self) -> None:
        r = LfsrRng(0)
        # no debe explotar al pedir bytes
        for _ in range(300):
            b = r.next_byte()
            assert 0 < b <= 255

    def test_same_seed_same_sequence(self) -> None:
        a = LfsrRng(42)
        b = LfsrRng(42)
        for _ in range(100):
            assert a.next_byte() == b.next_byte()

    def test_different_seed_different_sequence(self) -> None:
        a = LfsrRng(1)
        b = LfsrRng(2)
        diffs = sum(1 for _ in range(50) if a.next_byte() != b.next_byte())
        assert diffs > 0

    def test_period_at_most_255(self) -> None:
        r = LfsrRng(1)
        seen = {r.next_byte() for _ in range(300)}
        # un LFSR-8 visita 255 estados no-cero
        assert len(seen) <= 255

    def test_coin_respects_extremes(self) -> None:
        r = LfsrRng(7)
        # prob 0 → siempre False
        assert not any(r.coin(0.0) for _ in range(50))
        # prob 1 → siempre True (256/256 ⇒ todos los bytes < 256)
        assert all(r.coin(1.0) for _ in range(50))

    def test_randrange_in_bounds(self) -> None:
        r = LfsrRng(7)
        for _ in range(200):
            v = r.randrange(10)
            assert 0 <= v < 10


class TestLevelLoader:
    def test_list_builtin_returns_known_levels(self) -> None:
        names = levels.list_builtin()
        # La campaña tiene 12 niveles built-in
        assert len(names) == 12
        assert "01_cell" in names
        assert "12_jaffar" in names

    def test_load_builtin_parses(self) -> None:
        lv = levels.load_builtin("01_cell")
        assert lv.name == "01_cell"
        assert lv.rows > 0
        assert lv.prince_spawn.row >= 0

    def test_every_builtin_level_parses(self) -> None:
        for name in levels.list_builtin():
            lv = levels.load_builtin(name)
            assert lv.prince_spawn.row >= 0
            assert lv.cols > 0

    def test_load_unknown_raises(self) -> None:
        with pytest.raises(LevelLoadError):
            levels.load_builtin("9999_no")

    def test_load_from_file(self, tmp_path: Path) -> None:
        path = tmp_path / "x.poplv"
        path.write_text("######\n#..@>#\n######\n", encoding="utf-8")
        lv = levels.load_from_file(path)
        assert lv.name == "x"

    def test_load_from_file_missing(self, tmp_path: Path) -> None:
        with pytest.raises(LevelLoadError):
            levels.load_from_file(tmp_path / "missing.poplv")


class TestSaveGame:
    def test_roundtrip(self, tmp_path: Path) -> None:
        s = SaveGame(level=2, hp=3, max_hp=4, time_left_ms=120000, rng_seed=42)
        path = tmp_path / "save.json"
        savegame.save(s, path)
        loaded = savegame.load(path)
        assert loaded == s

    def test_can_save_level_100(self, tmp_path: Path) -> None:
        s = SaveGame(level=100, hp=3, max_hp=3, time_left_ms=0, rng_seed=42)
        path = tmp_path / "save.json"
        savegame.save(s, path)
        loaded = savegame.load(path)
        assert loaded is not None
        assert loaded.level == 100

    def test_load_missing_returns_none(self, tmp_path: Path) -> None:
        assert savegame.load(tmp_path / "no.json") is None

    def test_load_corrupted_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text("{ not json", encoding="utf-8")
        with pytest.raises(SaveCorruptedError):
            savegame.load(path)

    def test_load_invalid_schema_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text(json.dumps({"version": 1, "level": -1}), encoding="utf-8")
        with pytest.raises(SaveCorruptedError):
            savegame.load(path)

    def test_default_path_uses_xdg(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
        p = savegame.default_path()
        assert tmp_path in p.parents
