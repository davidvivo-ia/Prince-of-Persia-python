"""Interpolación visual 12→60 fps: posiciones suaves entre ticks."""

from __future__ import annotations

from pop2026canon.domain.chars import Char, CharId
from pop2026canon.presentation.renderer import _char_px, _lerp_char_px


def _kid(**kw: object) -> Char:
    defaults: dict[str, object] = {"charid": CharId.KID, "room": 1, "curr_col": 2, "curr_row": 1}
    defaults.update(kw)
    return Char(**defaults)  # type: ignore[arg-type]


class TestLerpCharPx:
    def test_alpha_one_is_current(self) -> None:
        prev, curr = _kid(curr_col=2), _kid(curr_col=3)
        assert _lerp_char_px(prev, curr, 1.0) == _char_px(curr)

    def test_no_prev_is_current(self) -> None:
        curr = _kid(curr_col=3)
        assert _lerp_char_px(None, curr, 0.2) == _char_px(curr)

    def test_midpoint_between_cells(self) -> None:
        prev, curr = _kid(curr_col=2), _kid(curr_col=3)
        px_prev, _ = _char_px(prev)
        px_curr, _ = _char_px(curr)
        x, _ = _lerp_char_px(prev, curr, 0.5)
        assert px_prev < x < px_curr

    def test_room_change_snaps(self) -> None:
        prev, curr = _kid(room=1, curr_col=9), _kid(room=2, curr_col=0)
        assert _lerp_char_px(prev, curr, 0.3) == _char_px(curr)

    def test_teleport_snaps(self) -> None:
        prev, curr = _kid(curr_col=0), _kid(curr_col=9)
        assert _lerp_char_px(prev, curr, 0.3) == _char_px(curr)
