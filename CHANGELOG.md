# Changelog

Todas las novedades reseñables. Formato basado en [Keep a Changelog]; el
versionado sigue [SemVer].

[Keep a Changelog]: https://keepachangelog.com/es/1.1.0/
[SemVer]: https://semver.org/lang/es/

## [canon-0.7.0] — 2026-05-15

### Combate REAL + trampas verificadas + IA de guard

Auditoría profunda del gameplay tras feedback "los niveles no tienen
sentido, la lucha no funciona". Confirmado: los guards eran estatuas
inertes, el kid los mataba sin oposición. Arreglos:

- **IA de guard** (`domain/guard.py` nueva):
  - FSM determinista por seed (tick + room + idx).
  - Estados: idle / face / advance / strike / block.
  - Cuando el kid está adyacente, el guard ataca con probabilidad
    creciente según skill (0..11), bloquea strikes entrantes según
    `prob_block` del skill.
  - Avanza hacia el kid si está en la misma row a distancia >1.
  - Cooldown (`refractory`) tras cada strike/block.
  - Integrada en `tick.advance` entre special chars y combat.
- **`Char.skill: int`** nuevo campo para los 12 niveles canon de skill.
  Guards spawnan con `SwordStatus.DRAWN` y skill heredado del GuardSpawn.
- **Combat fixes**:
  - `can_strike` exige attacker.sword == DRAWN (antes el kid sin
    espada hacía daño — bug).
  - Tras conectar un strike, `_exit_strike_window` avanza la secuencia
    del atacante para salir de los frames 165-167 y evitar multi-hit
    triple en la misma animación.
  - `take_hp` no letal devuelve al char a Action.STAND (no parálisis
    HURT permanente, gameplay responsivo).
- **Tests de gameplay end-to-end** (`test_gameplay.py` nuevo, 10 tests):
  - Guard adyacente mata al kid pasivo en pocos ticks.
  - Guard distante avanza hacia el kid.
  - Kid con espada mata al guard usando STRIKE repetido.
  - Kid sin espada NO hace daño (regresión documentada).
  - Chomper mata al kid en su fase letal.
  - Spike mata al kid aterrizando con fall_y alto.
  - Loose floor cae tras LOOSE_FLOOR_DELAY ticks.
  - Gate cerrada es sólida.
  - Kid recoge sword pisándola (`SwordStatus.DRAWN`).
  - Mouse de L8 abre la gate de su sala.

**Tests**: 687 verdes (677 previos + 10 gameplay). mypy strict + ruff
limpios.

## [canon-0.6.0] — 2026-05-15

### Plataformas multi-altura intra-sala + L14 jugable + diversidad canon

Refactor profundo de las salas planas: ahora cada nivel mezcla plataformas
elevadas, arenas con columnas y salas escalonadas para que el juego se
sienta como POP1 — saltos verticales, posiciones elevadas, combate en
arena con cobertura, no sólo corredores.

- **Helpers nuevos**: `_platform_rows(platform_cols, pit_cols)` mete
  plataforma DOORTOP_WITH_FLOOR en row 1 (segundo piso interno);
  `_split_rows(upper_cols, lower_cols, pit_cols)` da una sala
  escalonada con plataforma elevada a un lado; `_arena_rows(pillar_pair)`
  da una sala-arena con dos columnas BIGPILLAR enmarcando el combate.
- **L14 jugable** (3 salas): pórtico de entrada con plataforma y
  antorchas → galería de escaleras con lattices y doortop ceremonial →
  cámara real con pillars y la princesa esperando.
- **Refactor de salas**: ~25 salas reelaboradas en L1, L2, L3, L4, L5,
  L6, L7, L8, L9, L11, L12 para usar plataformas, splits o arenas en
  lugar de corredores planos.
- **Tests de plataforma** (`test_pathfinding.py` extendido):
  - `test_no_more_than_two_flat_corridors_per_level`: cada nivel
    jugable tiene ≤2 salas que son corredores planos puros.
  - `test_level_has_platform_features`: cada nivel usa al menos una
    plataforma elevada (DOORTOP_WITH_FLOOR en row 1) o lattice
    escalable.

**Tests**: 677 verdes (651 previos + 26 nuevos plataforma/contenido).
mypy strict + ruff format+check limpios.

