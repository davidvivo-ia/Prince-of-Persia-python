# PLAN — De pop2026 v1.0 a v2.0

> Hoja de ruta para acercar la reimplementación al "feel" del Prince of
> Persia original (Mechner, 1989), sin reproducir su código ni sus
> datos. El plan parte de una auditoría del repo actual y se ordena por
> impacto en la jugabilidad.

Fecha de redacción: 2026-05-13. Última versión publicada: **v1.0.0**
(rama `claude/prince-of-persia-rebuild-y7uxD`).

> **Progreso v1.1 (en curso)**:
> - ✅ **F-2** (Hang / drop) entregado: el príncipe se cuelga del borde al
>   correr fuera de una repisa; `UP` lo sube de nuevo, `DOWN` lo suelta.
> - ✅ **F-1 fase 0** (cimientos): `PositionF`, `Velocity`, `AABB`,
>   módulo `physics` con integrador y `is_grounded`. Tests con
>   invariantes de gravedad y colisión. Aún sin integrar en el FSM
>   del príncipe; pendiente fase 1.
> - ✅ **F-3** (Multi-pantalla con cámara *room-flick*) entregado:
>   `viewport_col()` calcula la habitación visible y el renderer dibuja
>   solo esa banda. HUD muestra `SALA n/N`. L10 rediseñado a 40 celdas
>   (dos habitaciones).
> - ✅ Demo bot reacciona a HANG y a saltos largos (`JUMP_R` desde
>   `RUN/WALK` interrumpe el paso para "saltar antes de caer").
> - ✅ Audio: nuevo SFX `grab` cuando agarra una cornisa.
> - L9 rediseñado con hueco de una celda que obliga a `JUMP_R`.
> - Demo bot gana 11 de 12 niveles; solo L12 queda como reto humano.
> - 141 tests, **91 % cobertura en dominio**, todas las gates verdes.

---

## 1. Auditoría del estado actual

### 1.1 Inventario de código (2 791 líneas)

| Capa            | Módulos | LOC | Tests | Cobertura |
|-----------------|---------|-----|-------|-----------|
| `domain/`       | 12      | 1 207 | 7 | **91 %** |
| `application/`  | 5       | 281   | 1 | 71 % |
| `infrastructure/` | 4     | ~120  | 1 | 100 % |
| `presentation/` | 9       | 1 296 | 1 | (no medido) |

Calidad: `ruff format`, `ruff check`, `mypy --strict` limpios.
113 tests pasan en 1.3 s.

### 1.2 Mecánicas implementadas (vs. el original)

| Mecánica                          | v1.0 | Original | Estado |
|-----------------------------------|------|----------|--------|
| Movimiento horizontal             | ✅ | ✅ | celda discreta + interpolación sub-celda al pintar |
| Salto vertical y direccional      | ✅ | ✅ | dos celdas con arco |
| Caída con daño                    | ✅ | ✅ | letal a 4 celdas |
| Trepar repisa (climb-up)          | ✅ | ✅ | una celda |
| Combate cuerpo a cuerpo           | ⚠️ | ✅ | binario: strike vs parry, sin avance/retroceso |
| Spikes                             | ✅ | ✅ | matan al caer encima |
| Suelo suelto                       | ✅ | ✅ | cae al pisar |
| Placas + rejas                     | ✅ | ✅ | abren la reja más cercana |
| Pociones (curativa / veneno)       | ✅ | ✅ | falta la *max-HP up* |
| Pickup del sable                   | ✅ | ✅ | tile `S` |
| Reloj global 60 min                | ✅ | ✅ | conservado entre niveles |
| **Colgarse del borde** (hang)     | ❌ | ✅ | falta |
| **Descolgar y caer voluntario**   | ❌ | ✅ | falta |
| **Niveles multi-pantalla**        | ❌ | ✅ | cada nivel = 1 pantalla |
| **Esqueleto inmortal**            | ❌ | ✅ | falta |
| **Nivel-espejo (clon)**           | ❌ | ✅ | falta |
| **Cinemáticas entre actos**       | ❌ | ✅ | solo carta de nivel estática |
| **Guillotinas y rejas que matan** | ❌ | ✅ | falta el "chopper" |
| **Combate con distancia**         | ❌ | ✅ | falta avance / retroceso |
| **Animación rotoscopiada**        | ⚠️ | ✅ | 3 poses interpoladas |
| **Audio melódico cinemático**     | ❌ | ✅ | solo SFX cortos |
| **Guardado / carga de partida**   | ⚠️ | ✅ | módulo existe, no integrado |

Resumen: **62 % de cobertura funcional**. La sensación de plataformas
rotoscópicas y el ritmo cinemático son lo que más se nota que falta.

### 1.3 Decisiones de diseño que conviene preservar

