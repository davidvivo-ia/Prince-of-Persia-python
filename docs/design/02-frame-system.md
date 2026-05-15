# `docs/design/02-frame-system.md` — Sistema de frames y secuencias

> Padre: `00-architecture.md`. Define `domain/frames.py`,
> `domain/seqtbl.py` y la lógica de avance frame-a-frame canónica.

## 1. Concepto canónico

El kid (y el resto de chars) tiene un `frame: int` actual. Cada tick
lógico (12 FPS):

1. Lee el siguiente `SeqAct` del `seqtbl` apuntado por `curr_seq_idx`.
2. Aplica el efecto:
   - `FRAME(n)`: pinta el frame `n` y avanza el cursor — termina el tick
   - `DX(n)`: aplica desplazamiento horizontal en el char (sub-tile)
   - `DY(n)`: aplica desplazamiento vertical
   - `SND(n)`: dispara sonido
   - `SET_FALL(dx, dy)`: setea fall_x y fall_y
   - `JMP(label)`: salta a otro punto de seqtbl

3. Cuando se encuentra `FRAME(n)`, el tick termina y el char queda en
   ese frame visualmente hasta el próximo tick.

Esto significa: **un tick = un frame visible**. Las acciones largas
encadenan FRAME → DX/DY → FRAME → DX/DY...

## 2. Tabla de frames (`domain/frames.py`)

180 entradas:

```python
@dataclass(frozen=True, slots=True)
class Frame:
    id: int           # 0..255 (algunos huecos)
    sprite: str       # nombre del slot en char_atlas
    shift_x: int      # ajuste de origen sub-tile px
    shift_y: int      # ajuste de origen sub-tile px
    weight: int       # flag para colisión (HEAVY=2, NORMAL=1)
    sound: int = 0    # sonido implícito al pintar este frame (footstep etc.)
```

Mapping aproximado por rangos (validado en `types.h` extraído en audit):

| Rango | Acción |
|---|---|
| 0-14 | Reservado / `stand_up` |
| 15 | `stand` (parado base) |
| 16-23 | Standing jump preparation |
| 24-33 | Standing jump airborne + landing |
| 34-39 | Start run jump (windup) |
| 40-44 | Running jump (5 frames cubriendo ~3 tiles) |
| 45-52 | Turn (8 frames de giro) |
| 53-66 | Run-turn (giro mientras corre) |
| 67-80 | Jump up & hang (14 frames del agarre) |
| 81-99 | Hanging variations (hangstraight, hang, climbup) |
| 102-108 | Fall & landing |
| 109-119 | Crouch & stand up |
| 121-132 | Stepping (12 frames del walk normal) |
| 135-149 | Climbing |
| 150-176 | Sword combat (engarde, strike, parry, advance, retreat) |
| 177 | Spiked |
| 178 | Chomped |
| 179-185 | Collapse & death |
| 191-205 | Drink potion |
| 207-210 | Draw sword |
| 217-228 | Exit stairs |
| 229 | Found sword |
| 230-240 | Sheathe sword |

180 IDs aproximados con huecos.

## 3. Tabla de secuencias (`domain/seqtbl.py`)

94 entradas. Esquema:

```python
class ActKind(IntEnum):
    FRAME = 0       # arg = frame id
    DX = 1          # arg = pixels (sub-tile)
    DY = 2
    SND = 3         # arg = sound id
    SET_FALL = 4    # arg = fall_x, arg2 = fall_y
    JMP = 5         # arg = seq id destino
    SETUP = 6       # arg = action id (e.g. set actions_4_in_freefall)
    NOP = 7

@dataclass(frozen=True, slots=True)
class SeqAct:
    kind: ActKind
    arg: int
    arg2: int = 0

Sequence = tuple[SeqAct, ...]
```

```python
# Ejemplo de secuencia: standing → start run (seq_1_start_run)
# Cada acto es un step incremental.
SEQ_1_START_RUN: Sequence = (
    SeqAct(ActKind.SETUP, action=0),  # action_0_stand
    SeqAct(ActKind.FRAME, 7),         # frame 7 — windup
    SeqAct(ActKind.DX, 1),
    SeqAct(ActKind.FRAME, 8),
    SeqAct(ActKind.DX, 1),
    SeqAct(ActKind.FRAME, 9),
    SeqAct(ActKind.DX, 2),
    SeqAct(ActKind.FRAME, 10),
    SeqAct(ActKind.DX, 2),
    SeqAct(ActKind.FRAME, 11),
    SeqAct(ActKind.JMP, SEQ_84_RUN),
)
```

(Valores ilustrativos — los exactos se extraerán de `seqtbl.c` de
SDLPoP en la implementación.)

Las 94 secuencias se nombran como en SDLPoP: `SEQ_2_STAND`,
`SEQ_3_STANDING_JUMP`, `SEQ_4_RUN_JUMP`, ..., `SEQ_85_STABBED_TO_DEATH`.

