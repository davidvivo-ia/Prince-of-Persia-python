# PLAN.md — Campaña de 100 niveles

> Plan ejecutable y atómico. Cada tarea se cierra independiente, con
> DoD verificable y *quality gates* en verde antes de avanzar al
> siguiente. Nada de tareas que dependan de "cuando termine X". Si una
> depende, se marca con ⤴ y se ejecuta después.
>
> **Decisión de producto** (confirmada):
> - 12 niveles hand-crafted (los actuales) + 88 procedurales por
>   semilla determinista.
> - 4 actos de 25 niveles. Cada acto introduce un mecanismo dominante.
> - Sin reloj global. Cada nivel tiene su propio tiempo.
> - Auto-save tras cada nivel ganado, slot único, hasta el 100.

---

## Bloque 0 — Pre-trabajo (no negociable)

### T0.1 · Snapshot de estado actual
- **Hago**: `git status --short`, `pytest -q`, `ruff check`, `mypy --strict`.
- **DoD**: 175 tests verdes, sin lints, mypy limpio. Si algo falla, se
  arregla antes de tocar nada de este plan.
- **Estimado**: 3 min.

---

## Bloque A — Cimientos (sin tocar UI todavía)

### T1 · Subir cota de SaveGame a 100
- **Archivos**: `src/pop2026/infrastructure/savegame.py`,
  `tests/unit/test_infrastructure.py`.
- **Hago**: `Field(ge=1, le=99)` → `Field(ge=1, le=100)`.
- **DoD**: test nuevo `test_can_save_level_100`; tests existentes
  siguen verdes.
- **Estimado**: 5 min.

### T2 · Tiempo por nivel en `Level`
- **Archivos**: `src/pop2026/domain/level.py`.
- **Hago**: añadir campo opcional `time_limit_ticks: int | None = None`
  al dataclass `Level`. Inmutable, retro-compatible.
- **DoD**: tests `test_level_default_time_limit_is_none` y
  `test_level_with_explicit_time_limit`.
- **Estimado**: 8 min.

### T3 · `new_game` respeta el tiempo del nivel
- **Archivos**: `src/pop2026/domain/game.py`,
  `tests/unit/test_game.py`.
- **Hago**: si `level.time_limit_ticks is not None`, usar ese valor;
  si no, mantener el `time_limit` argumento (compat).
- **DoD**: test `test_new_game_uses_level_time_when_set`.
- **Estimado**: 10 min.

### T4 · Reachability BFS pura
- **Archivos**: nuevo `src/pop2026/domain/reachability.py`,
  `tests/unit/test_reachability.py`.
- **Hago**:
  - `is_reachable(level: Level) -> bool` haciendo BFS desde
    `prince_spawn` por celdas walkable + caída + salto direccional
    (≤ 2 cells).
  - Considera placas que abren gates (modelo simplificado: si hay
    placa accesible, se asume gate abierta).
- **DoD**: tests con (a) corredor recto, (b) hueco salvable con jump,
  (c) hueco insalvable, (d) gate cerrada sin placa accesible.
- **Estimado**: 30 min.

### T5 · Tablas de densidad por acto
- **Archivos**: nuevo `src/pop2026/application/difficulty.py`,
  `tests/unit/test_difficulty.py`.
- **Hago**:
  - `@dataclass(frozen=True, slots=True) DifficultyParams`:
    `gap_prob`, `spike_prob`, `loose_prob`, `guard_count`,
    `skeleton_count`, `multi_room_prob`, `boss_flag`,
    `time_limit_seconds`.
  - `params_for(act: int, local_index: int) -> DifficultyParams`.
  - Curva monótona dentro de cada acto + escalón al cambiar de acto.
- **DoD**: tests:
  - `test_params_monotonic_within_act` (no decrece dificultad
    relativa).
  - `test_act_step_up` (acto 2 ≥ acto 1 en cualquier métrica).
  - `test_boss_flag_only_at_local_index_24` (jefe al final de cada
    acto).
- **Estimado**: 25 min.

---

## Bloque B — Generador (depende de A)

### T6 · Generador procedural ⤴ (T2, T4, T5)
- **Archivos**: nuevo `src/pop2026/application/level_generator.py`,
  `tests/unit/test_level_generator.py`,
  `tests/property/test_generator_invariants.py`.
- **Hago**:
  - `GeneratorConfig(level_index: int, seed: int)`.
  - `generate(config) -> Level`:
    1. Calcula `act = (level_index - 1) // 25`,
       `local = (level_index - 1) % 25`.
    2. Pide `params_for(act, local)`.
    3. Construye grid 20×6 (acto I–II) o 40×6 (acto III–IV).
    4. Coloca spawn izda, exit dcha en filas asentables.
    5. Sprinkle obstáculos según probabilidades, RNG sembrado por
       `seed * 1000 + level_index` (LFSR existente).
    6. Coloca guardias/esqueletos lejos del spawn.
    7. **Reintenta** hasta 12 veces con micro-perturbaciones si
       `is_reachable()` falla. Si tras 12 intentos no, fallback a un
       corredor mínimo.
    8. Devuelve `Level` con `time_limit_ticks` derivado de `params`.