## [canon-0.5.0] — 2026-05-15

### Niveles canon **completos** 18-24 salas + hang-shuffle + path-finding

Tirón largo para llevar los niveles al tamaño/complejidad del canon real:

- **Reescritura completa de `levels_canon.py`**: nuevo sistema declarativo
  basado en `_RoomSpec` + `_build_level`. Helpers ricos: `_floor_rows`,
  `_drop_rows`, `_pillar_rows`, `_lattice_rows`, `_balcony_rows`,
  `_doortop_rows`. Cada nivel se construye como lista de specs.
- **Niveles a tamaño canon**: L1=18, L2=20, L3=18, L4=20, L5=20, L6=18,
  L7=22, L8=20, L9=20, L10=20, L11=20, L12=24, L13=18, L14=1. Total
  ~257 salas (vs. 80 antes).
- **Layouts multi-piso** con loops, galerías paralelas, sub-rooms
  secretos, salas-cripta accesibles por drop sur.
- **Diversidad de tiles**: usadas BIGPILLAR_TOP/BOTTOM (columnas
  estructurales), LATTICE_PILLAR (rejas escalables), BALCONY_LEFT/RIGHT,
  DOORTOP_WITH_FLOOR (multi-piso intra-sala), TORCH, POTION con
  variantes HEAL/MAX_HP/POISON/FLOAT/TIME/EMPTY.
- **Doorlinks complejos**: múltiples plates por gate, plates lejanas que
  abren gates en otra sala, puzzles locales (plate+gate same-room).
- **Hang-shuffle + release-hang en `physics.py`**: `hang_shuffle(char,
  room, direction)` mueve lateralmente colgado de cornisa; `release_hang`
  pasa a IN_FREEFALL. Integrado en `tick.advance` cuando el char está en
  HANG_STRAIGHT y hay input left/right.
- **Test de path-finding BFS** (`test_pathfinding.py`):
  - `test_level_exit_room_reachable_from_spawn`: cada nivel jugable
    tiene exit alcanzable por grafo de salas.
  - `test_no_orphan_rooms`: máx 2 salas secretas por nivel.
  - `test_level_cell_pathing_partial`: BFS celda-a-celda confirma que
    el spawn alcanza al menos 2 salas distintas.
  - `test_tile_diversity_across_levels`: ≥15 tipos de tile usados.
  - `test_uses_lattice_tiles`, `test_uses_pillar_and_balcony`,
    `test_potions_have_diverse_modifiers`.

**Tests**: 651 verdes (575 previos + 11 hang-shuffle + 65 pathfinding/
content/diversity). mypy strict + ruff format+check limpios.

## [canon-0.4.0] — 2026-05-15

### Poster canon + intro animada + level cards en todos los niveles

Cinemática y presentación visual al nivel del original (tributo
procedural, sin reproducir el arte):

- **`presentation/poster.py`** nuevo: poster procedural en 5 capas
  (cielo nocturno con estrellas titilantes → luna llena con halo →
  palacio de minaretes con cúpula central y ventanas iluminadas →
  cortinas rojas con pliegues + cordones dorados → siluetas de
  princesa/Jaffar/prince/guard usando el atlas con paletas). API
  `draw_poster(...)` con `PosterCast` y `curtain_openness` 0..1
  para animar apertura.
- **`LEVEL_CASTS`** mapea cada nivel 1..14 a un cast narrativo:
  L3 sólo prince, L4-6 prince+vizier (sombra), L12 trío completo,
  L13 sin vizier (ya derrotado), L14 reunion con princesa.
- **Intro animada** (`screens/title.py`): cortinas cerradas + fade
  desde negro → easing cubic out → cortinas abriéndose mientras el
  título aparece a partir del 45% → estado estable con controles.
  Duración 3.5 s.
- **Level cards** (`screens/cutscene.py`): cada nivel se presenta
  con el poster + cast del nivel como fondo y un panel central con
  nombre, número, tagline y "Pulsa ENTER" parpadeante.
- **CLI**:
  - `pop2026canon poster --level N --out file.png --time T`: genera
    PNG del poster (level=0) o level card de un nivel concreto.
  - `pop2026canon --skip-intro`: salta la cinemática y empieza en
    el level card.
  - Game loop ahora tiene fases TITLE → LEVEL_CARD → PLAYING →
    ENDING con transiciones por ENTER.
