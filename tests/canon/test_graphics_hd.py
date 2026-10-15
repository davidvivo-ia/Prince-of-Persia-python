"""Gráficos HD: esqueleto de poses (puro), sprites de personajes y de
tiles, post-proceso y geometría del lienzo."""

from __future__ import annotations

import math
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import itertools

import pygame
import pytest

from pop2026canon.domain.seqtbl import ActKind
from pop2026canon.presentation import poses
from pop2026canon.presentation.layout import LAYOUT, px


def _seq_frames() -> set[int]:
    from pop2026canon.domain import seqtbl

    out: set[int] = set()
    for name, value in vars(seqtbl).items():
        if name.startswith("_SEQ_"):
            out |= {a.arg for a in value if a.kind is ActKind.FRAME}
    return out


SEQ_FRAMES = sorted(_seq_frames())


@pytest.fixture(scope="module", autouse=True)
def _pygame():  # type: ignore[no-untyped-def]
    pygame.init()


class TestLayout:
    def test_hd_canvas_is_twice_the_design_size(self) -> None:
        assert (LAYOUT.window_w, LAYOUT.window_h) == (1280, 852)
        assert LAYOUT.base_size == (640, 426)
        assert px(10) == 10 * LAYOUT.scale

    def test_feet_stand_on_the_slab_top(self) -> None:
        assert 0 < LAYOUT.foot_lift < LAYOUT.floor_face + LAYOUT.floor_top


class TestPoses:
    @pytest.mark.parametrize("frame", SEQ_FRAMES)
    def test_every_canon_frame_has_a_finite_pose(self, frame: int) -> None:
        j = poses.solve(poses.pose_for(frame))
        for x, y in j.points():
            assert math.isfinite(x)
            assert math.isfinite(y)
            assert abs(x) < 80
            assert -150 < y < 10

    @pytest.mark.parametrize("frame", [15, 121, 125, 158, 154, 110, 112])
    def test_grounded_poses_touch_the_floor(self, frame: int) -> None:
        j = poses.solve(poses.pose_for(frame))
        lowest = max(
            j.ankle_n[1] + poses.SOLE,
            j.ankle_f[1] + poses.SOLE,
            j.toe_n[1] + poses.SOLE * 0.6,
            j.toe_f[1] + poses.SOLE * 0.6,
        )
        assert lowest == pytest.approx(0.0, abs=0.01)

    def test_standing_height_matches_the_original_proportion(self) -> None:
        j = poses.solve(poses.STAND)
        top = j.head[1] - poses.HEAD_R
        assert 0.6 < -top / poses.ROW_UNITS < 0.72

    @pytest.mark.parametrize("frame", [70, 77, 78, 79, 80, 91])
    def test_hanging_hands_grip_the_ledge(self, frame: int) -> None:
        j = poses.solve(poses.pose_for(frame))
        assert j.hand_n == pytest.approx((poses.HANG_X, poses.HANG_Y), abs=0.01)
        assert j.head[1] > poses.HANG_Y  # la cabeza bajo la cornisa

    @pytest.mark.parametrize("frame", range(135, 143))
    def test_climbing_keeps_the_hands_on_the_ledge(self, frame: int) -> None:
        j = poses.solve(poses.pose_for(frame))
        assert j.hand_n[1] == pytest.approx(poses.HANG_Y, abs=0.5)

    def test_climb_ends_standing_on_the_ledge(self) -> None:
        j = poses.solve(poses.pose_for(149))
        lowest = max(
            j.ankle_n[1] + poses.SOLE,
            j.ankle_f[1] + poses.SOLE,
            j.toe_n[1] + poses.SOLE * 0.6,
            j.toe_f[1] + poses.SOLE * 0.6,
        )
        assert lowest == pytest.approx(-poses.ROW_UNITS, abs=0.01)

    def test_climb_rises_monotonically(self) -> None:
        heads = [poses.solve(poses.pose_for(f)).head[1] for f in range(135, 144)]
        assert all(b <= a + 1.0 for a, b in itertools.pairwise(heads))

    def test_turn_starts_mirrored_and_ends_facing_the_new_way(self) -> None:
        assert poses.pose_for(45).sx < 0
        assert poses.pose_for(49).sx == pytest.approx(1.0)

    def test_dead_body_lies_on_the_floor(self) -> None:
        j = poses.solve(poses.pose_for(185))
        ys = [p[1] for p in j.points()]
        assert max(ys) - min(ys) < 18  # tendido, no de pie
        assert max(ys) <= 0.01

    def test_sword_frames_hold_a_blade(self) -> None:
        for f in (150, 151, 154, 158, 167, 172):
            assert poses.pose_for(f).blade is not None
        assert poses.pose_for(15).blade is None

    def test_ik_reaches_or_points_at_the_target(self) -> None:
        elbow, hand = poses._ik((0.0, 0.0), (5.0, -10.0), poses.UARM, poses.FARM)
        assert hand == pytest.approx((5.0, -10.0), abs=1e-6)
        assert math.dist((0.0, 0.0), elbow) == pytest.approx(poses.UARM)
        _, far = poses._ik((0.0, 0.0), (100.0, 0.0), poses.UARM, poses.FARM)
        assert far == pytest.approx((poses.UARM + poses.FARM, 0.0))