- **DoD**:
  - `test_same_seed_same_level` (determinismo).
  - `test_different_seeds_differ` (variedad).
  - `test_every_generated_level_is_reachable` (hypothesis con seeds
    1..200, niveles 13..100). 0 fallos.
  - `test_difficulty_monotonic_levels_13_to_100` (suma de
    obstáculos no decrece de forma significativa).
- **Estimado**: 90 min.

### T7 · Source unificado de niveles ⤴ (T6)
- **Archivos**: nuevo `src/pop2026/application/level_source.py`,
  `tests/unit/test_level_source.py`.
- **Hago**:
  - `load_level(level_index: int, *, seed: int) -> Level`.
  - Si `level_index ≤ 12`: delega a
    `infrastructure.levels.load_builtin(slug)` con el slug actual.
  - Si `level_index ≥ 13`: delega a `level_generator.generate(...)`.
- **DoD**: tests por rama, plus `test_load_level_100_works`.
- **Estimado**: 15 min.

---

## Bloque C — Campaña a 100 (depende de B)

### T8 · `CAMPAIGN` extendida ⤴ (T7)
- **Archivos**: `src/pop2026/application/campaign.py`,
  `tests/unit/test_campaign.py`.
- **Hago**:
  - Mantener los 12 `LevelInfo` actuales como Acto I (1-12) +
    placeholder narrativo para 13-25.
  - Generar 88 entradas más con título derivado: `"Mazmorra 14"`,
    `"Prisión 28"`, `"Palacio 51"`, `"Torre 76"`. Subtítulo del
    pool deterministico por acto.
  - `total_levels() == 100`.
- **DoD**: `test_campaign_has_100_entries`, `test_act_for_level`,
  `test_titles_use_act_theme`.
- **Estimado**: 20 min.

### T9 · `app.py` integra `level_source` ⤴ (T7, T8)
- **Archivos**: `src/pop2026/presentation/app.py`,
  `tests/integration/test_runner_100_levels.py`.
- **Hago**:
  - Sustituir `load_builtin(info.slug)` por
    `level_source.load_level(level_idx, seed=config.seed)`.
  - Eliminar herencia de `time_left` entre niveles (cada nivel
    arranca con su propio reloj).
- **DoD**:
  - `test_runner_starts_level_50_headless`.
  - `test_runner_completes_levels_1_to_5_demo` (smoke).
- **Estimado**: 25 min.

### T10 · CLI hasta 100 ⤴ (T8)
- **Archivos**: `src/pop2026/presentation/cli.py`.
- **Hago**: `--start-level` ya usa `total_levels()`; queda automático.
- **DoD**: `pop2026 --start-level 100 --demo --headless --frames 200`
  no rompe.
- **Estimado**: 5 min.

---

## Bloque D — Presentación (depende de C)

### T11 · HUD con acto y `N/100`
- **Archivos**: `src/pop2026/presentation/renderer.py`,
  `tests/unit/test_renderer_hud.py`.
- **Hago**:
  - Línea HUD: `ACTO II · NIVEL 28/100 · ⏱ 01:24 · ❤❤❤`.
  - Cálculo de acto vía
    `application.difficulty.act_for_level(level_index)`.
- **DoD**: test que renderiza el HUD a `pygame.Surface` y verifica
  pixels de colores conocidos en posiciones esperadas.
- **Estimado**: 20 min.

### T12 · Cinemáticas de cambio de acto
- **Archivos**: `src/pop2026/presentation/screens/cutscene.py`,
  `src/pop2026/presentation/app.py`.
- **Hago**:
  - Nuevas escenas: `act1`, `act2`, `act3`, `act4`, `final`.
  - `app.py`: dispara al entrar en `level_index` 1, 26, 51, 76 y
    tras ganar 100. Conserva el set `shown_cutscenes`.
- **DoD**:
  - Render headless de cada escena no peta.
  - `test_cutscene_dispatched_at_act_boundaries`.
- **Estimado**: 30 min.

### T13 · Música por acto
- **Archivos**: `src/pop2026/presentation/audio.py`,
  `src/pop2026/presentation/app.py`.
- **Hago**: `zone_for_level` cambia de mapa: actos 1,2,3,4 →
  dungeon/prison/palace/throne. Añadir track `prison`.
- **DoD**: `test_zone_for_level_returns_four_distinct_zones`.
- **Estimado**: 25 min.

---

## Bloque E — Validación end-to-end

### T14 · Demo bot pasa muestra
- **Archivos**: `tests/integration/test_demo_sample.py`.
- **Hago**: para `level_index ∈ {1, 13, 26, 38, 51, 63, 76, 88, 99}`,
  el demo bot termina (WON o LOST_DIED, no PLAYING) en 8 000 frames.
  Niveles narrativos de combate (3, 7, 10, 12) excepción documentada.