- **Paleta**: nuevos `poster_curtain`, `poster_curtain_dark`,
  `poster_sky`, `poster_sky_light`, `poster_moon`, `poster_palace`,
  `poster_palace_dark`, `poster_gold`, `poster_gold_dark`.

**Tests**: 575 verdes (564 previos + 11 en `test_poster.py` que
cubren cast por nivel, render sin crash, comparativa de cortinas
y level card de cada nivel). mypy strict + ruff limpios.

## [canon-0.3.0] — 2026-05-15

### Niveles 4-13 refinados con layouts canon ricos

Los stubs corredor-plano de L4-L13 se reemplazan por layouts con
mecánicas variadas y progresión coherente:

- **L4 The Mirror**: loose en sala 1, slalom de pinchos, pit central que
  fuerza runjump, mirror + potion, plate+chomper, gate doorlinked al
  exit con guard skill 3.
- **L5 The Thief**: triple loose en sala 2 (slalom rápido), chomper+spike,
  potion objetivo del shadow, segundo loose, plate→gate doorlink al
  exit.
- **L6 The Steps**: pit grande en sala 1 (cols 4-6) que dispara
  shadow_step en frame 43, plate+chomper en sala 3, doorlink a gate
  sala 2, guard skill 4 con spike adyacente.
- **L7 The Mountains**: layout en "L" con drop sur por col 8, jardín
  de pinchos, loose escalonadas en el piso bajo, doble chomper.
- **L8 The Caverns**: drop al sur cols 4-5, 4 loose floors en sala 4,
  doble chomper, gate locked que sólo el mouse abre.
- **L9 The Tomb**: dos skeletons + jardín de spikes + doble chomper +
  plate→gate doorlink + potion heal.
- **L10 The Tower**: torre puramente vertical con drop_rooms de
  plataformas estrechas en cada nivel + spike garden + guards skill 5.
- **L11 The Tower II**: combina horizontal + vertical, doble chomper,
  loose intermedia, drop final con plate+gate locales.
- **L12 The Vizier**: 8 salas con spike, doble chomper, potion max_hp,
  pit con loose, mirror+potion heal para fusión, arena del vizier
  skill 11 con spikes laterales.
- **L13 Final Run**: 4 salas en carrera — triple chomper en cadencia,
  spike garden con loose intermedia, pit con spikes a los lados.

**Helpers nuevos**: `_corridor(..., pit_cols=..., no_ceiling=...)` y
`_drop_room(..., floor_cols=...)` para layouts verticales.

**Tests**: 564 verdes (541 previos + 23 nuevos en
`test_levels_content.py` que validan tiles+eventos+room counts+links).
mypy strict + ruff limpios.

## [canon-0.2.0] — 2026-05-15

### Motor canon — cierre final

Tras el commit `4d49b97` (FASES 0→3.8) este release cierra los flecos
documentados como deuda técnica en el motor `pop2026canon`:

- **Doorlinks plate→gate específicos**: nuevo `DoorLink` dataclass en
  `domain/level.py`, campo `doorlinks: tuple[DoorLink, ...]` en `Level`.
  El bucle `_tick_traps` consulta `level.plates_for_gate(...)` para
  decidir si una gate se abre. Reemplaza el modelo "cualquier plate abre
  cualquier gate" del prototipo. Doorlinks declarados en L6 y L11.
- **Mouse abre gates sin plate (L8)**: `trigger_mouse_appear` fuerza
  `state=7` + `open_gate` en las gates de la sala sin doorlink. Tests
  cubren la apertura y la no-apertura de gates desconectadas.
- **Seqtbl extendido a 40 secuencias operativas**: añadidas ENGARDE,
  ADVANCE, RETREAT, BLOCK_STRIKE, BLOCK_TO_STRIKE, PUT_SWORD_AWAY,
  RUNTURN, BUMP, BUMPED_FALL, HARD_LAND, MED_LAND, GUARD_FALL,
  JUMP_HANG_MIDAIR, EXIT_LEVEL. Cubre todo el combate canon + locomoción
  + transición final. SND_BUMP, SND_HARDLAND, SND_EXIT añadidos.
