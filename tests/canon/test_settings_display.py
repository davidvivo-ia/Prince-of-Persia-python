"""Ajustes persistentes y geometría de presentación escalada."""

from __future__ import annotations

from pathlib import Path

from pop2026canon.infrastructure.settings import Settings, from_json, load, save, to_json
from pop2026canon.presentation.display import fit_rect, window_to_canvas


class TestSettings:
    def test_roundtrip(self, tmp_path: Path) -> None:
        s = Settings().with_(music_volume=0.3, crt_filter=True, seen_hints=("grab",))
        path = tmp_path / "settings.json"
        save(s, path)
        assert load(path) == s

    def test_missing_file_gives_defaults(self, tmp_path: Path) -> None:
        assert load(tmp_path / "nope.json") == Settings()

    def test_corrupt_file_gives_defaults(self) -> None:
        assert from_json("{not json") == Settings()
        assert from_json("[1, 2]") == Settings()

    def test_partial_and_unknown_fields(self) -> None:
        s = from_json('{"music_volume": 0.1, "from_the_future": 42}')
        assert s.music_volume == 0.1
        assert s.sfx_volume == Settings().sfx_volume

    def test_values_are_clamped(self) -> None:
        s = from_json(
            '{"master_volume": 7, "window_scale": 99, "game_mode": "hard", "scale_mode": "x"}'
        )
        assert s.master_volume == 1.0
        assert s.window_scale == 4
        assert s.game_mode == "modern"
        assert s.scale_mode == "pixel"

    def test_effective_volumes(self) -> None:
        s = Settings().with_(master_volume=0.5, sfx_volume=0.5, music_volume=1.0)
        assert s.effective_sfx == 0.25
        assert s.effective_music == 0.5

    def test_json_is_human_readable(self) -> None:
        assert '"game_mode": "modern"' in to_json(Settings())


class TestFitRect:
    def test_exact_size(self) -> None:
        assert fit_rect((640, 426), (640, 426), pixel_perfect=True) == (0, 0, 640, 426)

    def test_integer_scale_letterboxed(self) -> None:
        # 1920x1080: escala entera 2 (3x no cabe en alto)
        x, y, w, h = fit_rect((1920, 1080), (640, 426), pixel_perfect=True)
        assert (w, h) == (1280, 852)
        assert x == (1920 - 1280) // 2
        assert y == (1080 - 852) // 2

    def test_smooth_fills_more(self) -> None:
        _, _, w, h = fit_rect((1920, 1080), (640, 426), pixel_perfect=False)
        assert h > 852
        assert abs(w / h - 640 / 426) < 0.01

    def test_small_window_downscales(self) -> None:
        _, _, w, h = fit_rect((320, 213), (640, 426), pixel_perfect=True)
        assert w <= 320
        assert h <= 213

    def test_mouse_mapping(self) -> None:
        win = (1920, 1080)
        x, y, _, _ = fit_rect(win, (640, 426), pixel_perfect=True)
        assert window_to_canvas((x, y), win, (640, 426), pixel_perfect=True) == (0, 0)
        assert window_to_canvas((0, 0), win, (640, 426), pixel_perfect=True) is None
