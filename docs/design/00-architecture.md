# `docs/design/00-architecture.md` — Arquitectura del motor `pop2026canon`

> **Estatus**: FASE 2.0 — bootstrap. Documento padre que define el
> alcance y la división por subsistemas. Cada subsistema tiene su
> propio doc detallado (`01-*`..`11-*`).

## 1. Objetivo

Construir un clon jugable de Prince of Persia (1989) con **paridad
funcional** respecto al original. Lo que el usuario verá:

- 14 niveles canónicos cargados desde `levels.dat` (o equivalente).
- Tile-based physics con frames rotoscopiados (~180 frames del prince).
- Hang/climb manual con SHIFT.
- Chomper, slicer, loose floor con timing canónico.
- Shadow man en niveles 4, 5, 6, 12.
- Skeleton en nivel 3.
- Vizier (Jaffar) y Princess como chars especiales con secuencias
  propias.
- Cinemática final con ratón.
- Tiempo límite real (60 min in-game).

## 2. Pilares arquitectónicos

| Pilar | Decisión |
|---|---|
| Lenguaje | Python 3.13+ |
| Render | pygame-ce (mantenemos del proyecto actual) |
| Patrón | Hexagonal — `domain` ← `application` ← `infrastructure` / `presentation` |
| Estado | `@dataclass(frozen=True, slots=True)` — todo inmutable |
| Loop | **12 FPS lógicos** (canon), **60 FPS visual** con interpolación |
| Globals | Cero. Constantes en módulos `data.py` por subsistema |
| Tests | Por subsistema en `tests/canon/test_NN_*.py` |
| Tipos | `mypy --strict` obligatorio |
| Lint | `ruff format` + `ruff check` |

## 3. Layout de paquetes

```
src/pop2026canon/
├── domain/                # Lógica pura — sin pygame, sin I/O
│   ├── actions.py         # action_0_stand .. action_99_hurt
│   ├── frames.py          # ~180 frame definitions (id, dx, dy, sound, flag)
│   ├── seqtbl.py          # 94 secuencias con act/dx/dy/jmp/snd
│   ├── tiles.py           # 31 tile types
│   ├── chars.py           # CharType (kid, shadow, guard, ...)
│   ├── physics.py         # gravity, collision, frame advance
│   ├── combat.py          # take_hp, sword_strike, parry resolution
│   ├── traps.py           # chomper, slicer, loose_floor, spike state machines
│   ├── room.py            # Room (10x3 grid + links N/S/E/W)
│   ├── level.py           # Level (24 rooms + guards + start_pos + exit)
│   ├── shadow.py          # Triggers de shadow encounters
│   ├── skeleton.py        # Skeleton wake-up logic
│   ├── vizier.py          # Jaffar AI
│   ├── princess.py        # Princess animations
│   └── game.py            # Game aggregate (kid + room + state + timer)
│
├── application/
│   ├── controller.py      # Input → command → action transition
│   ├── tick.py            # Step lógico 12 FPS
│   ├── campaign.py        # 14 niveles + cinemáticas
│   └── replay.py          # Replay format (estilo SDLPoP .p1r)
│
├── infrastructure/
│   ├── levels_dat.py      # Parser del binario levels.dat
│   ├── savegame.py        # Save slot format
│   ├── rng.py             # LFSR-8 determinista
│   └── audio_assets.py    # Generación de SFX/music
│
├── presentation/
│   ├── renderer.py        # Loop visual 60 FPS + interpolación
│   ├── tile_atlas.py      # Sprites tile (back/fore/overlay)
│   ├── char_atlas.py      # Sprites por frame del kid/shadow/guard/...
│   ├── hud.py             # Time, HP, sword status
│   ├── input_device.py    # Teclado → InputFrame
│   └── screens/           # Title, card, cutscene, ending
│
└── cli.py                 # Typer entry point
```

## 4. Modelos clave

### `domain.frames.Frame`

```python
@dataclass(frozen=True, slots=True)
class Frame:
    id: int                    # 0..180
    sprite: str                # nombre del sprite atlas
    dx: int                    # desplazamiento horizontal en px (relativo al char)
    dy: int                    # desplazamiento vertical en px
    flags: int                 # bit flags: sound, weight shift, etc.
```

180 frames precomputados en `domain/frames.py` (constantes inmutables).

### `domain.seqtbl.SeqAct`

```python
class ActKind(IntEnum):
    FRAME = 0       # mostrar frame N
    DX = 1          # tile-shift horizontal
    DY = 2          # tile-shift vertical
    SND = 3         # play sound N
    SET_FALL = 4    # set fall_x, fall_y
    JMP = 5         # jump to seq label

@dataclass(frozen=True, slots=True)
class SeqAct:
    kind: ActKind
    arg: int
    arg2: int = 0   # para SET_FALL (dx, dy)

Sequence = tuple[SeqAct, ...]
```

`domain.seqtbl.TABLE: dict[int, Sequence]` con las 94 entradas.

### `domain.chars.Char`

```python
@dataclass(frozen=True, slots=True)
class Char:
    charid: int             # 0..6, 0x18
    room: int               # 0..23
    curr_col: int           # 0..9 dentro de la sala
    curr_row: int           # 0..2
    x: int                  # 0..13 px sub-tile
    y: int                  # 0..62 px sub-tile
    direction: int          # -1 left, +1 right
    frame: int              # ID actual
    curr_seq_idx: int       # posición en seqtbl
    action: int             # action_0..action_99
    fall_x: int             # momentum horizontal en caída
    fall_y: int             # velocidad vertical de caída
    hp_curr: int
    hp_max: int
    sword: int              # 0 sheathed, 2 drawn
    alive: int              # -1 vivo, >=0 frames muerto
    repeat: int             # iteraciones del seq actual
```

