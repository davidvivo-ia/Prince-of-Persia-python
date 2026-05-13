# pop2026 — Prince of Persia reimaginado

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

### Opción B — con `python` plano (Windows, sin `uv`)

```powershell
py -3.13 -m pip install -r requirements.txt
py -3.13 persia.py                   # juega
py -3.13 persia.py --demo --seed 42  # demo determinista
py -3.13 persia.py --help
```

En Linux/macOS funciona el mismo flujo con `python3.13` en lugar de `py -3.13`.

> El script `persia.py` añade `src/` al `sys.path`, así que no hace
> falta instalar el paquete. Si prefieres instalarlo:
> `python -m pip install -e .` y luego `pop2026` queda disponible como
> comando.

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
- [`docs/postmortem.md`](docs/postmortem.md) — qué se ganó, qué se
  perdió, qué dice del oficio.

## Licencia

MIT. Ver [`LICENSE`](LICENSE). "Prince of Persia" es marca registrada
de Ubisoft; este proyecto es una reinterpretación fan y no redistribuye
código ni assets originales.