- **Packaging integrado**: `pyproject.toml` ahora declara `pop2026canon`
  en `[tool.hatch.build.targets.wheel].packages` y `[project.scripts]`
  (`pop2026canon = "pop2026canon.cli:app"`). `[tool.coverage.run]` cubre
  los dos paquetes.

**Tests**: 532 verdes (523 previos + 11 doorlinks + 9 seqtbl + sanity
mouse-gate). `mypy --strict` y `ruff format+check` limpios en los 39
archivos del motor canon.

## [4.2.0] — 2026-05-14

### Pulido jugable + polish visual

**Gameplay:**

- `input_device.poll()` ahora emite `jump_pressed` / `jump_held`
  como canal independiente de `command`, permitiendo *running jump*
  real para el jugador humano (antes una sola tecla a la vez).
- Knockback equilibrado tras experimentar bajadas (mantenido
  `VX=0.30`, `TICKS=10` para asegurar separación de combatientes).
- Test de integración `test_demo_bot_wins.py` parametrizado con
  10 niveles fáciles: garantiza que cambios futuros no rompen
  jugabilidad básica con seed determinista.

**Visuales:**

- Animación de muerte: colapso gradual del torso durante 30 ticks
  con interpolación lineal y charco de sangre creciente bajo el
  cuerpo a partir del 70% de la animación.
- Respiración sutil del príncipe en pose `STAND`: bob vertical
  de 1 px usando `sin(ticks * 0.06)`.
- Estela del sable durante la ventana de impacto (STRIKE/LUNGE):
  3 capas con `BLEND_ADD` en color acento + chispa blanca en la
  punta. Mucho más legible que la línea simple anterior.

**Tests**: 320 verdes (310 anteriores + 10 nuevos bot wins).

## [4.1.0] — 2026-05-14

### Híbrido pragmático: micro-pasos + sombra + multi-pantalla

- **`Action.ADVANCE` / `Action.RETREAT`** — micro-pasos de medio
  tile cuando el príncipe tiene sable y un guardia está a
  ≤ `COMBAT_NEAR_CELLS` (2 celdas). LEFT/RIGHT pasan a ser
  paso corto en lugar de carrera, evocando el duelo del original.
- **Mirror guard** — `Guard.is_mirror`: clon-espejo que copia el
  input del príncipe con LEFT↔RIGHT invertidos. Nuevo
  `Tile.SPAWN_MIRROR` (carácter `'m'`).
- **`L13 'La Sombra'`** — duelo cuerpo a cuerpo contra el clon.
- **`L14 'El Trono'` y `L15 'La Huida'`** — niveles finales
  hand-crafted. `HAND_CRAFTED_COUNT` sube de 12 a 15.
- **Multi-pantalla por defecto** — `NARROW_COLS=40` (antes 20),
  `WIDE_COLS=60` (antes 40). Todos los `.poplv` built-in
  reescalados a 40 columnas.

### Tests

- `test_advance_moves_half_cell_forward`,
  `test_retreat_moves_half_cell_back`,
  `test_advance_only_triggers_with_sword_and_guard_near`.
- `test_mirror_walks_opposite_when_prince_moves_left/right`,
  `test_mirror_copies_strike`.
- Suite total: **310 verdes**.

## [4.0.0] — 2026-05-14

### Cambio fundamental — platformer real

El motor pasa de FSM-por-celdas (esencialmente roguelike con
disfraz de plataformas) a **physics-based platformer** con
coordenadas continuas. `PhysicsPrince` reemplaza al `Prince`
discreto como motor por defecto.

### Game-feel platformer 2026

- **Coyote time** (6 ticks): saltar después de dejar una plataforma.
- **Jump buffer** (6 ticks): JUMP pulsado en el aire se consume al
  aterrizar.
- **Variable jump height**: soltar JUMP durante el ascenso corta
  la velocidad vertical en 0.45×.
- **Air control**: aceleración horizontal en el aire `0.025`
  vs `0.10` en suelo.
- **Knockback dirigido**: golpe del enemigo empuja al príncipe en
  sentido opuesto y bloquea input por 10 ticks.
- `JUMP_VEL=-0.55` (pico ~2.5 celdas), `JUMP_REACH=4` celdas.
- `last_impact_vy` propaga la velocidad de aterrizaje; spikes
  letales solo si vy ≥ `SPIKE_LETHAL_VY=0.30`.

