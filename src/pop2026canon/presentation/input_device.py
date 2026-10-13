"""Entrada unificada: teclado y mando (SDL GameController: Xbox,
PlayStation, Switch Pro, Steam Deck...).

Juego (``Command`` del dominio):

=============  =======================  ===============================
Acción         Teclado                  Mando
=============  =======================  ===============================
Moverse        Flechas / WASD           Cruceta / stick izquierdo
Saltar (↑)     ↑ / W                    A (Cruz)
Agacharse (↓)  ↓ / S                    B (Círculo)
Agarrar/paso   Shift                    RB / RT
Atacar         Espacio / J              X (Cuadrado)
Rebobinar      R (mantener)             LB / LT (mantener)
=============  =======================  ===============================

Interfaz: ``UiAction`` (navegar, confirmar, volver, pausa, mapa...),
emitida una vez por pulsación. El stick genera navegación al cruzar
el umbral (con detección de flanco: no repite mientras se mantiene).
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from enum import Enum, auto

import pygame

from pop2026canon.application.controller import Command

STICK_DEADZONE: float = 0.45
"""Fracción del recorrido del stick que cuenta como dirección."""

TRIGGER_THRESHOLD: float = 0.35


class UiAction(Enum):
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()
    CONFIRM = auto()
    BACK = auto()
    PAUSE = auto()
    MAP = auto()
    FULLSCREEN = auto()
    CONTINUE = auto()
    """Atajo de "continuar partida" en el título (C)."""


@dataclass(frozen=True, slots=True)
class PadState:
    """Estado instantáneo de un mando (valores normalizados)."""

    left: bool = False
    right: bool = False
    up: bool = False
    down: bool = False
    a: bool = False
    b: bool = False
    x: bool = False
    y: bool = False
    lb: bool = False
    rb: bool = False
    lt: float = 0.0
    rt: float = 0.0
    stick_x: float = 0.0
    stick_y: float = 0.0


@dataclass(frozen=True, slots=True)
class KeyState:
    """Teclas relevantes pulsadas (independiente de pygame para testear)."""

    left: bool = False
    right: bool = False
    up: bool = False
    down: bool = False
    shift: bool = False
    strike: bool = False
    rewind: bool = False


def command_from(keys: KeyState, pad: PadState | None = None) -> Command:
    """Combina teclado y mando en un ``Command``."""
    p = pad or PadState()
    left = keys.left or p.left or p.stick_x <= -STICK_DEADZONE
    right = keys.right or p.right or p.stick_x >= STICK_DEADZONE
    up = keys.up or p.up or p.a or p.stick_y <= -STICK_DEADZONE
    down = keys.down or p.down or p.b or p.stick_y >= STICK_DEADZONE
    if left and right:
        left = right = False
    return Command(
        left=left,
        right=right,
        up=up,
        down=down,
        shift=keys.shift or p.rb or p.rt >= TRIGGER_THRESHOLD,
        strike=keys.strike or p.x,
    )


def rewind_from(keys: KeyState, pad: PadState | None = None) -> bool:
    p = pad or PadState()
    return keys.rewind or p.lb or p.lt >= TRIGGER_THRESHOLD


_KEY_UI: dict[int, UiAction] = {
    pygame.K_UP: UiAction.UP,
    pygame.K_w: UiAction.UP,
    pygame.K_DOWN: UiAction.DOWN,
    pygame.K_s: UiAction.DOWN,
    pygame.K_LEFT: UiAction.LEFT,
    pygame.K_a: UiAction.LEFT,
    pygame.K_RIGHT: UiAction.RIGHT,
    pygame.K_d: UiAction.RIGHT,
    pygame.K_RETURN: UiAction.CONFIRM,
    pygame.K_KP_ENTER: UiAction.CONFIRM,
    pygame.K_SPACE: UiAction.CONFIRM,
    pygame.K_ESCAPE: UiAction.PAUSE,
    pygame.K_p: UiAction.PAUSE,
    pygame.K_BACKSPACE: UiAction.BACK,
    pygame.K_m: UiAction.MAP,
    pygame.K_F11: UiAction.FULLSCREEN,
    pygame.K_c: UiAction.CONTINUE,
}

_BUTTON_UI: dict[int, UiAction] = {
    pygame.CONTROLLER_BUTTON_DPAD_UP: UiAction.UP,
    pygame.CONTROLLER_BUTTON_DPAD_DOWN: UiAction.DOWN,
    pygame.CONTROLLER_BUTTON_DPAD_LEFT: UiAction.LEFT,
    pygame.CONTROLLER_BUTTON_DPAD_RIGHT: UiAction.RIGHT,
    pygame.CONTROLLER_BUTTON_A: UiAction.CONFIRM,
    pygame.CONTROLLER_BUTTON_B: UiAction.BACK,
    pygame.CONTROLLER_BUTTON_START: UiAction.PAUSE,
    pygame.CONTROLLER_BUTTON_BACK: UiAction.MAP,
}


def ui_action_for_key(key: int, mod: int = 0) -> UiAction | None:
    if key == pygame.K_RETURN and mod & pygame.KMOD_ALT:
        return UiAction.FULLSCREEN
    return _KEY_UI.get(key)


def ui_action_for_button(button: int) -> UiAction | None:
    return _BUTTON_UI.get(button)


def stick_edge(prev: float, now: float) -> int:
    """-1 / +1 cuando el eje cruza el umbral hacia un lado; 0 si no."""
    if now <= -STICK_DEADZONE < prev:
        return -1
    if now >= STICK_DEADZONE > prev:
        return 1
    return 0


class InputHub:
    """Mandos conectados + lectura de teclado. Una instancia por juego."""

    def __init__(self) -> None:
        self._pads: dict[int, object] = {}
        self._axis_prev: dict[tuple[int, int], float] = {}
        self._ok = False
        with contextlib.suppress(Exception):
            from pygame._sdl2 import controller

            controller.init()
            self._ok = True
            for i in range(controller.get_count()):
                self._open(i)

    @property
    def pad_connected(self) -> bool:
        return bool(self._pads)

    def _open(self, index: int) -> None:
        with contextlib.suppress(Exception):
            from pygame._sdl2 import controller

            if controller.is_controller(index):
                pad = controller.Controller(index)
                self._pads[pad.id] = pad

    def handle_event(self, ev: pygame.event.Event) -> list[UiAction]:
        """Traduce un evento a acciones de interfaz y gestiona mandos."""
        if ev.type == pygame.KEYDOWN:
            action = ui_action_for_key(ev.key, getattr(ev, "mod", 0))
            return [action] if action else []
        if not self._ok:
            return []
        if ev.type == pygame.CONTROLLERDEVICEADDED:
            self._open(ev.device_index)
            return []
        if ev.type == pygame.CONTROLLERDEVICEREMOVED:
            self._pads.pop(getattr(ev, "instance_id", -1), None)
            return []
        if ev.type == pygame.CONTROLLERBUTTONDOWN:
            action = ui_action_for_button(ev.button)
            return [action] if action else []
        if ev.type == pygame.CONTROLLERAXISMOTION and ev.axis in (
            pygame.CONTROLLER_AXIS_LEFTX,
            pygame.CONTROLLER_AXIS_LEFTY,
        ):
            key = (getattr(ev, "instance_id", 0), ev.axis)
            now = ev.value / 32767.0
            edge = stick_edge(self._axis_prev.get(key, 0.0), now)
            self._axis_prev[key] = now
            if edge == 0:
                return []
            if ev.axis == pygame.CONTROLLER_AXIS_LEFTX:
                return [UiAction.LEFT if edge < 0 else UiAction.RIGHT]
            return [UiAction.UP if edge < 0 else UiAction.DOWN]
        return []

    def _pad_state(self) -> PadState | None:
        if not self._pads:
            return None
        merged: dict[str, object] = {}
        for pad in self._pads.values():
            with contextlib.suppress(Exception):
                g = pad.get_button  # type: ignore[attr-defined]
                ax = pad.get_axis  # type: ignore[attr-defined]
                state = PadState(
                    left=bool(g(pygame.CONTROLLER_BUTTON_DPAD_LEFT)),
                    right=bool(g(pygame.CONTROLLER_BUTTON_DPAD_RIGHT)),
                    up=bool(g(pygame.CONTROLLER_BUTTON_DPAD_UP)),
                    down=bool(g(pygame.CONTROLLER_BUTTON_DPAD_DOWN)),
                    a=bool(g(pygame.CONTROLLER_BUTTON_A)),
                    b=bool(g(pygame.CONTROLLER_BUTTON_B)),
                    x=bool(g(pygame.CONTROLLER_BUTTON_X)),
                    y=bool(g(pygame.CONTROLLER_BUTTON_Y)),
                    lb=bool(g(pygame.CONTROLLER_BUTTON_LEFTSHOULDER)),
                    rb=bool(g(pygame.CONTROLLER_BUTTON_RIGHTSHOULDER)),
                    lt=ax(pygame.CONTROLLER_AXIS_TRIGGERLEFT) / 32767.0,
                    rt=ax(pygame.CONTROLLER_AXIS_TRIGGERRIGHT) / 32767.0,
                    stick_x=ax(pygame.CONTROLLER_AXIS_LEFTX) / 32767.0,
                    stick_y=ax(pygame.CONTROLLER_AXIS_LEFTY) / 32767.0,
                )
                for name in PadState.__slots__:
                    value = getattr(state, name)
                    old = merged.get(name)
                    if isinstance(value, bool):
                        merged[name] = bool(old) or value
                    elif old is None or abs(value) > abs(float(old)):  # type: ignore[arg-type]
                        merged[name] = value
        return PadState(**merged) if merged else None  # type: ignore[arg-type]

    def _key_state(self) -> KeyState:
        k = pygame.key.get_pressed()
        return KeyState(
            left=bool(k[pygame.K_LEFT] or k[pygame.K_a]),
            right=bool(k[pygame.K_RIGHT] or k[pygame.K_d]),
            up=bool(k[pygame.K_UP] or k[pygame.K_w]),
            down=bool(k[pygame.K_DOWN] or k[pygame.K_s]),
            shift=bool(k[pygame.K_LSHIFT] or k[pygame.K_RSHIFT]),
            strike=bool(k[pygame.K_SPACE] or k[pygame.K_j]),
            rewind=bool(k[pygame.K_r]),
        )

    def command(self) -> Command:
        return command_from(self._key_state(), self._pad_state())

    def rewind_held(self) -> bool:
        return rewind_from(self._key_state(), self._pad_state())

    def timer_held(self) -> bool:
        return bool(pygame.key.get_pressed()[pygame.K_TAB])


def poll() -> Command:
    """Compatibilidad: sólo teclado."""
    k = pygame.key.get_pressed()
    return command_from(
        KeyState(
            left=bool(k[pygame.K_LEFT] or k[pygame.K_a]),
            right=bool(k[pygame.K_RIGHT] or k[pygame.K_d]),
            up=bool(k[pygame.K_UP] or k[pygame.K_w]),
            down=bool(k[pygame.K_DOWN] or k[pygame.K_s]),
            shift=bool(k[pygame.K_LSHIFT] or k[pygame.K_RSHIFT]),
            strike=bool(k[pygame.K_SPACE] or k[pygame.K_j]),
        )
    )