- **Hexagonal**: `domain/` 100 % puro sin pygame ni filesystem. Los
  cambios futuros se prueban con `pytest` en milisegundos.
- **Dataclasses `frozen=True, slots=True`** para todas las entidades.
- **RNG inyectado** (LFSR-8). Cualquier `--seed` reproduce el run.
- **Formato `.poplv` ASCII**. Editable con `vim`, diff legible.
- **Domain events implícitos** vía diff de frames en `audio.play_transitions`.

---

## 2. Gap analysis y prioridad

Cada item se valora con tres ejes: **impacto en feel**, **coste técnico**
y **riesgo de regresión** (0–5).

| ID  | Mejora                          | Impacto | Coste | Riesgo | Tier |
|-----|---------------------------------|---------|-------|--------|------|
| F-1 | Física continua (x, y float)    | 5       | 4     | 4      | S |
| F-2 | Hang / drop desde repisa        | 5       | 3     | 2      | S |
| F-3 | Multi-pantalla por nivel        | 4       | 3     | 2      | S |
| F-4 | Combate con distancia           | 4       | 3     | 3      | A |
| F-5 | Animación con keyframes propios | 4       | 4     | 2      | A |
| F-6 | Save/load integrado en runner   | 3       | 1     | 1      | A |
| F-7 | Enemigos nuevos (esqueleto)     | 3       | 2     | 2      | A |
| F-8 | Cinemáticas (3 cards animadas)  | 3       | 2     | 1      | B |
| F-9 | Pociones de max-HP              | 2       | 1     | 1      | B |
| F-10| Música ambient sintetizada      | 3       | 3     | 1      | B |
| F-11| Modo difícil + speedrun timer   | 2       | 1     | 1      | C |
| F-12| Editor de niveles TUI           | 3       | 4     | 1      | C |

Reglas:
- **Tier S** son los tres que cambian la sensación de "esto no es POP" a
  "esto es POP". Se acometen primero.
- **Tier A** son los que aportan profundidad al combate y la
  arquitectura.
- **Tier B** son los acabados que el jugador percibe pero que el motor
  ya soporta a poco que se extienda.
- **Tier C** son chips de valor añadido, prescindibles para v2.0.

---

## 3. Roadmap detallado

### 3.1 Tier S — Base del "feel" (v1.1)

#### F-1 · Física continua

**Objetivo**: posición y velocidad en coma flotante; ticks lógicos a 60
Hz integrando como `pos += vel * dt`, `vel += accel * dt`.

**Cambios**:

- `domain/geometry.py`: añadir `PositionF(x: float, y: float)` y
  `Velocity(vx: float, vy: float)` (frozen). Conservar `Position`
  discreta como **derivada** (`@property` que castea a int).
- `domain/prince.py`: `Prince.pos` pasa a ser `PositionF`. Las acciones
  se siguen modelando como FSM, pero cada acción describe una curva
  paramétrica `(x(t), y(t))` que el integrador aplica cada tick.
- `domain/physics.py` (nuevo): integrador, colisión AABB contra grid de
  tiles, detección de borde para `hang`.
- Renderer ya está listo (lee offset sub-celda); pasará a leer
  directamente `pos.x * tile_w`.

**Pruebas**: `tests/property/test_physics_invariants.py` — un príncipe
soltado en aire siempre acaba en un tile sólido o muerto; nunca cruza
una pared sólida; la suma de daño por caída es monótona.

**Estimación**: 2 sesiones (10–14 h). Riesgo de regresión alto, por eso
va con feature-flag `PHYSICS_V2=1` que activa la nueva ruta y mantiene
la antigua durante un release.

#### F-2 · Hang / drop

**Objetivo**: el príncipe, al caer en el borde de una repisa, queda
colgado por las manos. `UP` sube, `DOWN` se suelta.

**Cambios**:

- Añadir `Action.HANG_STRAIGHT` (colgado quieto) y `Action.HANG_DROP`
  (soltarse).
- `prince._next_action`: al caer, si el borde adelante a `(r-1, c+1)`
  estaba sólido y `(r, c+1)` no, transición a `HANG_STRAIGHT` en vez
  de `FALL`.
- Renderer: pose nueva `hang` (brazos arriba, cuerpo colgando).
- Niveles: añadir hueco entre plantas en L8, L9, L12.

**Pruebas**: caída en borde lateral → estado `HANG`; pulsar UP → sube;
pulsar DOWN → cae sin daño extra; sin tecla → cae tras 2 s.

**Estimación**: 1 sesión (4–6 h).

#### F-3 · Multi-pantalla por nivel

**Objetivo**: un "nivel" pasa de ser una pantalla 20×6 a ser una
cuadrícula de habitaciones (típicamente 3×3 → 60×18 celdas) con
desplazamiento cuando el príncipe cruza el borde.

**Cambios**:

