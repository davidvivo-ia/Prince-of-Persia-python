"""Tests de los chars especiales: shadow, skeleton, vizier, princess, mouse."""

from __future__ import annotations

from dataclasses import replace

from pop2026canon.domain.chars import CharId
from pop2026canon.domain.game import new_game
from pop2026canon.domain.levels_canon import (
    LEVEL_3,
    LEVEL_4,
    LEVEL_5,
    LEVEL_8,
    LEVEL_12,
    LEVEL_14,
)
from pop2026canon.domain.princess import trigger_mouse_appear, trigger_princess_reunion
from pop2026canon.domain.shadow import trigger_shadow_encounters
from pop2026canon.domain.skeleton import step_skeleton_ai, trigger_skeleton_wake
from pop2026canon.domain.vizier import trigger_vizier_spawn


class TestSkeleton:
    def test_skeleton_wakes_at_trigger_col(self) -> None:
        game = new_game(LEVEL_3)
        # L3 SKELETON_WAKE event está en sala 1 col 2
        kid = replace(game.kid, room=1, curr_col=2)
        game = replace(game, kid=kid)
        game = trigger_skeleton_wake(game)
        skel = game.find_char(CharId.SKELETON)
        assert skel is not None
        assert skel.charid is CharId.SKELETON
        assert game.flags.skeleton_woke is True

    def test_skeleton_does_not_wake_wrong_col(self) -> None:
        game = new_game(LEVEL_3)
        kid = replace(game.kid, room=1, curr_col=5)
        game = replace(game, kid=kid)
        game = trigger_skeleton_wake(game)
        assert game.find_char(CharId.SKELETON) is None

    def test_skeleton_ai_moves_toward_kid(self) -> None:
        game = new_game(LEVEL_3)
        kid = replace(game.kid, room=1, curr_col=2)
        game = replace(game, kid=kid)
        game = trigger_skeleton_wake(game)
        skel = game.find_char(CharId.SKELETON)
        assert skel is not None
        original_col = skel.curr_col
        game = step_skeleton_ai(game)
        new_skel = game.find_char(CharId.SKELETON)
        assert new_skel is not None
        # Se movió hacia el kid (kid en col 2, skel spawn col 4 → debe ir a col 3)
        assert new_skel.curr_col < original_col


class TestShadow:
    def test_shadow_spawns_on_mirror(self) -> None:
        game = new_game(LEVEL_4)
        # Canon expandido: mirror en sala 5 col 5
        kid = replace(game.kid, room=5, curr_col=5)
        game = replace(game, kid=kid)
        game = trigger_shadow_encounters(game)
        assert game.flags.shadow_initialized is True
        assert game.find_char(CharId.SHADOW) is not None

    def test_shadow_steals_potion(self) -> None:
        game = new_game(LEVEL_5)
        kid = replace(game.kid, room=4)  # sala con potion
        game = replace(game, kid=kid)
        game = trigger_shadow_encounters(game)
        assert game.flags.shadow_stole_potion is True
        # Las potions de la sala 4 están marcadas consumidas
        consumed_in_room = [c for c in game.state.consumed_potions if c[0] == 4]
        assert len(consumed_in_room) >= 1

    def test_shadow_fusion_increases_hp_max(self) -> None:
        game = new_game(LEVEL_12)
        kid = replace(game.kid, room=5, curr_col=5)
        game = replace(game, kid=kid)
        # Primera llamada: spawn shadow
        game = trigger_shadow_encounters(game)
        assert game.find_char(CharId.SHADOW) is not None
        # Mueve shadow a la celda del kid
        shadow = game.find_char(CharId.SHADOW)
        assert shadow is not None
        new_shadow = replace(shadow, curr_col=5, curr_row=1)
        new_others = tuple(new_shadow if c.charid is CharId.SHADOW else c for c in game.others)
        game = replace(game, others=new_others)
        # Segunda llamada: fusión
        game = trigger_shadow_encounters(game)
        assert game.flags.shadow_fused is True
        assert game.kid.hp_max == 4  # 3 + 1


class TestVizier:
    def test_vizier_spawns(self) -> None:
        game = new_game(LEVEL_12)
        kid = replace(game.kid, room=7)  # sala del vizier
        game = replace(game, kid=kid)
        game = trigger_vizier_spawn(game)
        vz = game.find_char(CharId.VIZIER)
        assert vz is not None
        assert vz.hp_max >= 5  # canon: 5+ HP

    def test_vizier_only_spawns_once(self) -> None:
        game = new_game(LEVEL_12)
        kid = replace(game.kid, room=7)
        game = replace(game, kid=kid)
        game = trigger_vizier_spawn(game)
        game = trigger_vizier_spawn(game)
        viziers = [c for c in game.others if c.charid is CharId.VIZIER]
        assert len(viziers) == 1


class TestPrincessAndMouse:
    def test_princess_spawns_in_l14(self) -> None:
        game = new_game(LEVEL_14)
        game = trigger_princess_reunion(game)
        princess = game.find_char(CharId.PRINCESS)
        assert princess is not None

    def test_mouse_appears_in_l8(self) -> None:
        game = new_game(LEVEL_8)
        # Canon expandido: MOUSE_APPEAR en sala 10 (sala del exit)
        kid = replace(game.kid, room=10)
        game = replace(game, kid=kid)
        game = trigger_mouse_appear(game)
        assert game.flags.mouse_appeared is True
        assert game.find_char(CharId.MOUSE) is not None
