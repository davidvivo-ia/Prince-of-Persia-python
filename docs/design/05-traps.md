# `docs/design/05-traps.md` — Trampas

Estado por tile dinámico vive en `LevelState.tile_states: dict[(room,col,row), int]`.

## Loose floor (`tiles_11_loose`)

```
state ∈ {STABLE=0, SHAKING=1..11, FALLEN=12}
```
- STABLE → SHAKING al pisar arriba (kid en `(row-1, col)`)
- SHAKING avanza 1/tick; en `state == 11` (= `loose_floor_delay`) cae
- FALLEN: el tile pasa a `tiles_14_debris` SOLID en `(row+1, col)`,
  el `(row, col)` queda EMPTY
- Si el kid está en `(row-1, col)` cuando cae, action → `action_4_in_freefall`

## Spike (`tiles_2_spike`)

```
state ∈ {RETRACTED=0, EXTENDING=1..3, EXTENDED=4, RETRACTING=5..7}
```
- Trigger: kid pisa la celda con `fall_y >= 10` (caída) → impale instantáneo
- Walking sobre spike retracted = OK
- Ciclo automático según nivel: niveles avanzados los pinchos hacen
  ciclos extend/retract continuos
- Animación: 4 frames de extensión, 4 de retracción

## Chomper (`tiles_18_chomper`)

```
state ∈ {OPEN_FULL=0, CLOSING=1..3, CLOSED=4, OPENING=5..7}
```
- `chomper_speed = 15` ticks por ciclo completo
- Si kid está en la celda en `CLOSED` → instakill (`seq_54_chomped`)
- El render dibuja las hojas verticalmente; SFX al cerrar

## Slicer

Variante de chomper pero vertical (cae del techo). Mismo modelo de
estado, sprite distinto.

## Gate (`tiles_4_gate`)

```
state ∈ {CLOSED=0, OPENING=1..7, OPEN=8, CLOSING=9..15}
```
- Trigger: pisar `tiles_15_opener` (plate)
- `doorlinks` mapea cada plate→gate(s) — un plate puede abrir varias
- `tiles_6_closer` cierra gates (botón rojo)
- Cuando OPEN, el tile no es SOLID (kid pasa)
- Render: 8 estados visuales de barrotes bajándose

## Pillar-up / freezing block

Niveles avanzados: tiles que se elevan o congelan al kid. (P2,
implementación tardía.)

## Step de trampas (orden por tick)

```python
def tick_traps(game: Game) -> Game:
    new_states = dict(game.state.tile_states)
    for (room, col, row), st in game.state.tile_states.items():
        tile = game.level.rooms[room - 1].fg[row * 10 + col]
        new_st = advance_trap(tile, st, kid_pos=(game.kid.room, game.kid.curr_col, game.kid.curr_row))
        new_states[(room, col, row)] = new_st
        # detectar instakill
        if kills_kid(tile, new_st, game.kid):
            game = replace(game, kid=apply_kill_seq(game.kid, tile))
    return replace(game, state=replace(game.state, tile_states=new_states))
```

## Tests

`tests/canon/test_05_traps.py`:
- loose floor cae tras 11 ticks de presión y aparece debris bajo
- chomper instakill cuando state=CLOSED y kid en celda
- spike instakill solo si fall_y >= 10
- gate abre 8 niveles tras pisar plate, cierra 16 tras dejar

Estimación: 3 días.
