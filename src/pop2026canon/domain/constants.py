"""Constantes canónicas extraídas de SDLPoP (verificadas en `docs/audit.md`).

Todos los valores son del original POP1. No tocar sin justificación
documental — referenciar el offset de `src/types.h` o `src/data.h`.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Geometría del mundo (types.h)
# ---------------------------------------------------------------------------

TILE_SIZE_X: int = 14
"""Píxeles canónicos por tile horizontal."""

TILE_SIZE_Y: int = 63
"""Píxeles canónicos por tile vertical. POP usa tiles altos no cuadrados."""

SCREEN_TILECOUNT_X: int = 10
"""Columnas por sala."""

SCREEN_TILECOUNT_Y: int = 3
"""Filas por sala."""

ROOM_TILES: int = SCREEN_TILECOUNT_X * SCREEN_TILECOUNT_Y
"""30 tiles por sala."""

ROOMCOUNT: int = 24
"""Máximo de salas por nivel."""

SCREEN_GAMEPLAY_HEIGHT: int = 192

# ---------------------------------------------------------------------------
# Física (types.h)
# ---------------------------------------------------------------------------

FALLING_SPEED_MAX: int = 33
"""Velocidad de caída máxima en sub-tile px/tick."""

FALLING_SPEED_ACCEL: int = 3
"""Aceleración gravitacional por tick."""

FALLING_SPEED_MAX_FEATHER: int = 4
"""Caída máxima bajo el efecto de poción de pluma."""

FALLING_SPEED_ACCEL_FEATHER: int = 1
"""Aceleración bajo poción de pluma."""

FEATHER_FALL_LENGTH: float = 18.75
"""Duración en segundos de la poción de pluma."""

GRAB_FALL_Y_THRESHOLD: int = 32
"""``check_grab`` exige fall_y < 32 para enganchar."""

GRAB_TIMER_INITIAL: int = 12
"""Duración del grab inicial en frames."""

# ---------------------------------------------------------------------------
# Loop lógico (BASE_FPS de types.h)
# ---------------------------------------------------------------------------

BASE_FPS: int = 60
"""Frame rate visual. Mantenido por compatibilidad con motor moderno."""

LOGIC_FPS: int = 12
"""Frame rate lógico canónico. POP1 corre la simulación a 12 FPS."""

VISUAL_FRAMES_PER_TICK: int = BASE_FPS // LOGIC_FPS
"""Frames visuales entre ticks lógicos. Para interpolación."""

# ---------------------------------------------------------------------------
# HP & combat (data.h)
# ---------------------------------------------------------------------------

START_HITP: int = 3
"""HP inicial del kid."""

MAX_HITP_ALLOWED: int = 10
"""HP máximo permitido."""

TBL_GUARD_HP: tuple[int, ...] = (4, 3, 3, 3, 3, 4, 5, 4, 4, 5, 5, 5, 4, 6, 0, 0)
"""HP del guard por nivel (1..14, +2 sentinelas)."""

NUM_GUARD_SKILLS: int = 12
"""Skills 0..11."""

# ---------------------------------------------------------------------------
# Tiempo (data.h)
# ---------------------------------------------------------------------------

START_MINUTES_LEFT: int = 60
"""60 minutos in-game para rescatar a la princesa."""

START_TICKS_LEFT: int = 719
"""Ticks fraccionarios del primer minuto."""

TICKS_PER_MINUTE: int = 720
"""60 segundos x 12 ticks/s = 720 ticks lógicos por minuto."""

# ---------------------------------------------------------------------------
# Trampas y velocidades (data.h)
# ---------------------------------------------------------------------------

LOOSE_FLOOR_DELAY: int = 11
"""Ticks de presión antes de que el loose floor ceda."""

BASE_SPEED: int = 5
"""Velocidad base del kid."""

FIGHT_SPEED: int = 6
"""Velocidad en modo combate."""

CHOMPER_SPEED: int = 15
"""Ticks por ciclo del chomper."""

# ---------------------------------------------------------------------------
# Memoria (types.h)
# ---------------------------------------------------------------------------

TROBS_MAX: int = 30
"""Trampas/objetos activos máximo simultáneo."""

NUM_TIMERS: int = 3
