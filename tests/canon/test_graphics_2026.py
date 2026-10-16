"""Gráficos 2026: luz con relieve horneada en la pared, oclusión de
contacto, sombras en la pared, niebla sobre suelo y post-proceso de cine."""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from dataclasses import replace

import numpy as np
import pygame
import pytest

from pop2026canon.domain.game import new_game
from pop2026canon.domain.levels_canon import CANON_LEVELS
from pop2026canon.domain.tiles import Tile
from pop2026canon.infrastructure.settings import Settings
from pop2026canon.presentation import backdrop as bd
from pop2026canon.presentation import fx
from pop2026canon.presentation.layout import LAYOUT, px
from pop2026canon.presentation.menu import options_menu
from pop2026canon.presentation.scene import Scene


@pytest.fixture(scope="module", autouse=True)
def _pygame():  # type: ignore[no-untyped-def]
    pygame.init()


def _mean(surf: pygame.Surface, rect: pygame.Rect) -> float:
    sub = surf.subsurface(rect)
    return float(pygame.surfarray.array3d(sub).mean())


class TestReliefLight:
    def test_factor_is_brighter_near_the_light_than_far(self) -> None:
        wall = bd.backdrop(1, "l1")
        torch = (px(100), px(120), px(230), (255, 168, 64))
        fac = bd.relief_factor(wall, (torch,))
        assert fac.shape == (wall.get_width(), wall.get_height(), 3)
        near = fac[px(80) : px(120), px(100) : px(140)].mean()
        far = fac[px(560) : px(600), px(300) : px(340)].mean()
        assert near > far * 1.3

    def test_torch_colour_tints_the_wall(self) -> None:
        wall = bd.backdrop(1, "l1")
        fac = bd.relief_factor(wall, ((px(100), px(120), px(230), (255, 120, 40)),))
        r, g, b = fac[px(90) : px(110), px(110) : px(130)].mean(axis=(0, 1))
        assert r > g > b

    def test_bevels_facing_the_light_get_more_than_those_facing_away(self) -> None:
        """Una pared con un escalón vertical de luminancia: el lado que
        mira a la luz recibe más que el que le da la espalda."""
        w, h = 200, 100
        surf = pygame.Surface((w, h))
        surf.fill((90, 90, 90))
        pygame.draw.rect(surf, (160, 160, 160), (100, 0, 100, h))
        fac = bd.relief_factor(surf, ((20, 50, 400, (255, 255, 255)),), scale=1)
        # Normales en el borde x=100: el gradiente apunta hacia +x (más
        # claro a la derecha) → la normal se inclina hacia -x, hacia la luz.
        facing = fac[99:101, 45:55, 0].mean()
        flat_far = fac[150:160, 45:55, 0].mean()
        assert facing > flat_far

    def test_no_lights_leaves_the_backdrop_unbaked(self) -> None:
        a = bd.backdrop(2, "l1")
        b = bd.backdrop(2, "l1", ())
        assert pygame.image.tobytes(a, "RGB") == pygame.image.tobytes(b, "RGB")

    def test_lights_are_part_of_the_cache_key(self) -> None:
        plain = bd.backdrop(3, "l2")
        lit = bd.backdrop(3, "l2", ((px(300), px(200), px(230), (255, 160, 58)),))
        assert pygame.image.tobytes(plain, "RGB") != pygame.image.tobytes(lit, "RGB")
        assert plain is bd.backdrop(3, "l2")

    def test_room_lights_find_the_torches(self) -> None:
        lv = CANON_LEVELS[1]
        torch_room = next(
            rm.id for rm in lv.rooms if any((b & 0x1F) == int(Tile.TORCH) for b in rm.fg)
        )
        g = new_game(lv)
        g = replace(g, kid=replace(g.kid, room=torch_room))
        lights = fx.room_lights(g)
        assert any(col == (255, 160, 58) for *_rest, col in lights)
        for x, y, radius, _col in lights:
            assert 0 <= x <= LAYOUT.window_w
            assert 0 <= y <= LAYOUT.room_h
            assert radius > 0


class TestContactOcclusion:
    def test_wall_darkens_next_to_geometry_only(self) -> None:
        base = pygame.Surface((400, 300))
        base.fill((200, 200, 200))
        tiles = pygame.Surface((400, 300), pygame.SRCALPHA)
        pygame.draw.rect(tiles, (255, 255, 255, 255), (0, 150, 400, 150))
        fx.contact_occlusion(base, tiles)
        near = base.get_at((200, 146))
        far = base.get_at((200, 20))
        assert near.r < 190
        assert far.r == 200


class TestWallShadows:
    def test_shadow_falls_away_from_the_torch(self) -> None:
        lv = CANON_LEVELS[0]
        g = new_game(lv)
        world = pygame.Surface((LAYOUT.window_w, LAYOUT.window_h))
        world.fill((180, 180, 180))
        kx, ky = fx._char_px(g.kid)
        # Luz a la izquierda del kid: la sombra cae a su derecha
        light = (kx - px(80), ky - LAYOUT.hud_top - px(30), px(230), (255, 168, 64))
        fx.draw_wall_shadows(world, g, None, 1.0, (light,))
        right = _mean(world, pygame.Rect(kx + px(14), ky - px(50), px(10), px(40)))
        left = _mean(world, pygame.Rect(kx - px(40), ky - px(50), px(10), px(40)))
        assert right < left

    def test_silhouette_is_cached_and_blurred(self) -> None:
        from pop2026canon.presentation.char_atlas import CharPalette

        a, (ax, ay) = fx._silhouette(15, CharPalette.KID, 0, 0, 110)
        b, _ = fx._silhouette(15, CharPalette.KID, 0, 0, 110)
        assert a is b
        assert ax > 0
        assert ay > 0
        alphas = pygame.surfarray.array_alpha(a)
        assert alphas.max() > 150
        assert ((alphas > 0) & (alphas < 150)).any(), "bordes difuminados"


