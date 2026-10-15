# Análisis arqueológico — Prince of Persia (1989)

> Fuente: repositorio histórico
> https://github.com/jmechner/Prince-of-Persia-Apple-II y diarios de
> desarrollo publicados por Jordan Mechner.
> Este documento no copia código original. Documenta su **estructura
> funcional** para guiar la reimplementación en Python 2026.

## 1. Encuadre

| Campo            | Valor                                                          |
|------------------|----------------------------------------------------------------|
| Título           | Prince of Persia                                               |
| Autor            | Jordan Mechner (Brøderbund Software)                           |
| Año              | 1989                                                           |
| Plataforma       | Apple II / IIe / IIc (versión madre)                           |
| Lenguaje         | Ensamblador 6502                                               |
| Tamaño           | ~75 KB de código + dos disquetes 5.25" de datos                |
| Resolución       | 280x192 (modo HGR doble), 6 colores                            |
| Sonido           | PC Speaker monocanal (beeper)                                  |
| Input            | Teclado (no joystick obligatorio)                              |
| Género           | Plataformas cinemáticas / acción-aventura                      |

### Sinopsis funcional

El jugador encarna a un príncipe sin nombre encerrado en las mazmorras del
sultán de Persia. Jafar, el visir, ha dado a la princesa una hora para
desposarse con él o morir. El jugador debe escalar **12 niveles** (mazmorras,
prisión, salones del palacio, torres, calabozos) en **60 minutos reales**,
sorteando trampas, derrotando guardias con sable y, finalmente, derrotando a
Jafar.

### Lectura crítica desde 2026

- **Innovaciones**:
  - Rotoscopía animada (Mechner filmó a su hermano corriendo y la calcó
    fotograma a fotograma). Es la razón por la que el príncipe se mueve
    "como una persona".
  - Físicas inerciales: el príncipe acelera, frena, resbala. Romper la
    relación 1:1 entre tecla y movimiento fue revolucionario.
  - Combate de esgrima por turnos rápidos (parry / attack / advance /
    retreat) en vez de hack-and-slash.
  - Tiempo límite global, no por nivel. Cambia la sensación.

- **Fricciones para el jugador moderno**:
  - Sin checkpoints: cada muerte reinicia el nivel.
  - Controles inerciales hostiles en saltos al vacío.
  - Sin tutorial; aprender se paga con vidas.
  - Pantalla por pantalla (no scroll suave): cada habitación es un screen
    discreto. Hoy sería inaceptable.

- **Decisiones forzadas por la época**:
  - 64K de RAM ⇒ niveles pequeños cargados desde disquete.
  - Sin coma flotante ⇒ físicas en enteros con escala fina.
  - Sprites de 2 colores ⇒ paleta simbólica antes que realista.

---

## 2. Arqueología — flujo, datos, algoritmos

### 2.1 Grafo de flujo (alto nivel)

```
                ┌──────────────┐
                │  TITLE SCREEN│
                └──────┬───────┘
                       │ (any key)
                ┌──────▼───────┐         (death)
                │  LOAD LEVEL  │◀────────────────────┐
                └──────┬───────┘                     │
                       │                             │
                ┌──────▼───────┐                     │
        ┌──────▶│  GAME LOOP   │─────► UPDATE PRINCE │
        │       │  (60 Hz vbl) │       UPDATE GUARDS │
        │       └──────┬───────┘       UPDATE LEVEL  │
        │              │               UPDATE TIMER  │
        │       ┌──────▼───────┐       RENDER FRAME  │
        │       │ CHECK STATE  │                     │
        │       └──┬─────┬──┬──┘                     │
        │          │     │  │                        │
        │  (alive) │ (die)│  │ (exit reached)        │
        └──────────┘     │   └──► NEXT LEVEL ────────┘
                         └────► GAME OVER ──► TITLE
```

### 2.2 Inventario de variables (reconstruido)

> En 6502 las "variables" son zeropage o direcciones fijas. Reconstruyo las
> que sabemos por los diarios de Mechner y por nombres aparecidos en
> `MASTER.S` y similares. Marcadores [DATO] vs [INFERENCIA].

| Nombre lógico    | Descripción                                        | Confianza      |
|------------------|----------------------------------------------------|----------------|
| `prince_x`       | Posición horizontal (px·escala)                    | [DATO]         |
| `prince_y`       | Posición vertical (row·8)                          | [DATO]         |
| `prince_vx`      | Velocidad horizontal                               | [INFERENCIA]   |
| `prince_action`  | Enum de acción: stand, run, jump, climb, fall…     | [DATO]         |
| `prince_frame`   | Índice del fotograma de animación                  | [DATO]         |
| `prince_hp`      | Puntos de vida (3–10)                              | [DATO]         |
| `prince_facing`  | Dirección: -1 izquierda, +1 derecha                | [DATO]         |
| `current_level`  | 1..14 (12 jugables + 2 secretos)                   | [DATO]         |
| `room_id`        | Habitación actual dentro del nivel (1..24)         | [DATO]         |
| `tile_grid[r,c]` | Mapa de tiles 10x3 por habitación                  | [DATO]         |
| `time_left`      | Cuenta atrás global en ticks                       | [DATO]         |
| `guards[i]`      | Estructura por guardia: x, y, hp, action, skill    | [DATO]         |
| `rng_seed`       | LFSR de 8 bits                                     | [INFERENCIA]   |

