# pop2026 — Prince of Persia reimaginado · 100 niveles

> **v3.0** · 12 niveles narrativos hand-crafted + 88 procedurales por
> semilla determinista · 4 actos · cinemáticas · música ambient · save/load.

> *Una mazmorra que respira en violeta y oro, dibujada con la mano de
> 1989 pero el aliento de 2026.*

Reimplementación moderna en **Python 3.13+** del Prince of Persia
original de Jordan Mechner (1989). Preserva la lógica funcional y el
alma del original; reimagina todo lo demás.

- **Motor**: dominio puro, FSM explícitas, físicas inerciales.
- **Render**: pygame-ce con dibujo geométrico procedural (vector-retro).
- **Audio**: PC-speaker sintetizado (numpy → pygame mixer).
- **Determinismo**: `--seed` reproduce partidas exactas; `--demo`
  juega solo.
- **Calidad**: `ruff`, `mypy --strict`, `pytest` con cobertura ≥80%.

## Motor canon · Edición 2026 (`pop2026canon`)

El motor `pop2026canon` reproduce las reglas del POP1 de 1989 (física,
trampas y enemigos calcados de SDLPoP) y las presenta como un juego de
hoy:

```bash
uv run pop2026canon                    # juega (menú principal)
uv run pop2026canon --levels-dat RUTA  # con los niveles de tu copia original
```

- **Dos modos**: *moderno* (rebobinar con las Arenas del Tiempo y
  reaparecer en la entrada de la sala) y *clásico 1989* (morir
  reinicia el nivel). El reloj de 60 minutos es canon en ambos.
- **Gráficos HD**: lienzo 1280x852, personajes animados con esqueleto
  (una pose por frame canon, vestuario por personaje), tiles con
  volumen (losas biseladas, columnas por delante del personaje, rejas
  de hierro, frascos de vidrio, llamas animadas) y pared de piedra
  generada por sala. Todo procedural, sin assets del original.
- **Niveles con puzles**: la puerta de salida siempre está cerrada y su
  placa lejos; rejas con temporizador, placas de cierre que hay que
  saltar, losas que caen sobre placas, pasillos de cuchillas y pinchos,
  pozos y cornisas para subir y bajar entre pisos, pociones escondidas.
- **Cada nivel, su mundo**: los 14 niveles tienen salas que usan toda la
  altura (cornisas, plataformas, muros macizos) y un tema visual propio — mazmorra con goteras, osario con telarañas, galería de
  mármol a la luz de la luna, cavernas con cristales, tumba con
  jeroglíficos, torre al alba, dominios del visir, aposentos con rosas.
- **Luz y ambiente**: antorchas que iluminan la piedra, mazmorra fría y
  palacio cálido, *bloom*, rayos de luz, niebla baja, partículas
  (polvo, chispas, sangre, cascotes, ascuas), viñeta, sacudida de
  cámara, *hit-stop* en cada estocada y transición deslizante entre
  salas.
- **Audio sintetizado**: choques metálicos, pasos, rejas; música
  procedural en modo *hijaz* con capa de darbuka en combate; estéreo.
- **Mando** (Xbox, PlayStation, Switch Pro, Steam Deck) y teclado.
- **Interfaz**: menú principal, pausa, opciones persistentes, controles,
  mapa de salas exploradas, estadísticas por nivel, pistas contextuales
  la primera vez que hace falta cada verbo.
- **Historia**: cinemática de introducción (Jaffar, la princesa y el
  reloj de arena) y reencuentro final; guardias vestidos según el nivel;
  muerte a cámara lenta; ambiente sonoro por nivel; vibración del mando.
- **Progreso y medallas**: selección de nivel con mejores tiempos,
  medallas (Completado, Sin un rasguño, Veloz, Explorador) y dificultad
  normal / difícil.
- **Idioma**: español o inglés, desde opciones.
- **Pantalla**: ventana redimensionable, pantalla completa (F11), escala
  suave o entera nítida, filtro CRT y resplandor opcionales.
- **Accesibilidad**: sacudida y destellos desactivables, reloj siempre
  visible, pistas, volumen por canal.

| Acción | Teclado | Mando |
|---|---|---|
| Correr | ← → / A D | Cruceta / stick |
| Saltar · trepar | ↑ / W | A |
| Agacharse · descolgarse | ↓ / S | B |
| Agarrarse · paso corto | Shift | RB / RT |
| Atacar | Espacio / J | X |
| Rebobinar (moderno) | R (mantener) | LB / LT |
| Pausa · mapa | Esc · M | Start · Back |

## Vista previa (ASCII de captura)

```
┌──────────────────────────────────────────────────────────────────┐
│  NIVEL 1 · MAZMORRA                              ⏱ 59:42  ♥♥♥♥   │
├──────────────────────────────────────────────────────────────────┤
│ ##############################################################   │
│ #..........................................................#    │
│ #..@.........=====.........|...........+.....................   │
│ #####...^^^...#####....#####...########.........############    │
│      #.......#     #..#     #.#        #.......#                │
│      #########     ####     #.##########   g   #     >          │
│                              #              ####################│
└──────────────────────────────────────────────────────────────────┘
   ←→ moverse · ↑ saltar · ↓ agacharse · ⎵ atacar · Q parar · Esc pausa
```

## Instalación rápida

Requisitos: **Python 3.13+**.

### Opción A — con `uv` (recomendado, Linux/macOS/WSL)

```bash
uv sync                              # instala todo
uv run pop2026                       # juega
uv run pop2026 --demo --seed 42      # demo determinista
uv run pop2026 --help
```

### Opción B — con `python` plano (Windows / cualquier sistema, sin `uv`)

```bash
python -m pip install -r requirements.txt
python persia.py                     # juega
python persia.py --demo --seed 42    # demo determinista
python persia.py --help
```

> Si en tu Windows tienes el "Python Launcher" en vez del comando
> `python`, sustituye por `py -3.13`. En Linux/macOS, `python3` o
> `python3.13` funcionan igual.
>
> `persia.py` añade `src/` al `sys.path`, así que no hace falta
> instalar el paquete. Si prefieres instalarlo:
> `python -m pip install -e .` y luego `pop2026` queda disponible como
> comando en el PATH.

## Calidad

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy --strict src
uv run pytest --cov=src --cov-report=term-missing
```

## Estructura

Ver [`docs/architecture.md`](docs/architecture.md) y
[`docs/design.md`](docs/design.md).

## Documentación

- [`docs/original_program_analysis.md`](docs/original_program_analysis.md)
  — arqueología del original.
- [`docs/architecture.md`](docs/architecture.md) — capas y composición.
- [`docs/design.md`](docs/design.md) — sistema visual, paleta,
  tipografía, audio, accesibilidad.
- [`docs/adr/`](docs/adr) — Architecture Decision Records.
- [`docs/design/`](docs/design) — diseño por subsistema del motor canon.
- [`docs/roadmap-v2.md`](docs/roadmap-v2.md), [`docs/plan-v4.md`](docs/plan-v4.md),
  [`docs/puzzles-v1.md`](docs/puzzles-v1.md) — planes del motor v1.0.
- [`docs/postmortem.md`](docs/postmortem.md) — qué se ganó, qué se
  perdió, qué dice del oficio.

## Licencia

MIT. Ver [`LICENSE`](LICENSE). "Prince of Persia" es marca registrada
de Ubisoft; este proyecto es una reinterpretación fan y no redistribuye
código ni assets originales.