class TestFogAndCine:
    def test_fog_only_over_floor(self) -> None:
        lv = CANON_LEVELS[0]
        g = new_game(lv)
        room = g.level.room(g.kid.room)
        # Una columna de la fila de abajo con suelo y otra sin suelo
        floor_col = next(c for c in range(10) if fx.has_floor(int(room.tile_at(c, 2)[0])))
        empty = [c for c in range(10) if not fx.has_floor(int(room.tile_at(c, 1)[0]))]
        if not empty:
            pytest.skip("la sala no tiene huecos en la fila 1")
        world = pygame.Surface((LAYOUT.window_w, LAYOUT.window_h))
        world.fill((0, 0, 0))
        fx.draw_atmosphere(world, g, 0.0)
        y_floor = LAYOUT.hud_top + 3 * LAYOUT.tile_h - LAYOUT.foot_lift - px(30)
        y_empty = LAYOUT.hud_top + 2 * LAYOUT.tile_h - LAYOUT.foot_lift - px(30)
        lit = _mean(world, pygame.Rect(floor_col * LAYOUT.tile_w, y_floor, LAYOUT.tile_w, px(30)))
        dark = _mean(world, pygame.Rect(empty[0] * LAYOUT.tile_w, y_empty, LAYOUT.tile_w, px(30)))
        assert lit >= dark

    def test_film_grain_is_animated_and_zero_mean(self) -> None:
        a = pygame.Surface((LAYOUT.window_w, LAYOUT.window_h))
        a.fill((100, 100, 100))
        b = a.copy()
        fx.film_grain(a, 0.0)
        fx.film_grain(b, 0.5)
        arr_a = pygame.surfarray.array3d(a).astype(np.int32)
        arr_b = pygame.surfarray.array3d(b).astype(np.int32)
        assert (arr_a != arr_b).any()
        assert abs(arr_a.mean() - 100) < 1.0
        assert 0 < arr_a.std() <= fx.GRAIN_AMPLITUDE

    def test_aberration_touches_only_the_edge_bands(self) -> None:
        s = pygame.Surface((LAYOUT.window_w, LAYOUT.window_h))
        s.fill((0, 0, 0))
        area = pygame.Rect(0, LAYOUT.hud_top, LAYOUT.window_w, LAYOUT.room_h)
        for x in (px(30), LAYOUT.window_w // 2, LAYOUT.window_w - px(30)):
            pygame.draw.rect(s, (255, 255, 255), (x, 300, px(10), px(10)))
        before = pygame.surfarray.array3d(s).copy()
        fx.chromatic_aberration(s, area)
        after = pygame.surfarray.array3d(s)
        band = px(fx.ABERRATION_BAND)
        centre = slice(band + 4, LAYOUT.window_w - band - 4)
        assert (after[centre] == before[centre]).all(), "el centro queda intacto"
        edge = after[px(30) - px(2) : px(30) + px(10) + px(2), 300 : 300 + px(10)]
        assert (edge[:, :, 0] != edge[:, :, 2]).any(), "rojo y azul separados en el borde"
        # Sin costura: en la frontera de la banda no aparece una línea de color
        seam = after[band - 3 : band + 3, 500:520]
        assert (seam == 0).all()

    def test_cinematic_setting_and_menu(self) -> None:
        assert Settings().cinematic is True
        item = next(i for i in options_menu().items if i.key == "cinematic")
        assert item.kind == "toggle"


class TestSceneIntegration:
    @pytest.mark.parametrize("lighting", [True, False])
    def test_scene_draws_with_and_without_lighting(self, lighting: bool) -> None:
        lv = CANON_LEVELS[1]
        g = new_game(lv, has_sword=True)
        sc = Scene(Settings(lighting=lighting, cinematic=lighting))
        sc.on_level_start(g)
        canvas = pygame.Surface((LAYOUT.window_w, LAYOUT.window_h))
        for i in range(3):
            sc.update(1 / 60, g, i / 60)
            sc.draw(canvas, g, g, 1.0, i / 60, sand=None, rewinding=False, show_time=False)
        assert _mean(canvas, pygame.Rect(0, LAYOUT.hud_top, LAYOUT.window_w, LAYOUT.room_h)) > 5

    def test_base_is_recomposed_only_when_the_room_changes(self) -> None:
        lv = CANON_LEVELS[0]
        g = new_game(lv)
        sc = Scene(Settings())
        sc.on_level_start(g)
        canvas = pygame.Surface((LAYOUT.window_w, LAYOUT.window_h))
        sc.draw(canvas, g, g, 1.0, 0.0, sand=None, rewinding=False, show_time=False)
        key = sc._base_key
        sc.draw(canvas, g, g, 1.0, 0.1, sand=None, rewinding=False, show_time=False)
        assert sc._base_key is key
        assert key is not None
        assert isinstance(key[3], tuple), "las luces forman parte de la clave"
