# Arquitectura — pop2026

> Reimplementación de Prince of Persia (1989) en Python 3.13+.
> Capas limpias, dominio puro testeable, presentación pygame-ce.

## Vista general

```
┌─────────────────────────────────────────────────────────────────┐
│                       presentation/                             │
│   ┌──────────────┐  ┌────────────┐  ┌──────────────┐            │
│   │  Pygame App  │──│  Renderer  │──│  InputDevice │  (pygame)  │
│   └──────┬───────┘  └────┬───────┘  └──────┬───────┘            │
│          │               │                 │                    │
└──────────┼───────────────┼─────────────────┼────────────────────┘
           │               │                 │
           ▼               ▼                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                       application/                              │
│   ┌──────────────┐    ┌────────────────┐   ┌────────────────┐   │
│   │   GameLoop   │───▶│ AdvanceGameUC  │──▶│  DemoPlayerUC  │   │
│   └──────┬───────┘    └────────┬───────┘   └────────┬───────┘   │
│          │                     │                    │           │
└──────────┼─────────────────────┼────────────────────┼───────────┘
           │                     │                    │
           ▼                     ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                          domain/                                │
│   ┌──────────┐  ┌────────┐ ┌────────┐ ┌─────────┐ ┌──────────┐  │
│   │  Prince  │  │ Guard  │ │ Level  │ │ Combat  │ │  Physics │  │
│   │  (FSM)   │  │  (AI)  │ │ (grid) │ │  (FSM)  │ │  (pure)  │  │
│   └──────────┘  └────────┘ └────────┘ └─────────┘ └──────────┘  │
│   value-objects: Position, Velocity, Tile, Facing, Action, ...  │
└─────────────────────────────────────────────────────────────────┘
           ▲
           │ (interfaces inyectadas hacia abajo)
           │
┌─────────────────────────────────────────────────────────────────┐
│                       infrastructure/                           │
│   ┌────────────┐  ┌───────────────┐  ┌─────────────────┐        │
│   │  RngLfsr8  │  │ LevelLoader   │  │  SaveGameStore  │        │
│   │  (seeded)  │  │ (text → grid) │  │  (JSON / XDG)   │        │
│   └────────────┘  └───────────────┘  └─────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

## Reglas de dependencia

- `domain/` **no importa** nada de las otras capas. Es Python puro + stdlib.
- `application/` importa solo `domain/`. Define puertos (Protocols) que
  `infrastructure/` y `presentation/` implementan.
- `infrastructure/` implementa puertos. Puede importar `domain/`.
- `presentation/` orquesta: importa `application/` y, vía DI, instancias
  concretas de `infrastructure/`.
- `tests/unit` cubren `domain/`. `tests/property` cubren invariantes de
  físicas y FSM. `tests/integration` cubren casos de uso completos
  (incluyendo modo demo determinista).

## Composición

`presentation/app.py` es la única función que sabe instanciar
**concretamente** a `RngLfsr8`, `LevelLoader`, `JsonSaveGameStore` y
pasárselas a `GameLoop`. Es la *composition root*.

## Estructura de directorios

```
src/pop2026/
├── __init__.py
├── __main__.py
├── domain/
│   ├── __init__.py
│   ├── actions.py        # Action enum + transition table
│   ├── tiles.py          # Tile enum + helpers
│   ├── geometry.py       # Position, Velocity, Bounds (frozen dataclasses)
│   ├── prince.py         # Prince entity + FSM step
│   ├── guard.py          # Guard entity + AI step
│   ├── level.py          # Level (grid of tiles, rooms)
│   ├── combat.py         # Combat resolution (pure, RNG-injected)
│   ├── physics.py        # Apply gravity, collisions, edges
│   ├── game.py           # Game aggregate, advance(dt, input, rng)
│   ├── input.py          # PlayerCommand enum
│   ├── ports.py          # Protocols (Rng, LevelSource, SaveStore)
│   └── errors.py         # Domain exceptions
├── application/
│   ├── __init__.py
│   ├── game_loop.py      # Frame stepper, tick scheduler
│   ├── advance_game.py   # Use case: one tick
│   └── demo_player.py    # Use case: scripted inputs from seed
├── infrastructure/
│   ├── __init__.py
│   ├── rng.py            # LFSR-8 deterministic RNG
│   ├── levels.py         # Text-format level loader
│   ├── savegame.py       # XDG JSON store
│   └── builtin_levels/   # *.poplv text files
├── presentation/
│   ├── __init__.py
│   ├── app.py            # Composition root
│   ├── cli.py            # Typer entrypoint
│   ├── renderer.py       # pygame surface drawing
│   ├── input_device.py   # pygame → PlayerCommand mapping
│   ├── audio.py          # Beeper synth (numpy → pygame mixer)
│   ├── theme.py          # Palette, sizes, glyphs
│   └── screens/
│       ├── title.py
│       ├── play.py
│       └── ending.py
└── assets/
    ├── levels/           # symlink or copy of builtin_levels (data)
    └── README.md
```

## Bucle de juego (60 Hz lógico)

```
while running:
    dt_real = clock.tick(60)
    inputs  = input_device.poll()
    for _ in range(num_logic_ticks(dt_real)):
        game = advance_game.execute(game, inputs, rng)
    renderer.draw(game)
```

Tick lógico = 1/60 s. Input se lee 60 veces/s. Render 60 veces/s
(podríamos desacoplar; en v1.0 lo dejamos atados para simplificar). El
desacople permite el modo `--demo` y los tests E2E sin pygame.

## Modo demo

`DemoPlayerUC` consume una lista fija de comandos parametrizada por
seed. La misma seed produce la misma demo. Esto se usa para:

1. Aprobar visualmente que el motor sigue funcionando tras refactors.
2. Grabar GIFs/SVGs sin un humano sentado a las teclas.
3. Tests E2E que ejecutan `--demo --seed 42 --frames 600` y verifican
   que el príncipe llega vivo a la salida del nivel 1.

## Persistencia

`~/.local/share/pop2026/save.json` (XDG). Estructura:

```json
{
  "version": 1,
  "level": 2,
  "hp": 4,
  "max_hp": 4,
  "time_left_ms": 3450000,
  "rng_seed": 42
}
```

Un slot único, como el original.

## Errores y manejo

`PopError` raíz; subclases en `domain/errors.py`:

- `InvalidActionTransition`
- `LevelLoadError`
- `SaveCorruptedError`

`presentation/cli.py` traduce a *exit codes* + mensaje legible con
`rich`.