## 4. Frame advance (`domain/physics.py:play_seq`)

```python
def play_seq(char: Char, seqtbl: SeqTbl) -> Char:
    """Avanza la secuencia hasta el próximo FRAME (incluido)."""
    seq = seqtbl[char.curr_seq_id]
    idx = char.curr_seq_idx
    x, y = char.x, char.y
    fall_x, fall_y = char.fall_x, char.fall_y
    new_frame = char.frame
    new_action = char.action
    new_sound = 0
    new_seq = char.curr_seq_id

    while True:
        act = seq[idx]
        if act.kind is ActKind.FRAME:
            new_frame = act.arg
            idx += 1
            break
        elif act.kind is ActKind.DX:
            x += act.arg * char.direction
        elif act.kind is ActKind.DY:
            y += act.arg
        elif act.kind is ActKind.SND:
            new_sound = act.arg
        elif act.kind is ActKind.SET_FALL:
            fall_x, fall_y = act.arg, act.arg2
        elif act.kind is ActKind.SETUP:
            new_action = act.arg
        elif act.kind is ActKind.JMP:
            new_seq = act.arg
            seq = seqtbl[new_seq]
            idx = 0
        elif act.kind is ActKind.NOP:
            pass
        idx += 1

    # Normaliza x, y → curr_col/row + sub-tile
    new_col, new_row, new_x, new_y = normalize_pos(char.curr_col, char.curr_row, x, y)

    return replace(
        char,
        curr_col=new_col, curr_row=new_row,
        x=new_x, y=new_y,
        frame=new_frame,
        action=new_action,
        curr_seq_id=new_seq,
        curr_seq_idx=idx,
        fall_x=fall_x, fall_y=fall_y,
    )
```

## 5. Transiciones entre secuencias

Externas al `play_seq`:
- **Input del jugador**: si el comando es válido en la acción actual,
  setear `curr_seq_id = SEQ_X_NEW`, `curr_seq_idx = 0`.
- **Eventos físicos**: colisión, caída, golpe → cambian seq.
- **JMP interno**: la propia seq finaliza saltando a otra (ej. el
  ciclo `run` salta a sí mismo).

Reglas en `domain/transitions.py` (estilo SDLPoP `control.c`):

```python
def on_command_stand(char: Char, cmd: Command) -> Char | None:
    if cmd.right and char.direction > 0:
        return replace(char, curr_seq_id=SEQ_1_START_RUN, curr_seq_idx=0)
    if cmd.right and char.direction < 0:
        return replace(char, curr_seq_id=SEQ_5_TURN, curr_seq_idx=0)
    if cmd.jump:
        return replace(char, curr_seq_id=SEQ_3_STANDING_JUMP, curr_seq_idx=0)
    if cmd.shift and cmd.up:
        return replace(char, curr_seq_id=SEQ_55_DRAW_SWORD, curr_seq_idx=0)
    if cmd.down:
        return replace(char, curr_seq_id=SEQ_50_CROUCH, curr_seq_idx=0)
    return None
```

## 6. Atlas de chars (`presentation/char_atlas.py`)

Cada frame del kid (y demás chars) se dibuja procedurally con
primitivas pygame. NO sprites bitmap. Esto significa que las 180
entradas son **funciones de dibujo** parametrizadas por:

- Paleta (kid = primary+sash, shadow = silueta violeta, guard =
  armadura, princess = robe, vizier = robe black/gold, mouse =
  ratón pequeño)
- Direction (mirroring)
- Frame ID

```python
def draw_char_frame(
    surface, char: Char, frame: Frame, x_px: int, y_px: int, palette: Palette
):
    """Dibuja la silueta procedural del frame en pos píxel."""
    ...
```

Estrategia para 180 frames: definir 12-15 **building blocks** (head,
torso, arms, legs en diferentes poses) y combinarlos por frame ID.
No es 1-a-1 con los 180 sprites de POP1 pero captura la silueta.

## 7. Tests

`tests/canon/test_02_frame_system.py`:
- `play_seq` con cada secuencia conocida produce el frame esperado
- Secuencia que termina con JMP avanza a la nueva secuencia
- Frame IDs únicos en el atlas (sin huecos sin definir)
- Mirror horizontal correcto cuando direction = -1
- Snapshot test de los 20 frames más importantes

## 8. Riesgos

- **Reverso completo de seqtbl.c**: 94 secuencias × 10-50 acts cada
  una = ~2000 acts. Extracción mecánica del C posible con script.
- **Atlas procedural**: 180 frames procedurales son trabajo de
  ilustración. Aceptable como tributo si captura silueta.

## 9. Estimación

5 días: 1 día scaffolding + DSL, 2 días extracción mecánica de
seqtbl, 2 días atlas procedural + tests.