### 2.3 Inventario de subrutinas (reconstruido)

| Subrutina            | Función                                                 |
|----------------------|---------------------------------------------------------|
| `INIT`               | Limpia memoria, monta primer nivel                      |
| `LOAD_LEVEL`         | Lee del disquete los 24 cuartos del nivel               |
| `MAIN_LOOP`          | Sincroniza con vblank, llama updates y render           |
| `UPDATE_PRINCE`      | Lee input, aplica físicas, transiciona estado           |
| `UPDATE_GUARDS`      | IA por estado (patrolling, alert, fighting)             |
| `UPDATE_TILES`       | Suelos que caen, placas de presión, puertas             |
| `COLLISIONS`         | Detecta tile-vs-actor por celda y por borde de píxel    |
| `COMBAT`             | Tabla de transiciones (attack/parry/block/strike/back)  |
| `DRAW_ROOM`          | Dibuja tiles del cuarto activo                          |
| `DRAW_ACTORS`        | Pinta sprites de príncipe y guardias                    |
| `SOUND_BEEP`         | Toggle de speaker para FX (pasos, choque sable…)        |
| `SAVE_GAME`          | Persistencia en disquete (sólo dos niveles, slot único) |

### 2.4 IO y dispositivos

- **Input**: lectura directa de KEYBOARD ($C000) con strobe a $C010.
- **Vídeo**: doble buffer HGR (páginas $2000 y $4000), conmutadas para
  evitar tearing.
- **Sonido**: bit de $C030 alternado en bucles cronometrados para
  sintetizar frecuencias.
- **Disco**: comandos directos a la controladora Disk II vía `RWTS`.

### 2.5 Algoritmos identificados

1. **Estado-acción del príncipe**: máquina de estados finitos con ~15
   estados (`stand`, `run`, `jump_up`, `jump_run`, `climb_up`,
   `climb_down`, `hang`, `fall`, `crouch`, `strike`, `parry`, `block`,
   `advance`, `retreat`, `dead`). Cada estado tiene un *vector de
   animación* (lista de frames + offsets aplicados al "punto de pies"
   del príncipe).
2. **Físicas a paso de píxel**: posición avanza en sub-píxeles; al cruzar
   el centro de un tile se evalúa colisión.
3. **Combate**: tabla de probabilidad por nivel de habilidad del
   guardia. El parry interrumpe el attack si llega en el frame correcto.
4. **Trampas**:
   - *Spike floor*: pincha si la velocidad vertical es alta o si el pie
     cae sobre celda activa (las pinchos retraen 5 segundos tras
     pisada).
   - *Loose floor*: cae 1 tile abajo, hace ruido y rompe al impactar.
   - *Gate*: cerrada salvo si una placa de presión está activa.
5. **Cinemáticas entre niveles**: pantallas estáticas con texto.

### 2.6 Bugs y rarezas conocidas (originales)

- **Salto-en-el-borde**: si saltas con un sólo píxel sobre suelo, el
  motor cuenta dos saltos seguidos. Speedrunners lo explotan.
- **Doble-parry**: en versiones tempranas un parry consumía dos frames
  de input pero sólo respondía al primero, dando la sensación de input
  perdido.
- **Espadazo fantasma**: si un guardia muere en el mismo frame que el
  jugador inicia un strike, el strike se conserva contra el siguiente
  enemigo.
- **Reloj congelado**: en el menú no se pausa el reloj global. Vivido
  como bug por jugadores, intencional según Mechner.

### Bugs corregidos en esta reimplementación (1.0)

- *Reloj sigue corriendo en pausa* → **arreglado**: el menú pausa el
  cronómetro global.
- *Salto-en-el-borde* → **arreglado**: el salto exige al menos 2 píxeles
  de superficie debajo de los pies.
- *Espadazo fantasma* → **arreglado**: al morir un guardia se purga el
  flag `pending_strike`.

Estas correcciones se documentan también en `CHANGELOG.md` como
[LICENCIA CREATIVA].

---

## 3. Notas sobre lo que conservamos del "alma"

- **Físicas con peso**: aceleración, fricción, salto inerte. El
  príncipe no es un sprite de Mario.
- **Combate corto y nervioso**: 4 acciones, lectura del rival, parry
  como herramienta clave.
- **Tiempo presionando**: 60 minutos globales, contador siempre visible.
- **Rotoscopía**: en TUI/pygame-ce procedural, lo imitamos con
  *interpolación de poses* y micro-pausas entre estados (ver
  [`design.md`](design.md)).
- **Muerte severa pero justa**: caídas >3 tiles matan, spikes matan,
  guardias matan; pero el feedback visual y sonoro es siempre claro.

[SUPUESTO] Hemos preferido **simplificar** la cantidad de niveles a **3
niveles totalmente jugables** en v1.0 en vez de los 12 del original.
La estructura de carga de niveles soporta más; añadirlos es trabajo de
contenido, no de motor.
