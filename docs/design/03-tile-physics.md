# `docs/design/03-tile-physics.md` — Física tile-based

> Padre: `00-architecture.md`. Sustituye al motor continuo actual por
> uno **tile-based** alineado con SDLPoP.

## 1. Principio

El char vive en `(curr_col, curr_row)` (celda) más un **offset
sub-tile** `(x, y)` en píxeles canónicos (14 horizontales, 63
verticales). El movimiento se aplica como `dx`/`dy` en cada acto de
`seqtbl` (ver `02-frame-system.md`).

**Nada de velocidades continuas. Nada de aceleración float.** La
"gravedad" en POP1 es un `fall_y` discreto.

## 2. Caída libre (`fall_accel`, `fall_speed`)

Replicando `seg006.c`:

```python
FALLING_SPEED_MAX = 33     # px sub-tile / tick
FALLING_SPEED_ACCEL = 3    # incremento por tick
FALLING_SPEED_MAX_FEATHER = 4
FALLING_SPEED_ACCEL_FEATHER = 1

def fall_accel(char: Char, has_feather: bool) -> Char:
    if char.action != action_4_in_freefall:
        return char
    a = FALLING_SPEED_ACCEL_FEATHER if has_feather else FALLING_SPEED_ACCEL
    mx = FALLING_SPEED_MAX_FEATHER if has_feather else FALLING_SPEED_MAX
    return replace(char, fall_y=min(mx, char.fall_y + a))

def fall_speed(char: Char) -> Char:
    new_y = char.y + char.fall_y
    new_x = char.x + char.fall_x * char.direction
    return normalize_to_cell(replace(char, x=new_x, y=new_y))
```

`normalize_to_cell` redistribuye desbordes de sub-tile a
`curr_col`/`curr_row`:

```python
def normalize_to_cell(char: Char) -> Char:
    col, x = char.curr_col, char.x
    row, y = char.curr_row, char.y
    while x >= 14:
        x -= 14; col += 1
    while x < 0:
        x += 14; col -= 1
    while y >= 63:
        y -= 63; row += 1
    while y < 0:
        y += 63; row -= 1
    return replace(char, curr_col=col, curr_row=row, x=x, y=y)
```

## 3. Colisión

`check_collision(char, room)`:

```python
def check_collision(char: Char, room: Room) -> Char:
    """Si el char invadió un tile sólido, revertir y disparar bumped/freefall."""
    tile = tile_at(room, char.curr_col, char.curr_row)
    if tile_is_blocking(tile, char.action):
        # revertir al estado anterior y triggear seq_bumped
        return bumped(char)
    if tile_is_loose(tile):
        # cae si la trampa ya se rompió
        return maybe_fall_through_loose(char, room)
    return char
```

`tile_is_blocking` consulta `SOLID = {FLOOR, LOOSE, GATE_CLOSED, WALL,
PILLAR, BIGPILLAR, DEBRIS_SOLID, CHOMPER_CLOSED, ...}`.

## 4. Detección de cornisa (`check_grab`)

Replica canónico con SHIFT obligatorio:

```python
def check_grab(char: Char, cmd: Command, room: Room) -> Char | None:
    if not cmd.shift:
        return None
    if char.action != action_3_in_midair:
        return None
    if char.fall_y >= 32:  # cayendo demasiado rápido
        return None
    if char.alive >= 0:
        return None  # muerto
    # Tile delante a la altura de la cabeza
    forward_col = char.curr_col + char.direction
    head_row = char.curr_row - 1
    if not is_grabbable_ledge(room, head_row, forward_col):
        return None
    # Snap a hang
    return replace(
        char,
        curr_seq_id=SEQ_15_GRAB_LEDGE_MIDAIR,
        curr_seq_idx=0,
        action=action_6_hang_straight,
        fall_y=0, fall_x=0,
    )
```

`is_grabbable_ledge(room, row, col)`:
- Tile `(row, col)` SOLID o `tiles_floor`
- Tile `(row-1, col)` no SOLID (para que la mano pueda agarrar)

## 5. Cambio de sala

Cuando `normalize_to_cell` deja `curr_col` fuera de `[0, 9]`:

```python
def maybe_change_room(char: Char, level: Level) -> Char:
    if char.curr_col < 0:
        new_room = level.rooms[char.room].links.west
        if new_room == 0:
            return bumped(char)  # pared
        return replace(char, room=new_room, curr_col=9)
    if char.curr_col > 9:
        new_room = level.rooms[char.room].links.east
        if new_room == 0:
            return bumped(char)
        return replace(char, room=new_room, curr_col=0)
    # Idem rows para N/S
    return char
```

## 6. Step de física (orden por tick)

```python
def step_physics(char: Char, room: Room, level: Level, cmd: Command) -> Char:
    # 1. Avanza secuencia (frame_advance)
    char = play_seq(char, SEQTBL)
    # 2. Aplica gravedad si en freefall
    char = fall_accel(char, has_feather=False)
    char = fall_speed(char)
    # 3. Normaliza posición
    char = normalize_to_cell(char)
    # 4. Cambio de sala si cruzó borde
    char = maybe_change_room(char, level)
    # 5. Colisiones
    char = check_collision(char, room)
    # 6. Grab a cornisa si SHIFT y condiciones
    grabbed = check_grab(char, cmd, room)
    if grabbed is not None:
        char = grabbed
    return char
```

## 7. Estados de char (`action`)

| Action | Comportamiento físico |
|---|---|
| 0 stand | No physics; espera input |
| 1 run_jump | Movimiento controlado por seqtbl |
| 2 hang_climb | Trepando — sin gravity |
| 3 in_midair | Subiendo del salto — gravity 0 |
| 4 in_freefall | Cayendo — fall_y acelera |
| 5 bumped | Choque, perdió velocidad |
| 6 hang_straight | Colgado quieto — sin gravity |
| 7 turn | Girando — sin desplazamiento |
| 99 hurt | Inmóvil unos frames |

## 8. Diferencia con motor anterior

| Aspecto | Antes (`pop2026`) | Ahora (`pop2026canon`) |
|---|---|---|
| Pos | float `body.pos.{x,y}` | int `curr_col/row + x/y` sub-tile |
| Vel | float `body.vel.{vx,vy}` | int `fall_x, fall_y` (solo caída) |
| Gravedad | float continua 0.06 cells/tick² | int 3 px/tick² discreto |
| Salto | impulso JUMP_VEL = -0.55 cells/tick | seq con `dx`/`dy` por frame |
| Air control | AIR_ACCEL = 0.025 lerp continuo | NO existe (canon) |
| Coyote time | 6 ticks | NO existe (canon) |
| Jump buffer | 6 ticks | NO existe (canon) |
| Variable jump cut | sí | NO existe (canon) |
| Knockback | float vx + KNOCKBACK_TICKS | bumped seq + fall_x |
| Hang grab | automático | manual con SHIFT |

## 9. Tests

`tests/canon/test_03_tile_physics.py`:
- `fall_accel` acelera `fall_y` en +3 cada tick hasta 33
- `fall_speed` aplica `fall_y` a `char.y` correctamente
- `normalize_to_cell` redistribuye desbordes
- `maybe_change_room` cambia de sala al cruzar borde
- `check_grab` requiere SHIFT y `fall_y < 32`
- `check_collision` reverte movimiento si tile sólido
- Secuencia completa: spawn → fall → grab → climb → stand

## 10. Estimación

3 días: 1 día scaffolding, 1 día collision + room change, 1 día tests
+ integración con seqtbl.
