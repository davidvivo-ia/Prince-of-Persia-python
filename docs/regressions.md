# `docs/regressions.md` — FASE 1: Diagnóstico del código actual vs canon POP1

> **Estatus**: FASE 1 cerrada. Documenta el gap del motor `pop2026`
> actual frente al canon Prince of Persia (1989) según lo extraído en
> `docs/audit.md`.
>
> **Camino elegido**: A — paridad real. El motor actual se descarta
> como base; este documento sirve como **checklist de lo que el motor
> nuevo debe contener** y como inventario de lo que **NO se conserva**
> de la versión `pop2026` previa.

## Tabla de contenidos

1. [Regresiones globales (arquitectura y motor)](#1-regresiones-globales)
2. [Regresiones por nivel (1-12 + final)](#2-regresiones-por-nivel)
3. [Regresiones de mecánicas transversales](#3-regresiones-de-mecánicas-transversales)
4. [Priorización](#4-priorización)
5. [Lo que se conserva](#5-lo-que-se-conserva)

---

## 1. Regresiones globales

Cada fila lista una desviación verificada en `audit.md`. Severidad:
- **P0** = el juego no es POP sin esto
- **P1** = se nota a primer vistazo
- **P2** = aceptable como deuda técnica si el resto está

| ID | Subsistema | Canon | `pop2026` actual | Severidad |
|---|---|---|---|---|
| G1 | Tile size | 14×63 px (no cuadrado) | 48×64 px (casi cuadrado) | P0 |
| G2 | Room size | 10×3 tiles fijo | 20×6 tiles variable | P0 |
| G3 | Físicas | Tile-based + frame chains con `dx`/`dy` por frame | Continua float (Celeste-style) | P0 |
| G4 | Frames del prince | ~180 rotoscopiados, encadenados por `seqtbl` | 0 (dibujo procedural) | P0 |
| G5 | Frame chains (seqtbl) | 94 secuencias nombradas | 18 `Action` enum sin chain | P0 |
| G6 | Multi-room por nivel | Grafo de hasta 24 salas con `roomlinks[N/S/E/W]` | 1 grid grande, room-flick sólo en cámara | P0 |
| G7 | Formato de nivel | `levels.dat` binario, 2305 bytes/nivel | `.poplv` ASCII propio | P0 |
| G8 | Niveles canónicos | 14 originales | 15 diseñados ad-hoc | P0 |
| G9 | Loop lógico | 12 FPS (lógico) + interpolación a 60 (visual) | 60 FPS sin distinción | P1 |
| G10 | Save format | Save slot estilo POP1 con HP/level/time | Pydantic v2 custom JSON | P2 |

---

## 2. Regresiones por nivel

Para cada nivel se lista lo que el canon contiene y lo que tenemos.
Las descripciones canónicas se basan en:
- `types.h` (`tbl_guard_hp`)
- `seg002.c` (eventos especiales por nivel)
- Conocimiento general del juego (walkthroughs públicos)

> **Nota**: el dump tile-a-tile de cada sala vendrá en FASE 2 cuando
> tengamos el cargador de `levels.dat`. Por ahora se documenta el
> tema, mecánicas y exit conditions.

### Nivel 1 — **The Dungeon** (HP guard: 4)

**Canon**:
- Despertar en la celda (sala con prince tumbado).
- Encontrar **espada** en una sala más adelante (`tiles_22_sword`).
- Primera **loose floor** y caída al sótano (introduce la mecánica).
- Primer **guard** con HP=4.
- **Pressure plate + gate** para el exit.
- Tile `level_door_left/right` (`16`/`17`) marca la salida.

**`pop2026` actual** (`01_cell.poplv`):
```
..@..............................>......
```
Pasillo vacío de 40 cols con `@` (spawn) y `>` (exit).

**Regresión**:
- ❌ Sin loose floor introductoria
- ❌ Sin caída al sótano (no hay multi-room vertical)
- ❌ Sin sword pickup
- ❌ Sin primer guard
- ❌ Sin pressure plate
- ❌ Sin exit door real (sólo marker)

**Severidad**: P0. El nivel 1 actual no enseña ninguna mecánica.

### Nivel 2 — **The Guards** (HP guard: 3)

**Canon**:
- Multi-room compleja (~6-8 salas).
- Múltiples **loose floors** que cierran rutas.
- Primer **chomper** (`tiles_18_chomper`) — mandíbula vertical que instakill.
- Primer combate real (guard HP=3).
- Gates con plates encadenadas.

**`pop2026`** (`02_sword.poplv`):
```
..@..S...........................>......
```
Pasillo con sword pickup.

**Regresión**:
- ❌ Una sola sala
- ❌ Sin chomper (chomper como tile no existe en `pop2026`)
- ❌ Sin guard en este nivel
- ❌ Sin loose floors

**Severidad**: P0.

### Nivel 3 — **The Skeleton** (HP guard: 3)

**Canon**:
- ⚡ **Esqueleto** se despierta en sala 1 cuando el kid pisa una columna
  trigger (`skeleton_trigger_column_1/2` en `seg002.c`).
- Skeleton es **inmortal** (HP=0 → HP=1, animación HURT).
- Layout multi-room con puentes de loose floors.

**`pop2026`** (`03_guard.poplv`):
```
..@.S............g...............>......
```
Pasillo con sword + guard normal.

**Regresión**:
- ❌ Esqueleto en nivel equivocado (yo lo puse en `14_throne`)
- ❌ Sin trigger por columna
- ❌ Sin layout multi-room

**Severidad**: P0.

### Nivel 4 — **The Mirror** (HP guard: 3)

**Canon**:
- En una sala concreta hay un **espejo** (`tiles_13_mirror`).
- Al saltar a través del espejo emerge el **shadow man** (`charid_1_shadow`).
- El shadow corre hacia la izquierda y desaparece.
- Marca el inicio del arco narrativo del doble.

**`pop2026`** (`04_traps.poplv`):
```
..@.+....^.^.........^.^.^.+.....>......
```
Pasillo con pinchos y poción.

**Regresión**:
- ❌ Sin mirror tile (`tiles_13_mirror` no implementado)
- ❌ Sin shadow man
- ❌ Sin trigger de salto a través
- ⚠️ Pinchos presentes pero como tile mortal directo, no como trampa con timing

**Severidad**: P0. Nivel 4 sin espejo no es nivel 4.

### Nivel 5 — **The Thief** (HP guard: 3)

**Canon**:
- Sala 24: el shadow **roba la poción** del kid en su narices.
- Layout complejo con muchas gates.
- Primer **chomper** intensivo.

**`pop2026`** (`05_plate.poplv`):
```
..@..._...|.........._....|......>......
```
Pasillo con 2 placas + 2 gates.

**Regresión**:
- ❌ Sin shadow steal
- ❌ Sin chomper
- ⚠️ Placas y gates funcionales pero linealmente, no encadenadas

**Severidad**: P0.

### Nivel 6 — **The Steps** (HP guard: 4)

**Canon**:
- Multi-room complejo con pisos cortos.
- ⚡ El **shadow salta** entre salas cuando el kid está en frame_43 (mid-runjump).
- Trampas combinadas: spikes + loose + chompers.
- Salto largo crítico sobre abismo.

**`pop2026`** (`06_loose.poplv`):
```
..@..+...........................>......
####=#=##=#=##=#==#=##=#=##=#==#########
```
Loose floors abajo.

**Regresión**:
- ❌ Sin shadow appearance
- ❌ Loose floors actúan como caída instantánea visible (delay añadido pero sin animación de "crujido" previo)
- ❌ Sin chompers

**Severidad**: P0.

### Nivel 7 — **The Mountains** (HP guard: 5)

**Canon**:
- Layout vertical extremo (10+ salas apiladas).
- Sección abierta con caída al vacío (death).
- HP guard ya 5 — combate más duro.
- Aparece el **lattice** (rejas decorativas que no son sólidas).

**`pop2026`** (`07_duo.poplv`):
```
..@.S....g......+...........g.....>.....
```
Dos guards en pasillo plano.

**Regresión**:
- ❌ Sin verticalidad (es un pasillo horizontal)
- ❌ Sin lattices
- ❌ HP guard erróneo (canon 5, nuestro 3)

**Severidad**: P0.

### Nivel 8 — **The Caverns** (HP guard: 4)

**Canon**:
- Cavernas con paredes irregulares.
- Múltiples loose floors críticos.
- Combate medio-alto.

**`pop2026`** (`08_climb.poplv`): nivel vertical 12 rows con ledges en zigzag (mi diseño).

**Regresión**:
- ⚠️ Vertical sí, pero diseño propio no canon
- ❌ HP guard erróneo (canon 4, nuestro 2)

**Severidad**: P0.

### Nivel 9 — **The Tomb** (HP guard: 5)

**Canon**:
- **Esqueletos múltiples** (varios `tiles_21_skeleton`).
- Layout maze.
- Trampas combinadas.

**`pop2026`** (`09_maze.poplv`):
```
.@.._.|..+.._.|.....+_..|.._.|.+..>.....
```
Plates + gates intercalados.

**Regresión**:
- ❌ Sin esqueletos múltiples
- ⚠️ Es un maze 1D, no 2D
- ❌ HP guard erróneo (canon 5, nuestro 3)

**Severidad**: P0.

### Nivel 10 — **The Tower** (HP guard: 5)

**Canon**:
- Torre vertical larga con guards en cada piso.
- Caída desde lo alto = muerte instantánea.
- Saltos precisos entre cornisas.

**`pop2026`** (`10_patrol.poplv`):
```
.@.S.....g........g........g.....>......
```
Tres guards en pasillo plano.

**Regresión**:
- ❌ Sin verticalidad
- ❌ HP guard erróneo (canon 5, nuestro 3)

**Severidad**: P0.

### Nivel 11 — **The Tower 2** (HP guard: 5)

**Canon**:
- Continúa el ascenso.
- Posiblemente combate con **mirror image guard** que copia movimientos.
- Layout complejo con balcones (`tiles_23/24_balcony_*`).

**`pop2026`** (`11_spikes.poplv`):
```
..@.....^...........^..........>.......
```
Pinchos en línea.

**Regresión**:
- ❌ Sin mirror guard canónico (mi mirror está en L13)
- ❌ Sin balcones

**Severidad**: P0.

### Nivel 12 — **The Jaffar Confrontation** (HP guard: 5)

**Canon**:
- ⚡ Sala 15: **fusión con el shadow** (`shadow_initialized == 0`). Si te
  fusionas con tu shadow, +HP.
- **Vizier (Jaffar)** como char especial (`charid_6_vizier`), HP=6
  según `tbl_guard_hp[13] = 6`.
- Es el combate final pre-ending.

**`pop2026`** (`12_jaffar.poplv`):
```
.@.S.g..............M.................>.
```
Pasillo con boss `G` skill 2.

**Regresión**:
- ❌ Sin shadow fusion event
- ❌ Vizier es un boss genérico, no char especial
- ⚠️ HP correcto por casualidad

**Severidad**: P0.

### Nivel 13 — **Final Run** / Nivel 14 — **Ending**

**Canon**:
- Nivel 13: carrera contra Jaffar tras vencerlo (cinemática + control
  limitado).
- Nivel 14: **ending** con la princesa (`charid_5_princess`) y el ratón
  (`charid_24_mouse`). Cinemática del Sultan/Jaffar.

**`pop2026`**:
- `13_shadow.poplv` — mi mirror guard (no canon level 13).
- `14_throne.poplv`, `15_escape.poplv` — diseños propios sin equivalente.

**Regresión**:
- ❌ Toda la cinemática final inexistente
- ❌ Princess, mouse, vizier_special inexistentes
- ❌ Mis niveles 13-15 son ad-hoc

**Severidad**: P0.

---

## 3. Regresiones de mecánicas transversales

| ID | Mecánica | Canon | `pop2026` | Severidad |
|---|---|---|---|---|
| M1 | **Hang grab** | Manual (SHIFT) + `fall_y < 32` | Automático al caer | P1 |
| M2 | **Chomper** | Tile 18, instakill con timing | No existe | P0 |
| M3 | **Slicer** | Tile vertical instakill | No existe | P0 |
| M4 | **Float potion** | 18.75s caída lenta | No existe | P1 |
| M5 | **Time potion** | +30s tiempo | No existe | P1 |
| M6 | **Sword pickup** | Sólo en nivel 1, sale del tile floor | Auto al matar guard | P1 |
| M7 | **Strike damage** | `take_hp(1)` por golpe no bloqueado | Mismo (3 hits = muerte) | ✓ |
| M8 | **Guard skill 0-11** | Tabla de prob. parry/strike por skill | Hardcoded 50/50 | P1 |
| M9 | **Time limit** | 60min in-game → princesa muere | Implementado pero sin "princess dies" cinematic | P2 |
| M10 | **Mouse cinematic** | Aparece antes del ending para abrir gate | No existe | P2 |
| M11 | **Vizier as char** | charid_6 con guion propio | No existe | P0 |
| M12 | **Princess as char** | charid_5 con animaciones (Pstand, Palert, ...) | No existe | P0 |
| M13 | **Audio jingles** | Victory, death, drink, etc. | Beeper con varios SFX ✓ | mostly ✓ |
| M14 | **Save format** | Slot con HP/lvl/time bytes | Pydantic JSON | P2 |

---

## 4. Priorización

Orden recomendado para implementación en FASE 3 (asumiendo motor
nuevo en FASE 2):

### Bloque 1 — Cimientos (sin esto nada funciona)
1. **G3**: Físicas tile-based + frame advance
2. **G4**: Sistema de frames (carga de tabla seqtbl)
3. **G1, G2**: Geometría correcta de tile y room
4. **G6**: Grafo de salas con roomlinks
5. **G7**: Parser `levels.dat`

### Bloque 2 — Jugabilidad real
6. **M2 chomper**, **M3 slicer**: tiles letales con timing
7. **M1 hang grab manual**: SHIFT
8. **M8 guard skill**: tabla por nivel
9. **G8 niveles canónicos**: cargar los 14 originales

### Bloque 3 — Narrativa y polish
10. **M11 vizier, M12 princess**: chars especiales con seq propias
11. **L3, L4, L5, L6**: eventos shadow/skeleton scripted
12. **M4 float**, **M5 time**: pociones extra
13. **L12 final**: shadow fusion + ending
14. **M10 mouse**: cinemática final

### Bloque 4 — Calidad
15. **G9**: separar lógica (12 FPS) y render (60 FPS)
16. **G10**: save format compatible
17. Tests por subsistema

---

## 5. Lo que se conserva del `pop2026` actual

Aunque el motor de física y los niveles se tiran, **estos componentes
se rescatan** para el motor nuevo (con adaptaciones):

| Componente | Adaptación necesaria |
|---|---|
| `presentation/audio.py` (Beeper) | Mantener; añadir jingles `victory`/`drink`/`princess`/`mouse` |
| `presentation/theme.py` palette | Mantener; los hex siguen siendo apropiados |
| `presentation/renderer.py` primitives | Reescribir top-level pero conservar `_draw_back_wall`, `_draw_floor`, etc. como tiles individuales |
| `presentation/screens/*` (title, card, ending) | Mantener — son menus genéricos |
| `infrastructure/rng.py` (LFSR) | Mantener |
| `infrastructure/savegame.py` | Reformatear para slot binario |
| Tests de game-feel (coyote, jump buffer) | Tirar — no aplican a tile-based |
| Tests de level reachability (BFS) | Mantener pero adaptar al nuevo formato |
| CLI/app.py | Mantener; adaptar al nuevo modelo de campaña |

---

## 6. Conclusión FASE 1

Confirmado: el motor actual y los niveles actuales se descartan. Los
componentes de presentación, audio, RNG y CLI se rescatan. **FASE 2
diseña los subsistemas nuevos**.

**Trabajo restante estimado** (engineer-weeks):
- FASE 2 (design docs): 3-5 días
- FASE 3 cimientos: 2 semanas
- FASE 3 jugabilidad real: 2 semanas
- FASE 3 narrativa: 1-2 semanas
- Pulido + tests + cross-platform: 1 semana
- **Total: ~6-8 semanas full-time**

Coincide con la estimación inicial del audit.
