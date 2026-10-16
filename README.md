# Prince of Persia · Python 2026 (`pop2026canon`)

> Reimplementación en **Python 3.13 / pygame-ce** del Prince of Persia
> de 1989: las reglas del original (física, trampas, enemigos y
> secuencias sacadas de SDLPoP) con la presentación, la jugabilidad y
> los extras de un juego de 2026. Todo procedural: ni código ni arte
> ni datos de Ubisoft.

```bash
uv sync && uv run pop2026canon          # juega
python persia.py                         # sin uv (Windows / cualquier sistema)
uv run pop2026canon --levels-dat RUTA    # con los niveles de tu copia original
```

## El juego, tal como está

### La historia
Persia, hace mucho tiempo. Con el sultán en la guerra, el visir Jaffar
se adueña del palacio y le da a la princesa una hora para elegir:
casarse con él o morir. Al joven que ella ama lo arrojan a las
mazmorras. Tienes sesenta minutos de reloj real, que no se detienen
al morir, para subir trece niveles hasta la torre, acabar con Jaffar y
llegar a los aposentos de la princesa. La introducción (palacio bajo la
luna, Jaffar y el reloj de arena, la mazmorra) y el reencuentro final
son cinemáticas procedurales que se saltan con Enter.

### Los verbos
| Acción | Teclado | Mando |
|---|---|---|
| Correr | ← → / A D | Cruceta / stick |
| Saltar · trepar | ↑ / W | A |
| Salto largo parado | ↑ + dirección | A + dirección |
| Agacharse · descolgarse | ↓ / S | B |
| Agarrarse · paso corto | Shift | RB / RT |
| Atacar | Espacio / J | X |
| Parar (en guardia) | ↑ | A |
| Rebobinar (moderno) | R (mantener) | LB / LT |
| Pausa · mapa | Esc · M | Start · Back |
| Reloj | Tab | — |

Las pistas contextuales enseñan cada verbo la primera vez que hace
falta (cornisa, borde, losa suelta, placa, duelo) y nunca más.

### Dos modos de juego
- **Moderno**: rebobinar el tiempo (las Arenas) y reaparecer en la
  entrada de la sala al morir. Morir cuesta reloj, no vidas.
- **Clásico 1989**: morir reinicia el nivel; el reloj sigue corriendo.

Dificultad **normal** o **difícil** (guardias dos puntos más diestros,
45 minutos de reloj).

### Lo que te encuentras
- **Trampas**: pinchos (a paso corto se pasan; corriendo o cayendo
  matan), cuchillas con ciclo fijo, losas sueltas que caen a los pocos
  instantes de pisarlas (y que al caer sobre una placa la dejan
  accionada para siempre), rejas que abren con placa y se cierran solas
  a los 18 segundos, placas de cierre, pozos de uno, dos y tres pisos.
- **Pociones**: vida (roja), vida máxima (la grande), veneno (verde),
  pluma (caída suave), tiempo (+30 s) y frascos vacíos.
- **Enemigos**: guardias con habilidad de 0 a 11 y vestuario por nivel,
  esqueletos que no mueren (hay que perderlos), tu sombra (L4, L5, L6,
  L12), el visir Jaffar (L12) y un ratón aliado (L8).
- **Duelo**: desenvainar (↑ + Shift), en guardia (Shift), estocada
  (Espacio), parada (↑ justo cuando el rival ataca) y réplica.

### Progreso, medallas y fantasma
- Progreso persistente: niveles desbloqueados, mejor tiempo y menos
  muertes por nivel; selección de nivel desde el menú.
- Medallas por nivel: **Completado**, **Sin un rasguño** (sin morir ni
  rebobinar), **Veloz** (bajo el tiempo de referencia) y **Explorador**
  (todas las salas).
- **Fantasma del récord**: tu mejor carrera limpia de cada nivel corre
  a tu lado como un kid translúcido; la tarjeta del nivel muestra el
  récord y el resumen, la diferencia.
- Resumen de campaña al ganar: tiempo total, muertes y medallas.

### Presentación
- Lienzo HD 1280x852; personajes animados con un esqueleto 2D (una pose
  por frame del original, vestuario por personaje y guardias vestidos
  según el nivel); tiles con volumen; pared de piedra generada por sala.
- **Luz**: la pared tiene relieve y cada sillar recibe la luz de las
  antorchas según mire o no hacia la llama (mapa de normales horneado
  por sala), losas y columnas con la misma luz, oclusión de contacto,
  sombras de los personajes en la pared, mapa de luz con parpadeo,
  *bloom*, rayos de luz, niebla sobre las losas, partículas (polvo,
  chispas, sangre, cascotes, ascuas, pétalos, esporas), viñeta y, si
  quieres, grano de película y aberración cromática.
- **Un mundo por nivel**: mazmorra con goteras, cuerpo de guardia,
  osario con telarañas, galería de mármol a la luz de la luna, salón del
  ladrón, escalinata, entrañas de la montaña, cavernas con cristales,
  tumba con jeroglíficos, torre al alba, dominios del visir, aposentos
  con rosas. Cada uno con su paleta, decoración, partículas y fondo
  sonoro.
- **Audio** sintetizado: choques, pasos, rejas, pociones; música
  procedural con diez estilos por ambiente (modos hijaz, nahawand, kurd
  y ajam) y capa de darbuka en combate; ambiente sonoro por nivel.
