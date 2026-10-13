"""Entrada unificada teclado + mando."""

from __future__ import annotations

import pygame

from pop2026canon.presentation.input_device import (
    KeyState,
    PadState,
    UiAction,
    command_from,
    rewind_from,
    stick_edge,
    ui_action_for_button,
    ui_action_for_key,
)


class TestGameplayMapping:
    def test_keyboard_only(self) -> None:
        cmd = command_from(KeyState(right=True, shift=True))
        assert cmd.right
        assert cmd.shift
        assert not cmd.left

    def test_pad_buttons(self) -> None:
        cmd = command_from(KeyState(), PadState(a=True, x=True, rb=True))
        assert cmd.up, "A salta"
        assert cmd.strike, "X ataca"
        assert cmd.shift, "RB agarra / paso corto"

    def test_stick_deadzone(self) -> None:
        assert not command_from(KeyState(), PadState(stick_x=0.3)).right
        assert command_from(KeyState(), PadState(stick_x=0.8)).right
        assert command_from(KeyState(), PadState(stick_y=-0.9)).up

    def test_trigger_as_shift_and_rewind(self) -> None:
        assert command_from(KeyState(), PadState(rt=0.9)).shift
        assert rewind_from(KeyState(), PadState(lt=0.9))
        assert not rewind_from(KeyState(), PadState(lt=0.1))
        assert rewind_from(KeyState(rewind=True))

    def test_opposite_directions_cancel(self) -> None:
        cmd = command_from(KeyState(left=True), PadState(right=True))
        assert not cmd.left
        assert not cmd.right


class TestUiMapping:
    def test_keys(self) -> None:
        assert ui_action_for_key(pygame.K_ESCAPE) is UiAction.PAUSE
        assert ui_action_for_key(pygame.K_RETURN) is UiAction.CONFIRM
        assert ui_action_for_key(pygame.K_RETURN, pygame.KMOD_ALT) is UiAction.FULLSCREEN
        assert ui_action_for_key(pygame.K_F11) is UiAction.FULLSCREEN
        assert ui_action_for_key(pygame.K_z) is None

    def test_buttons(self) -> None:
        assert ui_action_for_button(pygame.CONTROLLER_BUTTON_A) is UiAction.CONFIRM
        assert ui_action_for_button(pygame.CONTROLLER_BUTTON_B) is UiAction.BACK
        assert ui_action_for_button(pygame.CONTROLLER_BUTTON_START) is UiAction.PAUSE

    def test_stick_edge_fires_once(self) -> None:
        assert stick_edge(0.0, 0.9) == 1
        assert stick_edge(0.9, 0.95) == 0, "mantener no repite"
        assert stick_edge(0.0, -0.9) == -1
        assert stick_edge(0.2, 0.3) == 0