- `Level.grid` ya es una matriz; admite cualquier tamaño. El parser ya
  soporta líneas arbitrarias.
- Formato `.poplv` extendido: cabecera opcional `# rooms_x: 3` para
  documentar la organización por habitaciones (puramente decorativa).
- `presentation/renderer.py`: cámara que sigue al príncipe. La cámara
  enfoca la habitación actual; al cruzar el borde, transición de 200 ms
  pintando *fade-cut* o desplazamiento brusco a la habitación adyacente
  (estilo *room flick* del original).
- Niveles: rediseñar L8–L12 con al menos 2 habitaciones cada uno.

**Pruebas**: integración — un demo determinista cruza dos habitaciones
y llega al exit.

**Estimación**: 2 sesiones (8–10 h).

### 3.2 Tier A — Profundidad y polish (v1.2)

#### F-4 · Combate con distancia y ritmo

**Objetivo**: dejar de tener combate binario; añadir tempo y lectura
del rival.

**Cambios**:

- Añadir `Action.ADVANCE`, `Action.RETREAT`, `Action.BLOCK`,
  `Action.LUNGE`.
- `domain/combat.py`: máquina de transiciones con ventanas activas.
  Cada `STRIKE` tiene 3 fases (wind-up, hit, recovery); solo conecta
  durante la fase `hit` si el defensor no está en `BLOCK` o `PARRY`.
- IA del guardia (`guard.py`): elige acción según distancia, salud
  propia y "agresividad" inyectada como parámetro.
- Renderer: poses adicionales para cada nueva acción.

**Pruebas**: hypothesis — partidas guardia-vs-guardia simétricas
deberían acabar con probabilidad cercana al 50 %; un guardia con skill
2 gana ≥70 % contra skill 1 en 100 simulaciones.

**Estimación**: 2 sesiones (10–12 h).

#### F-5 · Animación con keyframes propios

**Objetivo**: cuerpo articulado (cabeza, torso, brazos, piernas, sable)
con keyframes definidos en código, interpolados con curvas de Bézier.

**Cambios**:

- `domain/skeleton.py` (nuevo, puro): definición del esqueleto y
  estructura de keyframe.
- `domain/poses.py` (nuevo): poses por acción como secuencias de
  keyframes con timing. **Diseño original**, sin referencia al
  rotoscope de Mechner.
- `presentation/renderer.py`: dibuja cada hueso como segmento
  primitivo.

**Pruebas**: hypothesis — interpolación de poses en `t ∈ [0, 1]`
nunca produce segmentos de longitud negativa ni ángulos > 360°.

**Estimación**: 2 sesiones (10 h).

#### F-6 · Save/load integrado

**Objetivo**: pulsar `S` durante el juego graba la partida; al iniciar,
si existe un guardado, se ofrece "Continuar".

**Cambios**:

- `infrastructure/savegame.py` ya existe. Wire en `presentation/app.py`
  y nueva opción en el título.
- Modelar el `SaveSlot` con campos suficientes para restaurar nivel,
  HP, max_HP, time_left, rng_seed, has_sword.

**Estimación**: 0.5 sesión (2–3 h).

#### F-7 · Esqueleto inmortal

**Objetivo**: enemigo que no puede morir; al "vencerlo" se cae al suelo
y vuelve a levantarse tras 5 s. Solo se le puede evitar.

**Cambios**:

- `domain/guard.py`: subclase / variante `Skeleton` con HP infinito y
  pierde un golpe → `HURT` → vuelve a `STAND` tras delay.
- Nuevo tile spawn: `K` (de *kraneo*).
- L11 o L12: añadir un esqueleto en un pasillo angosto.

**Estimación**: 0.5 sesión (3 h).

### 3.3 Tier B — Acabados (v1.3)

#### F-8 · Cinemáticas con texto y dibujo simple

Tres viñetas animadas:
- Intro: princesa atada, Jafar amenazante, prince encerrado.
- Mid: prince entra al palacio.
- Final: encuentro con Jafar.

Implementación: `presentation/screens/cutscene.py` con paneles de
texto + dibujo procedural (silueta de princesa, columna, antorcha). La
duración total de los tres no supera 30 s.

**Estimación**: 1 sesión (5 h).

#### F-9 · Poción de max-HP

Nuevo tile `M` (de *magia*). Aumenta `max_hp` y cura. Una por nivel a
partir del 4.

**Estimación**: 0.25 sesión (1 h).

#### F-10 · Música ambient sintetizada

`numpy` + `pygame.mixer` para producir 3 loops de ~30 s en distintas
escalas (calabozo, palacio, torre). El motor reproduce el loop
correspondiente según el `level_index`.

**Estimación**: 1 sesión (4–6 h).

### 3.4 Tier C — Bonus

- **F-11 · Modo difícil**: HP inicial = 2, daño doble.
- **F-12 · Editor TUI**: `pop2026-edit` con Textual; previewa el
  `.poplv` y sirve para que la comunidad cree niveles.

