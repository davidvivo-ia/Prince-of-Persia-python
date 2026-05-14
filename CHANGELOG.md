# Changelog

Todas las novedades reseñables. Formato basado en [Keep a Changelog]; el
versionado sigue [SemVer].

[Keep a Changelog]: https://keepachangelog.com/es/1.1.0/
[SemVer]: https://semver.org/lang/es/

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