- **Juice**: sacudida de cámara, *hit-stop* en cada estocada, muerte a
  cámara lenta con el mundo desaturándose, transición deslizante entre
  salas, vibración del mando.
- Menús, opciones persistentes, controles, mapa de salas exploradas,
  estadísticas por nivel, español e inglés, mando (Xbox, PlayStation,
  Switch Pro, Steam Deck), ventana redimensionable, pantalla completa,
  filtro CRT, accesibilidad (sacudida y destellos desactivables, reloj
  siempre visible, volumen por canal).

## Los 14 niveles

Cada nivel es una cuadrícula de salas de 10x3 con un tema mecánico que
se presenta, se retuerce y se combina con un enemigo. La puerta de
salida siempre está cerrada y su placa lejos; hay rejas con mecanismo,
losas-llave, placas de cierre y, en casi todos, una **reja de tesoro**
opcional con la poción grande. El diseño completo, con la deliberación
y los riesgos, está en [`docs/superpensada-niveles.md`](docs/superpensada-niveles.md).

| # | Nivel | Tema mecánico | Set piece | Guardias | Esqueleto |
|---|---|---|---|---|---|
| 1 | Mazmorra | un verbo por sala | el pozo y la losa sobre el primer guardia; duelo final en la puerta | 3 (0) | — |
| 2 | Cuerpo de guardia | duelos con terreno | placa de cierre a la carrera en la 4; losa-llave de la 8 | 5 (1-3) | — |
| 3 | Osario | el esqueleto y las losas | despertar al esqueleto y perderlo por las losas | 4 (2-3) | sí |
| 4 | Galería del espejo | la sombra y las placas de cierre | el espejo; pelea a paso corto sobre pinchos | 4 (3) | — |
| 5 | Salón del ladrón | perder y recuperar | la sombra roba tu poción; placa de cierre ante la cuchilla | 5 (3) | — |
| 6 | La escalinata | saltar a ciegas | la sombra salta contigo; losa-llave de la 6 | 5 (4) | — |
| 7 | Entrañas de la montaña | caer con cabeza | pluma y pozo de tres pisos; losas triples | 5 (5) | — |
| 8 | Cavernas | lo que vive abajo | esqueleto junto a los huesos; el ratón abre la salida | 4 (4) | sí |
| 9 | La tumba | cuchillas y porteros | esqueleto guardando la poción; porteros de la placa | 5 (5) | sí |
| 10 | La torre | bajar | pluma para bajar el pozo de un salto | 6 (5) | — |
| 11 | Lo alto de la torre | rejas en cadena | losa-llave de la 13 sobre la placa de la 5 | 5 (3-5) | — |
| 12 | Dominios del visir | todo junto | Jaffar; fusión con la sombra; cadena de tres placas | 7 (6-8) | sí |
| 13 | La huida final | velocidad | tres guardias en la carrera; losas sobre el vacío | 3 (6) | — |
| 14 | Aposentos | — | el reencuentro | — | — |

Cómo se verifica cada nivel:

- **Bot** sin guardias (trampas reales): recorre la ruta prevista
  (`tests/canon/routes.py`), pisa la placa de la salida y cruza la puerta
  jugando ticks reales del motor.
- **Solucionador humano** con guardias, cuchillas y la vida media de
  campaña: genera un replay dorado (`tests/canon/replays/L<n>.txt`) que
  se reproduce en cada ejecución de la suite.
- **Tests de diseño**: ninguna sala plana ni repetida, cornisas
  trepables, ninguna caída acaba en un muro, los bordes entre salas
  encajan, placa de salida lejana, rejas con mecanismo, trampas y
  pociones mínimas, guardias por nivel y rejas de tesoro.

## Instalación

Requisitos: **Python 3.13+**.

```bash
# Con uv (recomendado)
uv sync
uv run pop2026canon

# Sin uv
python -m pip install -r requirements.txt
python persia.py
```

En Windows con el Python Launcher: `py -3.13 persia.py`. El motor
original de 2026 (`pop2026`, vector-retro, 100 niveles) sigue
disponible con `uv run pop2026`.

## Calidad

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy --strict src
uv run pytest --cov=src --cov-report=term-missing
```

CI en GitHub Actions con Python 3.13 y 3.14. Más de 1400 tests: dominio
puro, solucionadores que juegan cada nivel, replays dorados, tests
visuales por sala, audio, menús, progreso y la app completa sin ventana.

## Documentación

- [`docs/superpensada-niveles.md`](docs/superpensada-niveles.md) —
  diseño nivel a nivel: diagnóstico, deliberación, plan, riesgos.
- [`docs/design/`](docs/design) — diseño por subsistema del motor canon.
- [`docs/original_program_analysis.md`](docs/original_program_analysis.md)
  — arqueología del original.
- [`docs/architecture.md`](docs/architecture.md),
  [`docs/design.md`](docs/design.md), [`docs/adr/`](docs/adr) — motor
  `pop2026` (v1.0), capas, sistema visual, decisiones.
- [`docs/roadmap-v2.md`](docs/roadmap-v2.md), [`docs/plan-v4.md`](docs/plan-v4.md),
  [`docs/puzzles-v1.md`](docs/puzzles-v1.md) — planes del motor v1.0.
- [`CHANGELOG.md`](CHANGELOG.md) — todo lo entregado, versión a versión.

## Licencia

MIT. Ver [`LICENSE`](LICENSE). "Prince of Persia" es marca registrada
de Ubisoft; este proyecto es una reinterpretación fan y no redistribuye
código ni assets originales.