- **DoD**: test pasa o explícitamente skip los conocidos.
- **Estimado**: 20 min.

### T15 · Property test del generador
- **Archivos**: `tests/property/test_generator_invariants.py`.
- **Hago** (hypothesis):
  - Para `seed ∈ [0, 255]`, `level ∈ [13, 100]`: el level es
    reachable.
  - Para mismo `seed, level`, dos llamadas devuelven `Level` igual.
  - Para mismo `level`, distintos seeds producen al menos 50 % de
    layouts diferentes.
- **DoD**: hypothesis 100 ejemplos, 0 fallos.
- **Estimado**: 25 min.

### T16 · Save/load nivel 100
- **Archivos**: `tests/integration/test_save_load_100.py`.
- **Hago**: simular ganar nivel 99 → save → reload → arranca en 100.
- **DoD**: test verde.
- **Estimado**: 10 min.

---

## Bloque F — Documentación + release

### T17 · Actualizar `README`, `CHANGELOG`, `plan.md`, `docs/postmortem.md`
- **Archivos**: `README.md`, `CHANGELOG.md`, `plan.md`, `docs/postmortem.md`.
- **Hago**:
  - README: sección "100 niveles" explicando híbrido y cómo se
    juega.
  - CHANGELOG: nueva v3.0.0 con todo lo del bloque.
  - plan.md: marcar todas las tareas de este `PLAN.md` como
    completadas.
  - postmortem: párrafo nuevo sobre escala 12 → 100, decisiones de
    procedural, qué se ganó / qué se perdió.
- **DoD**: docs leen bien y reflejan el estado real.
- **Estimado**: 25 min.

### T18 · ADR-0006 generador procedural
- **Archivos**: `docs/adr/0006-procedural-levels.md`.
- **Hago**: contexto, opciones consideradas, decisión, consecuencias.
- **DoD**: archivo existe, formato consistente con otros ADRs.
- **Estimado**: 15 min.

### T19 · Verificación final + push
- **Hago**:
  ```bash
  uv run ruff format --check .
  uv run ruff check .
  uv run mypy --strict src persia.py
  uv run pytest --cov=src/pop2026/domain --cov-report=term -q
  uv run python persia.py preview 50_act2 --out /tmp/l50.png
  uv run python persia.py --demo --seed 42 --headless --frames 200 --start-level 50
  ```
  - Tag `v3.0.0`, push.
- **DoD**: gates verdes; demo headless de un nivel procedural OK;
  push aceptado por el remoto.
- **Estimado**: 15 min.

---

## Resumen y dependencias

```
T0.1 ──┐
       ├── T1, T2, T3, T4, T5  (Bloque A — independientes entre sí)
       │           │
       │           └─→ T6 ──→ T7 ──→ T8 ──→ T9 ──→ T10
       │                                     │
       │                                     ├─→ T11
       │                                     ├─→ T12
       │                                     └─→ T13
       │                                            │
       │                                            ├─→ T14
       │                                            ├─→ T15
       │                                            └─→ T16
       │                                                  │
       └─────────────────────────────────────────────────→ T17, T18 → T19
```

**Tareas paralelizables** (subagentes potenciales):
- A: T1, T2, T3, T4, T5 — todos independientes.
- D: T11, T12, T13 — todos independientes una vez T9 está cerrado.
- F: T17, T18 — independientes entre sí.

**Tiempo total estimado**: ~6 h ejecutando en serie; ~3.5 h con
paralelización inteligente de A y D.

---

## Criterios de "hecho" para v3.0

- [ ] Las 19 tareas con DoD verificada.
- [ ] `pytest --cov=src/pop2026/domain` ≥ 90 %.
- [ ] `uv run python persia.py --demo --seed 42 --headless` puede
      arrancar en cualquier nivel 1..100 y reportar status.
- [ ] Save/load funcional hasta nivel 100.
- [ ] CHANGELOG, README, postmortem, plan.md alineados.
- [ ] ADR-0006 publicado.
- [ ] Tag `v3.0.0`, branch `claude/prince-of-persia-rebuild-y7uxD`
      sincronizada con `origin`.

---

## Riesgos identificados (para tu repaso)

| Riesgo | Mitigación |
|---|---|
| Generador produce niveles imposibles | T4 (BFS) + reintentos en T6, fallback a corredor |
| Niveles procedurales aburridos | T5 con curvas pensadas + T15 garantiza variedad |
| 100 niveles agotan al jugador | Acto = pausa narrativa con cinemática (T12) y música distinta (T13) |
| Save/load schema cambia | T1 sólo bumpea `le=100`, no rompe slots existentes |
| HUD se queda pequeño con `ACTO X · NIVEL N/100` | T11 con tabular numerals y abreviación si hace falta |
| Tests de hypothesis lentos | Limitar a 100 ejemplos; pytest marker `slow` para los E2E |

---

*Pendiente de tu revisión. Modifica, recorta, reordena. No empiezo
hasta tu OK explícito.*