### Combate continuo (R4)

- **Alcance Euclídeo**: STRIKE 1.0 celdas, LUNGE 2.0 celdas en
  distancia float (no por adyacencia entera).
- **Cono frontal de parada**: PARRY solo bloquea si el defensor
  mira hacia el atacante.
- **Knockback** aplicado vía `with_damage(from_direction=±1)`.

### Verticalidad real

- L8 y L11 rediseñados con plataformas intermedias que requieren
  jump precision.
- Reachability BFS ajustada a los nuevos rangos
  (`JUMP_REACH=4`, `MAX_FALL_DROP=8`).

### Tests

- `test_physics_prince.py`: 5 tests nuevos sobre los game-feel
  essentials (coyote, buffer, var jump, air, knockback).
- `test_combat.py`: migrado a `PhysicsPrince`; 5 tests nuevos para
  alcance Euclídeo, cono de parry y knockback.
- 301 tests verdes, ruff/format/mypy --strict limpios.

### Compat

- `domain/prince.py` (Prince discreto) queda como módulo
  deprecated. Sus tests siguen pasando como referencia histórica.
- `physics_prince.PhysicsPrince` queda alias-importado como `Prince`
  en `combat.py` y `renderer.py` para compatibilidad de tipos.
- `InputFrame` gana `jump_held: bool` para soportar variable jump.

---

## [3.0.0] — 2026-05-13

### Modernizado / añadido en v3.0

- **100 niveles encadenados** en 4 actos de 25:
  Acto I "Mazmorra" (1-25), Acto II "Prisión" (26-50),
  Acto III "Palacio" (51-75), Acto IV "Torre" (76-100).
- **12 niveles hand-crafted** (los originales de v1.0) + **88 procedurales**
  por semilla determinista. Misma `--seed` reproduce la misma campaña
  byte a byte.
- **Generador procedural** en `application/level_generator.py`:
  esqueleto + densidad + actores + validación BFS + reintentos.
- **Reachability BFS** en `domain/reachability.py`: garantiza que cada
  nivel generado tiene al menos un camino del spawn al exit.
- **Curva de dificultad** declarativa en `application/difficulty.py`:
  monótona dentro de cada acto, escalón al cambiar; jefe en cada local
  24, esqueleto inmortal aparece en Acto IV a partir del local 12.
- **Tiempo por nivel** (no global): cada nivel arranca con su propio
  cronómetro derivado del acto (90/75/60/50 segundos).
- **Auto-save tras cada nivel ganado** hasta el 100; `--resume` carga
  la partida.
- **HUD** muestra acto + `N/100`.
- **Cinemáticas por acto** (4 escenas + final 100): `act1`, `act2`,
  `act3`, `act4`, `victory100`.
- **Música ambient por zona** (4 loops sintetizados): dungeon, prison,
  palace, throne. Cada acto tiene su pista.
- **CLI** acepta `--start-level [1..100]`, `--difficulty hard`,
  `--resume`, `--seed`, etc.
- **Tests**: 290+ verdes en menos de 2 s, 90 % cobertura en dominio,
  property tests con hypothesis para invariantes del generador.
- ADR 0006: justificación del enfoque procedural híbrido.

### Bugs corregidos en v3.0

- BFS de alcanzabilidad ya **no permite saltar sobre rejas cerradas**
  (antes la trayectoria horizontal del salto direccional ignoraba la
  celda intermedia).
- Esqueleto inmortal solo aparece a partir de Acto IV, local 12 (antes
  aparecía en todo el Acto IV por una constante mal asignada).

---

## [1.0.0] — 2026-05-13

### Preservado del original

- **Géneros de obstáculos**: pinchos (`spikes`), suelo suelto que se
  rompe al pisarlo (`loose floor`), placas de presión que abren puertas
  (`pressure → gate`), pociones curativas y venenosas.
- **Mecánica de combate**: sable, golpe (`strike`), parar (`parry`),
  daño doble por la espalda. Dos niveles de habilidad del guardia.
- **Tiempo límite global** que decrementa frame a frame.
- **Físicas con peso**: cada acción ocupa varios ticks antes de aplicar
  el desplazamiento; las caídas duelen y matan a partir de 4 celdas.
