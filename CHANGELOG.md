# Changelog

Todas las novedades reseñables. Formato basado en [Keep a Changelog]; el
versionado sigue [SemVer].

[Keep a Changelog]: https://keepachangelog.com/es/1.1.0/
[SemVer]: https://semver.org/lang/es/

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