---

## 4. Calendario y release plan

| Hito  | Contenido             | Tiempo | Trigger semver |
|-------|-----------------------|--------|----------------|
| v1.1.0 | F-1, F-2, F-3        | ~30 h  | minor (cambios visibles pero compatibles) |
| v1.2.0 | F-4, F-5, F-6, F-7   | ~30 h  | minor |
| v1.3.0 | F-8, F-9, F-10       | ~12 h  | minor |
| v2.0.0 | rebranding + docs    | ~5 h   | major (rotura de `.poplv` por extensiones) |
| v2.x   | F-11, F-12           | ~10 h  | minor por ítem |

Después de cada hito:

1. `uv run ruff format --check . && uv run ruff check .`
2. `uv run mypy --strict src persia.py`
3. `uv run pytest --cov=src --cov-report=term-missing`
4. `uv run pop2026 --demo --seed 42 --headless` (al menos primeros 8
   niveles WON).
5. Captura PNG headless de las pantallas clave para el changelog.
6. Tag `vX.Y.Z` + push.

---

## 5. Reglas para no romper lo que funciona

- **Compatibilidad de `.poplv`**: cualquier nuevo tile lleva carácter
  no usado y se documenta en `docs/level_format.md`. La parser ignora
  caracteres no reconocidos solo en modo `--lax`; por defecto sigue
  reventando para detectar typos.
- **Determinismo**: cualquier rama nueva del motor recibe `Rng` como
  argumento. Cero `random.random()` global.
- **Capas**: nada en `domain/` importa `pygame` ni `pathlib.Path`. Si un
  feature lo necesita (p. ej. save/load), va en `infrastructure/` y se
  expone como `Protocol`.
- **Tests primero** para todo lo del Tier S y F-4: el cambio toca
  física y combate, donde un bug es invisible hasta que sangra.
- **Feature flags** vía variable de entorno (`POP2026_PHYSICS_V2=1`)
  durante el desarrollo de F-1, para poder volver a la rama vieja sin
  revertir commits.

---

## 6. Riesgos identificados

| Riesgo                                          | Mitigación |
|-------------------------------------------------|------------|
| F-1 introduce bugs sutiles en colisiones        | flag + tests de hypothesis con seed |
| Animación con keyframes consume CPU             | profile con `py-spy`, simplificar curvas si <60 fps |
| Multi-pantalla rompe el demo bot existente      | reescribir `demo_player.decide` con A* sobre las habitaciones |
| `pygame.mixer` no disponible en algunos entornos | ya está cubierto: `_try_init_mixer` no falla, audio degrada a silente |
| Crecimiento de `presentation/renderer.py` (>1000 LOC) | trocear en `renderer/tiles.py`, `renderer/actors.py`, `renderer/hud.py` |

---

## 7. Definición de "hecho" para v2.0

El proyecto se declara v2.0 cuando:

- [ ] Tier S y A completos, todos los tests verdes.
- [ ] El demo bot completa los 12 niveles con seed 42.
- [ ] Cobertura `domain/` ≥ 92 %.
- [ ] README explica la nueva física y muestra GIFs animados de
      hang, run-jump, climb, combat.
- [ ] Cinemáticas presentes (al menos 2 de las 3).
- [ ] Save/load funcional con un slot persistente.
- [ ] CHANGELOG con sección "Modernizado 2026" diferenciando lo
      heredado del original y lo añadido conscientemente.
- [ ] Postmortem actualizado.

---

## 8. Convención de commits para esta fase

```
feat(physics): add continuous (x,y) coordinates and integrator
feat(hang): implement ledge hanging with up/down controls
feat(rooms): multi-screen level layout with camera follow
feat(combat): four-action sword duel with timing windows
fix(prince): climb landing when ceiling is solid
docs(plan): update with progress on F-1
refactor(renderer): split into tiles/actors/hud modules
test(physics): property tests for collision invariants
```

Y todos los commits siguen pasando los 5 gates de calidad antes de
hacer `push`.

---

## 9. Lo que NO está en este plan (intencionalmente)

- **Reproducir** el código original de Jordan Mechner. El repo
  histórico está disponible bajo su propia licencia y este proyecto
  jamás lo redistribuye. Las mecánicas se diseñan desde cero usando
  conocimiento público de cómo funciona el juego.
- **Importar** assets gráficos o sonoros del original.
- **Imitar** layout-por-layout los niveles del original. Los nuestros
  son diseños propios "en el estilo de".
- **Acoplarnos** a `pygame-ce` en `domain/` o `application/`. Si en el
  futuro queremos un puerto web (pyodide, transcrypt), el dominio ha de
  quedar libre.

---

*Documento vivo. Actualizar al cerrar cada hito.*
