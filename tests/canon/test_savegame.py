"""Tests del save/load."""

from __future__ import annotations

from pathlib import Path

import pytest

from pop2026canon.domain.game import GameStatus, new_game
from pop2026canon.domain.levels_canon import LEVEL_1, LEVEL_5
from pop2026canon.infrastructure.savegame import (
    SAVE_VERSION,
    load_save,
    read_from_disk,
    save_game,
    write_to_disk,
)


class TestSaveLoad:
    def test_save_captures_state(self) -> None:
        game = new_game(LEVEL_5)
        slot = save_game(game)
        assert slot.version == SAVE_VERSION
        assert slot.level == 5
        assert slot.kid_hp_curr == 3

    def test_load_restores_state(self) -> None:
        game = new_game(LEVEL_5)
        slot = save_game(game)
        restored = load_save(slot)
        assert restored.level.number == 5
        assert restored.kid.hp_curr == 3
        assert restored.status is GameStatus.PLAYING

    def test_roundtrip_disk(self, tmp_path: Path) -> None:
        game = new_game(LEVEL_1)
        slot = save_game(game)
        path = tmp_path / "save.json"
        write_to_disk(slot, path)
        loaded = read_from_disk(path)
        assert loaded == slot

    def test_version_mismatch_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text('{"version": 999}', encoding="utf-8")
        with pytest.raises(ValueError, match="save version"):
            read_from_disk(path)


class TestSaveDeaths:
    def test_deaths_roundtrip(self, tmp_path: Path) -> None:
        game = new_game(LEVEL_1)
        slot = save_game(game, deaths=7)
        path = tmp_path / "save.json"
        write_to_disk(slot, path)
        loaded = read_from_disk(path)
        assert loaded.deaths == 7

    def test_v1_save_migrates(self, tmp_path: Path) -> None:
        """Un save de la versión 1 (sin deaths) carga con deaths=0."""
        game = new_game(LEVEL_1)
        slot = save_game(game)
        path = tmp_path / "save.json"
        write_to_disk(slot, path)
        import json

        data = json.loads(path.read_text(encoding="utf-8"))
        data["version"] = 1
        del data["deaths"]
        path.write_text(json.dumps(data), encoding="utf-8")
        loaded = read_from_disk(path)
        assert loaded.deaths == 0
        assert loaded.level == 1