Coincide 1-a-1 con `char_type` de `types.h`.

### `domain.room.Room`

```python
@dataclass(frozen=True, slots=True)
class Room:
    fg: tuple[int, ...]            # 30 tiles foreground (10x3)
    bg: tuple[int, ...]            # 30 tiles background/modifier
    links: tuple[int, int, int, int]  # N, S, E, W → room idx o 0 (wall)
    guards: tuple[GuardSpawn, ...]
```

### `domain.level.Level`

```python
@dataclass(frozen=True, slots=True)
class Level:
    number: int                # 1..14
    rooms: tuple[Room, ...]    # 24 elementos (huecos = empty room)
    start_room: int            # 1..24
    start_col: int             # 0..9
    start_row: int             # 0..2
    start_direction: int
    events: tuple[Event, ...]  # shadow_appear, skeleton_wake, etc.
```

### `domain.game.Game`

```python
@dataclass(frozen=True, slots=True)
class Game:
    level: Level
    kid: Char
    others: tuple[Char, ...]   # shadow, guards, princess, mouse, vizier
    state: LevelState          # gates abiertas, loose caídos, potions consumidas
    time_left_minutes: int     # 60..0
    time_left_ticks: int       # 0..719
    flags: int                 # bits: shadow_initialized, sword_picked, etc.
```

## 5. Loop

```
12 Hz lógico:
  for tick in 12_fps:
      cmd = controller.poll()
      game = tick.advance(game, cmd)
      replay.record(cmd)

60 Hz visual:
  for frame in 60_fps:
      t = (frame % 5) / 5.0    # interpolación entre ticks
      renderer.draw(game_prev, game_curr, t)
```

`advance(game, cmd)`:
1. Process commands → posible cambio de seq del kid
2. Para cada char (kid, others): `play_seq(char)` ejecuta los acts
   hasta el próximo FRAME
3. `physics.apply_falling(char)` aplica gravedad si in_freefall
4. `physics.check_collision(char, room)` reverte movs inválidos
5. `physics.check_grab(kid, cmd.shift)` evalúa hang
6. `traps.tick_all(state)` chompers/slicers/loose
7. `combat.resolve(kid, guard)` si comparten room
8. `events.fire(game)` shadow/skeleton triggers
9. `time.advance(game)` -1 tick

## 6. Renderer

- Carga `tile_atlas` y `char_atlas` (sprites individuales por frame).
- En cada frame visual interpola sub-pixel entre `game_prev` y
  `game_curr` (sólo posición del char; los tiles no se interpolan).
- Pinta orden:
  1. Back wall (sala adyacente sombreada — efecto profundidad)
  2. BG tiles (overlays bajo el char)
  3. Chars en el orden adecuado (princess sobre suelo, kid sobre
     princess en abrazo, etc.)
  4. FG tiles (gates, lattices que tapan al char)
  5. HUD: tiempo, hp, sword status

## 7. Plan de migración

El motor actual `src/pop2026/` se **conserva** durante la transición.
El nuevo motor vive en `src/pop2026canon/`. Cuando esté completo:
- `pop2026canon` se renombra a `pop2026`
- El viejo motor se borra
- CLI cambia el entry point

Durante la migración, ambos pueden coexistir. Tests separados.

## 8. Roadmap subsistemas

| # | Doc | Contenido | Días estimados |
|---|---|---|---|
| 01 | `tile-renderer.md` | Atlas tiles, capas, overlays | 2 |
| 02 | `frame-system.md` | Atlas char, seqtbl runner | 3 |
| 03 | `tile-physics.md` | Frame advance, collision, gravity | 3 |
| 04 | `room-graph.md` | Room/Level model + levels.dat parser | 3 |
| 05 | `traps.md` | Chomper, slicer, loose, spike state machines | 2 |
| 06 | `combat.md` | take_hp, strike, parry, knockback | 2 |
| 07 | `guard-ai.md` | Skill table, patrol, alert, combat | 2 |
| 08 | `shadow.md` | 4 encounter scripts | 2 |
| 09 | `time-limit.md` | 60 min countdown + princess timer | 1 |
| 10 | `audio.md` | Jingles, footsteps, sword clash | 1 |
| 11 | `saves.md` | Slot format, quicksave | 1 |

**Total docs FASE 2**: ~22 días-hombre. Realista: 3-5 días con foco.

## 9. Definition of done por nivel (FASE 3)

Para considerar un nivel cerrado:

- [ ] Layout tile-a-tile cargado de `levels.dat`
- [ ] Todos los guards instanciados con HP correcto de `tbl_guard_hp`
- [ ] Todas las trampas (chomper, slicer, spike, loose) activas
- [ ] Pressure plates / gates funcionales
- [ ] Potions de todos los tipos canónicos
- [ ] Exit alcanzable
- [ ] Eventos especiales del nivel (shadow, skeleton, mouse, princess)
- [ ] Playthrough manual documentado
- [ ] Replay determinista grabado y reproducible

## 10. Riesgos

| Riesgo | Mitigación |
|---|---|
| 180 frames a dibujar | Render procedural por capas (no sprites pixelados) — paleta paramétrica |
| Carga de `levels.dat` sin dump | Implementar parser binario desde docs comunidad princed.org |
| Audio jingles canónicos | Beeper sintético basta como tributo; no replicar AdLib literalmente |
| Cinemáticas (intro, princess, ending) | Estilo "tarjeta de texto" mínima; aceptamos deuda visual |
| Skill table del guard | Aproximación con tabla simple si no se consigue el reverso |
| Tiempo de implementación | Iteraciones quincenales; entregar bloques verticales (un nivel completo end-to-end) |

---

**Documento padre cerrado. Próximo: `01-tile-renderer.md`.**
