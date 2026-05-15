# `docs/audit.md` — FASE 0: Auditoría de fuentes canónicas

> **Estatus**: FASE 0 cerrada. Permite avanzar a FASE 1 (diagnóstico de
> regresiones) y FASE 2 (diseño por subsistemas).
>
> Esta auditoría se hace con propósito de **referencia / clean-room**:
> documentamos la mecánica canónica para reimplementarla en código
> propio, no para copiar texto fuente de SDLPoP (GPL-3) ni del 6502 de
> Mechner (licencia personal).

## Tabla de contenidos

1. [Resumen ejecutivo](#1-resumen-ejecutivo)
2. [Fuentes consultadas y método](#2-fuentes-consultadas-y-método)
3. [Mechner Apple II — repo `jmechner/Prince-of-Persia-Apple-II`](#3-mechner-apple-ii)
4. [SDLPoP — repo `NagyD/SDLPoP`](#4-sdlpop)
   1. [Constantes canónicas extraídas](#41-constantes-canónicas-extraídas)
   2. [Tipos enumerados (`types.h`)](#42-tipos-enumerados-typesh)
   3. [Tabla de secuencias (`seqtbl.c`)](#43-tabla-de-secuencias-seqtblc)
   4. [Mecánicas especiales: shadow, skeleton, princesa](#44-mecánicas-especiales)
   5. [Detección de grab a cornisa (`seg004.c`)](#45-detección-de-grab-a-cornisa)
   6. [Modelo de física tile-based](#46-modelo-de-física-tile-based)
   7. [Formato de `levels.dat`](#47-formato-de-levelsdat)
5. [VictorBusque — repo C++/OpenGL](#5-victorbusque)
6. [Gap analysis vs código actual `pop2026`](#6-gap-analysis-vs-código-actual-pop2026)
7. [Decisiones de scope y plan FASE 1](#7-decisiones-de-scope-y-plan-fase-1)

---

## 1. Resumen ejecutivo

**Prince of Persia 1989** (Mechner / Broderbund) es un cinematic
platformer 2D **tile-based** (no píxel-libre): el príncipe se mueve por
celdas discretas siguiendo cadenas de frames (rotoscopiadas) que
definen cuántos tiles avanza cada acción y en qué frame se aplica el
desplazamiento. Las salas son rejillas fijas de **10 columnas × 3
filas** de tile-size **14×63 px** (relación aspecto vertical
característica). Cada nivel se compone de varias salas enlazadas
N/S/E/W (hasta 24 por nivel).

Mecánicas pilar:
- **Tile physics + frame chains**: ninguna trayectoria balística; cada
  acción del prince (run, jump, climb, hang, strike) avanza el char
  por una secuencia con `dx`/`dy` por frame.
- **Cornisa**: `check_grab` engancha al prince si cae lento (`fall_y <
  32`) y existe una repisa enfrente; clave para el platforming.
- **Combate**: HP por nivel (`tbl_guard_hp`), stamina del guard,
  parries, ataque desbloqueable.
- **Shadow man**: doble del prince que aparece en cuatro niveles con
  guion específico (mirror, robo, salto, fusión final).
- **Esqueleto inmortal**: en una sala concreta del nivel 3.
- **Tiempo límite**: 60 minutos in-game para rescatar a la princesa.

El código actual `pop2026` se construyó sobre un modelo de física
continua (Celeste-style) y diseños de nivel propios — diverge
sustancialmente del canon en arquitectura, física y contenido.

---

## 2. Fuentes consultadas y método

| Fuente | Tipo | Uso en este audit |
|---|---|---|
| `github.com/NagyD/SDLPoP` (GPL-3) | Port C moderno | Constantes canónicas, frame tables, mecánicas |
| `github.com/jmechner/Prince-of-Persia-Apple-II` | 6502 original | Cross-check de constantes y nomenclatura |
| `github.com/VictorBusque/prince-of-persia-1989` | C++ tributo | Marca de qué NO funciona como referencia |
| `princed.org` forum/docs | Comunidad | Pendiente — formato `.dat` |

**Método**: fetch de raw files (`raw.githubusercontent.com`) y
extracción de constantes literales. No se copia código; se documenta
comportamiento.

---

## 3. Mechner Apple II

Repo `jmechner/Prince-of-Persia-Apple-II` contiene el código fuente
**6502 assembly** del original (1985-89, Broderbund). Estructura:

- `01 POP Source/` — código del juego.
- `02 POP Disk Routines/` — I/O de disco.
- `03 Disk Protection/` — protección anti-copia.
- `04 Support/` — utilidades y documentación.

Composición del lenguaje: 83.8% Assembly. Mechner declara en el README
que **no recuerda detalles** y remite a su documento técnico de
octubre 1989 en `jordanmechner.com/library`.

Los `.S` clave (no he podido fetchear el contenido raw — los nombres
exactos requieren navegar el directorio o clonar el repo):

| Archivo (típico POP1 Apple II) | Subsistema |
|---|---|
| `MASTER.S` | Game loop / dispatcher |
| `PRINCE.S` | Lógica del prince |
| `MOVER.S` | Avance de frames (movimiento sub-tile) |
| `FRAMEADV.S` | Frame advance machine |
| `SEQDATA.S` | **Tabla de secuencias** (canónica) |
| `FRAMEDEF.S` | Definición de cada frame (sprite ID + offsets) |
| `COLLISIO.S` | Colisión / tile checking |
| `GAMEEQ.S` | Constantes del juego (HP, time, etc.) |

**No copiable directamente** — el repo no tiene licencia open. Uso:
clean-room reference. SDLPoP a su vez deriva del **port DOS**, no del
Apple II original; las cadenas de frames coinciden pero los IDs
internos pueden diferir.

---

## 4. SDLPoP

Repo principal: `NagyD/SDLPoP` (GPL-3). Código en C, ~50k LoC. Es la
**referencia ejecutiva** moderna: build limpio, replays comparables,
mods soportados. Los archivos `.c` que importan para el audit:

| Archivo | Contenido relevante |
|---|---|
| `src/types.h` | enums (tiles, chars, actions, frames, seqids), structs |
| `src/data.h` | extern de variables del runtime (HP, tiempo, speeds) |
| `src/seqtbl.c` | **Tabla de secuencias** (frame chains por acción) |
| `src/data.c` | Tablas internas (offsets, defaults) |
| `src/seg002.c` | Lógica especial: shadow, skeleton triggers |
| `src/seg004.c` | Handlers de acciones del kid |
| `src/seg005.c` | Step transitions del kid |
| `src/seg006.c` | Frame advance, gravity, hang grab |
| `src/seg009.c` | Render, audio, file I/O |
| `src/options.c` | Defaults configurables |

### 4.1 Constantes canónicas extraídas

Verificadas directamente en `src/types.h` y `src/data.h`:

```c
// Geometría del mundo
#define TILE_SIZEX 14            // px ancho del tile
#define TILE_SIZEY 63            // px alto del tile (ratio 1:4.5, no cuadrado)
#define SCREEN_TILECOUNTX 10     // 10 columnas por sala
#define SCREEN_TILECOUNTY 3      // 3 filas por sala
#define ROOMCOUNT 24             // 24 salas máximo por nivel
#define BASE_FPS 60

// Física
#define FALLING_SPEED_MAX 33
#define FALLING_SPEED_ACCEL 3
#define FALLING_SPEED_MAX_FEATHER 4
#define FALLING_SPEED_ACCEL_FEATHER 1
#define FEATHER_FALL_LENGTH 18.75 // duración pocion plumas

// HP & combat
start_hitp = 3                    // HP inicial del kid
max_hitp_allowed = 10             // HP máximo
tbl_guard_hp = {4, 3, 3, 3, 3, 4, 5, 4, 4, 5, 5, 5, 4, 6, 0, 0}
                                  // HP del guard por nivel (1-15)
NUM_GUARD_SKILLS = 12             // skill 0..11

// Tiempo
start_minutes_left = 60           // 60 minutos para rescatar princesa
start_ticks_left = 719            // ticks fraccionarios primer minuto

// Trampas y velocidades
loose_floor_delay = 11            // frames antes de que ceda
base_speed = 5
fight_speed = 6
chomper_speed = 15

// Memoria
TROBS_MAX = 30                    // trampas/objetos activos máx
NUM_TIMERS = 3
```

**Implicación crítica**: el tile **NO es cuadrado**. Es 14×63 (relación
1:4.5). En el render, una sala es **140×189 px**. El prince ocupa ~1
tile horizontal × ~2 tiles vertical aproximadamente.

### 4.2 Tipos enumerados (`types.h`)

**Tiles** (`enum tiles`, 31 valores):

| ID | Nombre | Notas |
|---|---|---|
| 0 | `empty` | aire |
| 1 | `floor` | suelo sólido |
| 2 | `spike` | pinchos (con timing) |
| 3 | `pillar` | columna decorativa |
| 4 | `gate` | reja vertical |
| 5 | `stuck` | bloqueado |
| 6 | `closer` | botón que cierra puertas |
| 7 | `doortop_with_floor` | tapiz con suelo |
| 8 | `bigpillar_bottom` | columna grande inferior |
| 9 | `bigpillar_top` | columna grande superior |
| 10 | `potion` | poción (subtipo en modifier) |
| 11 | `loose` | suelo suelto |
| 12 | `doortop` | tapiz top |
| 13 | `mirror` | **espejo (nivel 4)** |
| 14 | `debris` | suelo roto |
| 15 | `opener` | botón que abre |
| 16 | `level_door_left` | exit izq |
| 17 | `level_door_right` | exit dcha |
| 18 | `chomper` | mandíbula vertical |
| 19 | `torch` | antorcha |
| 20 | `wall` | muro vertical sin pisable |
| 21 | `skeleton` | **esqueleto (nivel 3)** |
| 22 | `sword` | espada recogible |
| 23 | `balcony_left` | balcón izq |
| 24 | `balcony_right` | balcón dcho |
| 25-29 | `lattice_*` | rejas decorativas |
| 30 | `torch_with_debris` | antorcha sobre debris |

**Personajes** (`enum charids`):

| ID | Nombre | Notas |
|---|---|---|
| 0 | `kid` | prince |
| 1 | `shadow` | doble oscuro |
| 2 | `guard` | guardia genérico |
| 3 | — | reservado |
| 4 | `skeleton` | esqueleto inmortal |
| 5 | `princess` | princesa |
| 6 | `vizier` | Jaffar |
| 0x18 | `mouse` | ratón (cinemática) |

**Acciones del prince** (`enum actions`):

| ID | Nombre |
|---|---|
| 0 | `stand` |
| 1 | `run_jump` |
| 2 | `hang_climb` |
| 3 | `in_midair` |
| 4 | `in_freefall` |
| 5 | `bumped` |
| 6 | `hang_straight` |
| 7 | `turn` |
| 99 | `hurt` |

### 4.3 Tabla de secuencias (`seqtbl.c`)

90+ secuencias. Cada secuencia es una cadena `act(frame)` + opcionales
`dx(n)`, `dy(n)`, `snd(...)`, `set_fall(...)`, `jmp(label)`. Base
address `0x196E` (offset DOS original). Catalogadas:

**Locomoción**:
- `running`, `startrun`, `runcyc1..N` — ciclo de carrera
- `stand`, `standup` — quieto / tras agacharse
- `turn`, `turnrun`, `runturn` — giros (instantáneo y al correr)
- `step1..step14` — **paso de N tiles** (14 longitudes de stride)
  catalogadas para alinear sub-tile precisión

**Saltos**:
- `standjump` — salto vertical desde quieto
- `runjump` — salto con carrerilla (cubre 2-3 tiles)
- `highjump`, `superhijump` — saltos altos
- `jumpfall`, `rjumpfall`, `fallhang` — transiciones a caída

**Escalada (`HANG / CLIMB`)**:
- `jumphangMed`, `jumphangLong` — agarre tras salto
- `hang`, `hangstraight` — colgado de cornisa
- `climbup` — trepar (`seq_10_climb_up`)
- `climbdown`, `climbfail`, `hangdrop` — descender / fallar agarre
- `climbstairs` — última escalera del ending

**Caídas**:
- `softland`, `medland`, `hardland` — aterrizajes con 0/1/2 daños
- `hardland_dead` — muerte por caída
- `stepfall`, `freefall`, `freefall_loop` — caída sin agarre

**Combate**:
- `engarde`, `ready`, `strike`, `faststrike` — postura y ataque
- `advance`, `fastadvance`, `retreat` — micro-pasos en duelo
- `blockedstrike`, `readyblock`, `blocking`, `blocktostrike` — parry
- `draw_sword` (`seq_55_draw_sword`), `sheathe`

**Muerte**:
- `stabkill` — apuñalado en combate
- `dropdead` — muerte simple
- `impale` — empalado en pinchos
- `halve` — cortado por chomper
- `crush` — aplastado por suelo
- `deadfall` — muerte por caída

**Estados especiales**:
- `seq_22_crushed`, `seq_51_spiked`, `seq_52_loose_floor_fell_on_kid`
- `seq_54_chomped`, `seq_71_dying`, `seq_78_drink`, `seq_85_stabbed_to_death`
- `seq_29..42` — `safe_step` (14 variantes para aproximarse a un
  borde con la precisión correcta)

**Personajes secundarios**:
- Vizier: `Vstand`, `Vraise`, `Vwalk`, `Vstop`, `Vexit`
- Princesa: `Pstand`, `Palert`, `Pstepback`, `Plie`, `Pembrace`,
  `Prise`, `Pcrouch`, `Pslump`
- Mouse: `Mscurry`, `Mstop`, `Mraise`, `Mleave`, `Mclimb`

**Total**: 94 puntos de entrada (`seq_*`). **Estos son los building
blocks del motor — cualquier port fiel los reimplementa todos.**

### 4.4 Mecánicas especiales

Extraído de `src/seg002.c` (lógica del shadow y skeleton):

**Esqueleto** — NIVEL 3 (no nivel 8 como dice el brief del usuario):
- Sala 1, columnas trigger configurables (`skeleton_trigger_column_1/2`).
- Se activa cuando el kid pisa una columna concreta.
- El tile `tiles_21_skeleton` está en el layout pero el char solo se
  instancia al disparo.
- Es **inmortal**: con HP=0 vuelve a HP=1 con animación HURT.

**Shadow man** — cuatro apariciones canónicas (los números de nivel
del brief del usuario están **desplazados**):

| Nivel canónico | Sala | Evento |
|---|---|---|
| **4** (`mirror_room` = 4) | 4 | Aparece tras saltar al espejo (`tiles_13_mirror`). Se mueve a la izquierda. |
| **5** (`shadow_steal_room` = 24) | 24 | Roba la poción cuando la puerta está abierta. |
| **6** (`shadow_step_room` = 1) | 1 | Salta cuando el kid está en `frame_43` (run-jump). |
| **12** | 15 | Fusión final: `Char.room == 15 && shadow_initialized == 0`. Si se "une" al shadow, +HP. |

> ⚠️ El brief del usuario dice "Nivel 3: mirror" / "Nivel 6: roba" /
> "Nivel 8: skeleton" / "Nivel 12: final". Los tres primeros números
> están **mal**. Lo correcto (verificado en `seg002.c`):
>   - Mirror → nivel 4
>   - Steal → nivel 5
>   - Step → nivel 6
>   - Skeleton wake → nivel **3** (no 8)
>   - Final → nivel 12

### 4.5 Detección de grab a cornisa

`check_grab()` en `seg006.c`. Condiciones:

```
- Tecla SHIFT pulsada (¡input del jugador, no automático!)
- Char.fall_y < 32 (velocidad de caída < máxima)
- Char.alive < 0 (vivo)
- Hay un ledge enfrente en la celda inmediatamente superior
```

Activa:
```c
seqtbl_offset_char(seq_15_grab_ledge_midair);
play_seq();
grab_timer = 12;
```

Transiciona a `actions_6_hang_straight` o `actions_2_hang_climb`.

> Diferencia con nuestro código `pop2026`: actualmente el grab es
> **automático** al caer cerca de una cornisa. El canon requiere
> SHIFT pulsado.

### 4.6 Modelo de física tile-based

POP1 NO usa posiciones float continuas. Cada `Char` (kid, guard,
shadow, princess) tiene:
- `curr_col`, `curr_row` — celda actual
- `x`, `y` — píxel dentro de la celda (sub-tile)
- `frame` — frame actual en la cadena
- `curr_seq` — puntero a posición en `seqtbl`

Cada tick:
- `play_seq()` lee el siguiente acto: aplica `dx`/`dy` y avanza
  `frame`. Cuando se queda sin acts, salta al siguiente `seq` por
  `jmp`.
- `load_fram_det_col()` recalcula `curr_col/curr_row` desde `x`/`y`.
- Colisión: `in_wall()` checa tiles adyacentes para validar el
  movimiento; revierte si choca.

**Gravedad** (`fall_accel` + `fall_speed` en `seg006.c`):

```c
// fall_accel
if (Char.action == actions_4_in_freefall) {
    Char.fall_y += FALLING_SPEED_ACCEL;          // +3 por tick
    if (Char.fall_y > FALLING_SPEED_MAX)         // cap a 33
        Char.fall_y = FALLING_SPEED_MAX;
}

// fall_speed
Char.y += Char.fall_y;
if (Char.action == actions_4_in_freefall) {
    Char.x = char_dx_forward(Char.fall_x);
    load_fram_det_col();
}
```

**Implicación**: no hay velocidad horizontal continua durante la
caída excepto el componente `fall_x` que se conserva del momento del
salto/empujón. La aceleración es de 3 px/tick² a 60 FPS.

### 4.7 Formato de `levels.dat`

`sizeof(level_type) == 2305` bytes según `types.h`. Componentes:

| Campo | Tamaño | Uso |
|---|---|---|
| `fg[720]` | 720 bytes | Foreground tiles (24 salas × 30 tiles) |
| `bg[720]` | 720 bytes | Modifiers / overlays |
| `doorlinks` | variable | Links entre puertas y botones |
| `roomlinks[24]` | 24*N bytes | N/S/E/W de cada sala |
| `guards_tile[24]` | 24 | Pos del guard por sala |
| `guards_dir[24]` | 24 | Dirección inicial |
| `guards_x[24]` | 24 | Sub-tile X |
| `guards_skill[24]` | 24 | Skill 0..11 |
| `guards_color[24]` | 24 | Variante visual |

Cada tile = 1 byte con `5 bits piece + 3 bits modifier`. Total niveles
en `levels.dat`: **14** (1-12 + level 0 demo + level 13/14 cinemáticas
finales).

> No he podido recuperar el doc oficial `dat-files.txt` (404 en raw
> path). Para FASE 1 quizá necesitemos clonar el repo o extraerlo con
> `gh api`.

---

## 5. VictorBusque

Repo `VictorBusque/prince-of-persia-1989`:
- **Lenguaje C++ con OpenGL** — *no es Python* como decía el brief.
- README **vacío** (0 bytes).
- 6 stars, 6 forks, 0 issues abiertas.
- Sin documentación de mecánicas, niveles, ni status.

**Conclusión**: no es una fuente útil como referencia técnica.
Probable proyecto educativo abandonado o pre-release. Lo registramos
y descartamos para FASE 1.

---

## 6. Gap analysis vs código actual `pop2026`

Comparativa cara a cara entre nuestro motor actual y la referencia
canónica. Cada fila marcada ⚠️ es un gap que FASE 1 / FASE 2 deben
documentar y planificar.

### 6.1 Arquitectura del motor

| Aspecto | Canon POP1 / SDLPoP | `pop2026` actual | Estado |
|---|---|---|---|
| Tile size | 14×63 px | 48×64 px | ⚠️ ratio incorrecto |
| Room size | 10×3 tiles | 20×6 tiles | ⚠️ doble densidad |
| Max rooms/nivel | 24 | irrelevante (single grid) | ⚠️ no hay grafo de salas |
| Camera | Room-flick (salto en bloque) | Room-flick (ya implementado) | ✓ |
| Físicas | Tile-based + frame chains | **Continua float (Celeste)** | ⚠️ pivot grande |
| Frame rate lógico | 60 FPS | 60 FPS | ✓ |
| Estado del char | `frame + curr_seq + sub-tile` | `Action + ticks_in_action + body.pos.{x,y}` | ⚠️ modelo distinto |

### 6.2 Constantes

| Constante | Canon | `pop2026` |
|---|---|---|
| HP inicial kid | 3 | 3 ✓ |
| HP guard nivel 1 | 4 | 2-3 (random) ⚠️ |
| HP guard nivel 8 (jaffar bro) | 4 | 2 ⚠️ |
| HP guard nivel 12 (vizier) | 5 | 4 ⚠️ |
| Time límit | 60 min | DEFAULT_TIME_LIMIT_TICKS = 216000 (60min × 60s × 60tick) ✓ |
| Loose floor delay | 11 frames | 12 ticks ✓ |
| Falling accel | 3 px/tick² | 0.06 cells/tick² (continuous) ⚠️ unidades distintas |
| Falling max | 33 px/tick | 0.45 cells/tick ⚠️ |

### 6.3 Frame system

| Aspecto | Canon | `pop2026` |
|---|---|---|
| Frames del prince | ~180 (rotoscopiados) | 0 (dibujo procedural) ⚠️ |
| Secuencias | 94 nombres (`seqtbl`) | 18 acciones (`Action` enum) ⚠️ |
| `dx`/`dy` por frame | Sí — clave del platforming | No, derivado de física continua ⚠️ |
| `safe_step` | 14 variantes (step1..step14) | No existe ⚠️ |

### 6.4 Niveles

| Aspecto | Canon (POP1 original) | `pop2026` |
|---|---|---|
| Layouts | 14 niveles (1-12 + final) | 15 hand-crafted **diseñados por nosotros** |
| Formato | `levels.dat` binario | `.poplv` ASCII (incompatible) |
| Multi-room por nivel | Hasta 24 salas con links | 1 grid grande (20×6 a 60×6) |
| Trampas | chomper, slicer, freezing-block, pillar-up | spike + loose + gate (3 tipos) ⚠️ faltan chomper/slicer |
| Potions | 5 tipos | 3 tipos (heal, poison, maxHP) ⚠️ faltan time, float |

### 6.5 Mecánicas

| Mecánica | Canon | `pop2026` |
|---|---|---|
| Sword pickup | Nivel 1, recogible | Implementado ✓ |
| Hang/climb | Manual con SHIFT | **Automático** ⚠️ |
| Shadow man | 4 apariciones scripted | Solo mirror guard custom en L13 ⚠️ |
| Skeleton inmortal | Nivel 3 sala 1 | En L14 (mi diseño) ⚠️ |
| Chomper | Sí — instakill | No ⚠️ |
| Slicer | Sí — instakill | No ⚠️ |
| Time potion | Sí (+30s) | No ⚠️ |
| Float potion | Sí (cae lento 18.75s) | No ⚠️ |
| Mouse cinematic | Sala con ratón antes del final | No ⚠️ |
| Princess + Jaffar ending | Cinemática completa | No ⚠️ |

### 6.6 IA

| Comportamiento | Canon | `pop2026` |
|---|---|---|
| Guard skills 0-11 | Tabla de probabilidades de parry/strike por skill | Hardcoded 50/50 ⚠️ |
| Guard cruza salas | No por defecto, configurable | No tiene salas ⚠️ |
| Shadow imita prince | Solo en sala mirror, mov scripted | Mirror guard mio invierte LEFT/RIGHT ⚠️ no canónico |
| Vizier (Jaffar) | Char especial con guion | No existe ⚠️ |

---

## 7. Decisiones de scope y plan FASE 1

El gap es enorme. Tres caminos posibles:

### Camino A — Paridad real con POP1 (lo que pide el brief)
- Pivot del motor: continuo → tile-based.
- Reimplementar 94 secuencias con `dx`/`dy` por frame.
- Cargar `levels.dat` real.
- Implementar chomper, slicer, time potion, float potion.
- Shadow man scripted en 4 niveles.
- Cinemáticas princesa/jaffar.
- **Estimado**: 4-8 semanas full-time. **No es trabajo de una sesión.**

### Camino B — Asunción honesta del gap, FASE 1 documenta lo más roto
- Mantener arquitectura continuous physics.
- Listar en `docs/regressions.md` cada desviación con prioridad y
  esfuerzo.
- Priorizar las 5-10 cosas que más acercan el feel sin reescribir
  motor: HP del guard por nivel, chomper como tile, manual grab con
  SHIFT, shadow encounter en un nivel específico, time potion.
- **Estimado**: 1-2 semanas iteradas.

### Camino C — Subset doble track
- Mantener `pop2026` como "tribute" jugable (lo actual).
- Empezar `pop2026-canon` como subproyecto separado siguiendo el plan
  A en paralelo.

**Recomendación**: Camino B. El motor actual tiene 325 tests verdes,
HANG/CLIMB funcional, 15 niveles diseñados, gráficos pulidos y
estética definida. Tirarlo y empezar de cero costaría meses para
acabar en algo menos terminado. Mejor: documentar el gap, cerrar las
desviaciones más visibles, y mantener el proyecto como tribute serio.

**Si el usuario prefiere Camino A**, FASE 1 debería empezar
descartando los módulos `physics.py`, `physics_prince.py`, todos los
`.poplv` actuales y `level.py` (formato propio) para sustituirlos
por equivalentes tile-based + cargador `levels.dat`. Es un proyecto
distinto.

---

**FASE 0 cerrada.** Pendiente decisión del usuario sobre Camino A/B/C
antes de entrar en FASE 1.
