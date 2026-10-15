# `pop2026canon` — Motor canon Prince of Persia 1989 en Python

Clon tile-based del POP1 original (Jordan Mechner, Broderbund 1989) con
paridad mecánica respecto a [SDLPoP](https://github.com/NagyD/SDLPoP).

## Instalación

```bash
uv sync
```

## Ejecutar

```bash
# Lanzar el juego desde nivel 1
python -m pop2026canon

# Empezar en un nivel específico (1-14)
python -m pop2026canon --level 5

# Demo headless (sin ventana, para CI)
python -m pop2026canon --headless --frames 200

# Generar preview PNG de una sala
python -m pop2026canon preview 12 --out /tmp/l12.png
```

## Controles

| Tecla | Acción |
|---|---|
| ← → | Mover izquierda/derecha |
| ↑ | Saltar |
| ↓ | Agacharse |
| SHIFT | Agarrar cornisa al caer / andar lento |
| SPACE | Atacar con sable |
| Q | Atacar (alternativa) |
| W A S D | Direcciones (alternativa) |
| ESC | Salir |

## Mecánicas canon implementadas

- **Tile-based physics**: posición sub-tile + cell, sin float.
- **Frame chains canónicas**: 25 secuencias (stand, run, jump, hang, climb, sword, death...) replicando `seqtbl.c` de SDLPoP.
- **Hang grab manual**: requiere SHIFT + `fall_y < 32` (canon).
- **Gravity discreta**: `fall_y` += 3 hasta MAX=33.
- **Loose floors**: 11 ticks de presión antes de caer.
- **Chompers**: ciclo de 15 ticks, letales en estado CLOSED.
- **Spikes**: letales solo al aterrizar con `fall_y >= 10`.
- **Gates**: 8 estados (0 cerrada → 7 abierta) controlados por plates.
- **Combate**: HP por nivel (`tbl_guard_hp = {4,3,3,3,3,4,5,4,4,5,5,5,4,6}`), ventana strike 165-167, block 161-164.
- **Skeleton inmortal**: HP=0 → HP=1 + HURT (no muere).
- **Shadow encounters**: L4 mirror (nace), L5 steal (roba poción), L6 step (frame 43), L12 fusion (+1 HP).
- **Vizier**: L12 sala 7, char especial con skill 11.
- **Princess + Mouse**: cinemática final (L14) y abertura de gate (L8).
- **60 minutos canon**: timeout → princesa muere.

## Arquitectura

```
src/pop2026canon/
├── domain/             # Lógica pura (sin pygame)
│   ├── actions.py      # Action / Seq / FrameID / Direction
│   ├── chars.py        # Char + CharId + GuardSkill
│   ├── combat.py       # take_hp / resolve_combat
│   ├── constants.py    # Constantes canon de data.h
│   ├── frames.py       # Catálogo de ~110 frames
│   ├── game.py         # Game aggregate
│   ├── level.py        # Level + Event + EventKind
│   ├── levels_canon.py # Los 14 niveles canon
│   ├── physics.py      # play_seq + gravity + grab
│   ├── princess.py     # Princess + Mouse
│   ├── room.py         # Room (10x3 tiles)
│   ├── seqtbl.py       # 25 secuencias canónicas
│   ├── shadow.py       # 4 encuentros shadow
│   ├── skeleton.py     # Skeleton inmortal L3
│   ├── tiles.py        # 31 tile types
│   ├── traps.py        # Loose / chomper / spike / gate
│   └── vizier.py       # Jaffar
├── application/
│   ├── audio_bridge.py # Game transitions → SFX
│   ├── controller.py   # Input → seq transitions
│   └── tick.py         # Loop lógico 12 FPS
├── infrastructure/
│   ├── audio.py        # Beeper PC-speaker
│   └── savegame.py     # Save slot JSON
├── presentation/
│   ├── char_atlas.py   # Sprites kid procedurales
│   ├── input_device.py # pygame → Command
│   ├── layout.py       # Geometría 28x126 (escala 2x canon)
│   ├── palette.py      # Paleta tributo HGR
│   ├── renderer.py     # Render principal
│   ├── tile_atlas.py   # 31 draws procedurales
│   └── screens/        # Title, cutscene, ending
├── cli.py
└── __main__.py
```

## Tests

```bash
uv run pytest tests/canon/ -q
```

## Créditos

- **Jordan Mechner** — diseño y código original del Prince of Persia (1989, Broderbund).
- **NagyD / princed.org community** — [SDLPoP](https://github.com/NagyD/SDLPoP), referencia ejecutiva moderna.

Este motor es **clean-room**: ningún byte del binario original ni del
código de SDLPoP se reproduce. Implementación propia inspirada en las
mecánicas documentadas públicamente.