- **Animación rotoscópica** reinterpretada con interpolación de poses
  geométricas y duraciones de acción cuidadas.
- **Atmósfera de mazmorra**: paleta nocturna, oro polvoriento, violetas.

### Modernizado

- **Python 3.13+** con `pyproject.toml`, gestión con `uv`,
  `src/` layout.
- **Arquitectura hexagonal** con capas `domain / application /
  infrastructure / presentation`. Dominio puro y testeable sin SDL.
- **Tipos estrictos**: `mypy --strict` pasa en toda `src/`.
- **Calidad**: `ruff` + `ruff format` limpios, cobertura ≥90 % en
  dominio.
- **RNG determinista** inyectado (LFSR-8). Toda partida es reproducible
  con `--seed N`.
- **Modo demo determinista** con `--demo --seed N`: una IA simple lleva
  al príncipe hasta la salida sin intervención humana.
- **Render procedural** con pygame-ce: cero sprites bitmap, todo se
  dibuja con primitivas. Cero blobs binarios en el repositorio.
- **Audio sintetizado** estilo PC-speaker generado con numpy.
- **Overlay CRT** con scanlines (firma visual).
- **Persistencia XDG** (JSON validado con Pydantic).
- **Formato de niveles** `.poplv` texto plano, editable con `vim`.

### Añadido

- **12 niveles** de campaña con nombres y subtítulos:
  `01_cell`, `02_sword`, `03_guard`, `04_traps`, `05_plate`,
  `06_loose`, `07_duo`, `08_climb`, `09_maze`, `10_patrol`,
  `11_spikes`, `12_jaffar`. Diseños propios en formato `.poplv`.
- **Campaña encadenada** con reloj global de 60 minutos conservado
  entre niveles (homenaje al original).
- **Pantalla de título** con logo, subtítulo y parpadeo del prompt.
- **Cartas de nivel** intermedias con número, título narrativo y
  subtítulo.
- **Pantallas finales** de victoria y derrota con opción de reintento.
- **Tile sable `S`**: se recoge al pisarlo y habilita el combate.
- **Salto direccional**: ``JUMP`` mientras corres/andas hace `JUMP_R`
  (salto largo para cruzar huecos).
- **Trepar repisas**: ``UP`` ante una cornisa válida hace `CLIMB_UP`.
- **Demo determinista** mejorada: gestiona combate y reconocimiento de
  trampas. Gana 11/12 niveles sin intervención humana.
- CLI con Typer: `--demo`, `--seed`, `--frames`, `--start-level`,
  `--skip-title`, `--headless`, `--no-crt`, `--mute`, `--version`.
- Launcher `persia.py` para Windows/macOS/Linux sin `uv`.
- Tests unitarios, de integración y de propiedad (hypothesis).
- CI GitHub Actions con matriz Python 3.13 y 3.14.
- 5 ADRs documentando decisiones clave.

### Licencias creativas tomadas

- **[LICENCIA CREATIVA] Granularidad de celda en vez de píxel**: el
  movimiento avanza una celda por acción completada. Preserva la
  sensación de peso pero simplifica la física para v1.0. Ver
  `docs/original_program_analysis.md` §3.
- **[LICENCIA CREATIVA] Reloj global pausable**: en el original el
  cronómetro corría incluso en el menú. Aquí se pausa al abrir pausa.
- **[LICENCIA CREATIVA] Estética vector-retro**: en lugar de imitar los
  sprites rotoscopiados con bitmaps, dibujamos siluetas geométricas con
  scanlines CRT. Ver `docs/adr/0005-visual-language.md`.
- **[LICENCIA CREATIVA] 12 niveles propios**: los diseños de los
  niveles son nuestros, en formato `.poplv` ASCII; no reproducen los
  layouts concretos del original. La progresión de dificultad y los
  nombres narrativos son originales.

### Bugs corregidos respecto del original

- **Reloj corría en pausa** → el menú pausa el cronómetro.
- **Salto-en-el-borde permitía doble salto** → exigimos al menos 2
  píxeles (1 celda) de superficie bajo los pies para saltar.
- **Espadazo fantasma tras muerte de guardia** → al morir un guardia se
  purga el flag pendiente.

[1.0.0]: https://github.com/davidvivo-ia/Prince-of-Persia-python/releases/tag/v1.0.0