class TestCharSprites:
    def test_sprites_are_cached_and_mirrored(self) -> None:
        from pop2026canon.presentation.char_atlas import CharPalette, sprite

        a = sprite(15, CharPalette.KID, 0)
        assert sprite(15, CharPalette.KID, 0) is a
        right, (ax, ay) = a
        left, (bx, by) = sprite(15, CharPalette.KID, -1)
        assert right.get_size() == left.get_size()
        assert ay == by
        assert ax + bx == pytest.approx(right.get_width(), abs=1)

    @pytest.mark.parametrize("palette", range(7))
    def test_every_outfit_renders_visible_pixels(self, palette: int) -> None:
        from pop2026canon.presentation.char_atlas import CharPalette, sprite

        img, (ax, ay) = sprite(158, CharPalette(palette), 0)
        assert 0 <= ax <= img.get_width()
        assert 0 <= ay <= img.get_height()
        mask = pygame.mask.from_surface(img)
        assert mask.count() > 200

    def test_kid_is_hd_sized(self) -> None:
        from pop2026canon.presentation.char_atlas import CharPalette, sprite

        img, _ = sprite(15, CharPalette.KID, 0)
        rect = pygame.mask.from_surface(img).get_bounding_rects()[0]
        assert 0.6 < rect.h / LAYOUT.tile_h < 0.75


class TestTiles:
    @pytest.mark.parametrize("tile", range(31))
    @pytest.mark.parametrize("palace", [False, True])
    def test_every_tile_draws_in_both_styles(self, tile: int, palace: bool) -> None:
        from pop2026canon.presentation.tile_atlas import draw_tile, draw_tile_front

        s = pygame.Surface((LAYOUT.window_w, LAYOUT.window_h))
        for mod in (0, 1, 3, 7, 0x80, 0xFF):
            draw_tile(s, tile, LAYOUT.tile_w, LAYOUT.hud_top + LAYOUT.tile_h, mod, palace=palace)
        draw_tile(s, tile, 0, LAYOUT.hud_top, 0, palace=palace, edges=(True, True), variant=5)
        draw_tile_front(s, tile, 0, LAYOUT.hud_top, palace=palace)

    def test_floor_bearing_tiles(self) -> None:
        from pop2026canon.presentation.tile_atlas import has_floor

        assert has_floor(1)
        assert has_floor(20)
        assert has_floor(4)
        assert not has_floor(0)
        assert not has_floor(12)
        assert not has_floor(9)

    def test_only_visual_state_enters_the_cache_key(self) -> None:
        from pop2026canon.presentation.tile_atlas import mod_key

        assert mod_key(1, 5) == 0  # el suelo no cambia con el modificador
        assert mod_key(4, 5) == 5  # la reja sí
        assert mod_key(15, 3) == 1  # placa: pisada o no

    def test_torch_flame_animates(self) -> None:
        from pop2026canon.presentation.tile_atlas import draw_torch_flame

        a = pygame.Surface((px(40), px(60)))
        b = pygame.Surface((px(40), px(60)))
        draw_torch_flame(a, px(20), px(50), 0.0)
        draw_torch_flame(b, px(20), px(50), 0.37)
        assert pygame.image.tobytes(a, "RGB") != pygame.image.tobytes(b, "RGB")


class TestPost:
    def test_bloom_spreads_light_around_bright_spots(self) -> None:
        from pop2026canon.presentation.fx import bloom

        s = pygame.Surface((LAYOUT.window_w, LAYOUT.window_h))
        s.fill((10, 10, 10))
        pygame.draw.circle(s, (255, 240, 200), (640, 400), px(8))
        before = s.get_at((640 + px(13), 400))
        bloom(s, pygame.Rect(0, LAYOUT.hud_top, LAYOUT.window_w, LAYOUT.room_h))
        after = s.get_at((640 + px(13), 400))
        assert after.r > before.r

    def test_bloom_leaves_dark_scenes_alone(self) -> None:
        from pop2026canon.presentation.fx import bloom

        s = pygame.Surface((LAYOUT.window_w, LAYOUT.window_h))
        s.fill((60, 60, 80))
        bloom(s, pygame.Rect(0, LAYOUT.hud_top, LAYOUT.window_w, LAYOUT.room_h))
        assert s.get_at((300, 300))[:3] == (60, 60, 80)

    def test_display_window_sizes_follow_the_design_scale(self) -> None:
        from pop2026canon.presentation.display import Display

        assert Display._scaled(1) == (640, 426)
        assert Display._scaled(2) == (1280, 852)
