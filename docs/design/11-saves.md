# `docs/design/11-saves.md` — Saves y level select

## Slot format

```python
@dataclass(frozen=True)
class SaveSlot:
    version: int           # protocolo de save
    level: int             # 1..14
    room: int              # sala actual
    col: int               # posición kid
    row: int
    direction: int
    hp_curr: int
    hp_max: int
    minutes_left: int
    ticks_left: int
    sword: int             # 0 sheathed, 2 drawn
    flags: int             # shadow_initialized, has_stolen_potion, etc.
    rng_seed: int          # para reproducibilidad
```

## Backend

Mantener `pop2026/infrastructure/savegame.py` (Pydantic v2 JSON) o
migrar a struct binario compatible con SDLPoP. Decisión: **JSON
propio** — no necesitamos compatibilidad de save format con SDLPoP.

## Quicksave

- `F5` guarda en slot 0
- `F9` carga slot 0
- Auto-save al pasar de nivel (slot 1)

## Level select

Para desarrollo / debug:
- CLI `--start-level N` (ya existe en `pop2026/cli.py`)
- En el menú de título, opción "level select" si flag debug activo

## Tests

- save + load roundtrip preserva estado
- save de level 1 + load → kid en spawn de nivel 1
- save corrupto → mensaje claro

Estimación: 1 día.
