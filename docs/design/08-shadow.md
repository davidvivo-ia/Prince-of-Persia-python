# `docs/design/08-shadow.md` — Shadow man

> Cuatro apariciones canónicas. Verificado en audit (`seg002.c`):

| Nivel | Sala | Evento | charid |
|---|---|---|---|
| 4 | 4 | Mirror — kid salta a través, shadow nace | `charid_1_shadow` |
| 5 | 24 | Steal potion — shadow roba la poción | `charid_1_shadow` |
| 6 | 1 | Step — shadow salta cuando kid en frame_43 | `charid_1_shadow` |
| 12 | 15 | Final fusion — kid se "une" para +HP | `charid_1_shadow` |

## Modelo

```python
@dataclass(frozen=True)
class ShadowState:
    initialized: bool = False
    encounter: int = 0    # contador de encounters resueltos
    has_stolen_potion: bool = False
    fused: bool = False
```

Vive en `Game.flags` (bit fields) o `Game.shadow_state`.

## L4 — Mirror

- Sala 4 contiene `tiles_13_mirror` en una posición concreta.
- Cuando el kid hace `seq_4_run_jump` cruzando la celda del mirror:
  - El mirror se "rompe" (tile changes to `tiles_14_debris`)
  - Spawn de char `charid_1_shadow` en la celda
  - Shadow corre hacia el oeste y desaparece al borde
- `shadow.initialized = True`

## L5 — Steal

- Sala 24 contiene una poción.
- Cuando el kid entra y la puerta está abierta, el shadow llega
  corriendo desde el oeste, recoge la poción y desaparece al este.
- `shadow.has_stolen_potion = True` — la poción de la sala se marca
  `consumed`.

## L6 — Step

- Sala 1.
- Cuando el kid está en `frame_43` (mid-runjump) y en la celda
  trigger, spawnea shadow que salta desde la pared opuesta.
- Es decorativo / cinemático — no daña.

## L12 — Final fusion

- Sala 15. `shadow_initialized` ya es True.
- El shadow imita los movimientos del kid pero invertidos.
- Si el kid hace seq que choca con el shadow (e.g., touch), se fusionan:
  - `hp_max += 1`, `hp_curr = hp_max`
  - shadow desaparece
  - Continúa hacia el combate final con Jaffar

## Implementación

```python
def shadow_tick(game: Game) -> Game:
    if not game.shadow_state.initialized:
        return game

    shadow = find_char(game, charid_1_shadow)
    if shadow is None:
        return game

    if game.level.number == 4:
        # Corre hacia el oeste hasta desaparecer
        new_shadow = step_forward(shadow, direction=-1)
        if new_shadow.curr_col < 0:
            return remove_char(game, charid_1_shadow)
        return replace_char(game, charid_1_shadow, new_shadow)

    if game.level.number == 12:
        # Imita kid invertido
        kid = game.kid
        mirrored_cmd = mirror_horizontal(game.last_cmd)
        new_shadow = step_with_cmd(shadow, mirrored_cmd, game.level)
        # Detecta fusión
        if shares_cell(new_shadow, kid):
            new_kid = replace(kid, hp_max=kid.hp_max + 1, hp_curr=kid.hp_max + 1)
            new_game = remove_char(game, charid_1_shadow)
            return replace(new_game, kid=new_kid, shadow_state=replace(new_game.shadow_state, fused=True))
        return replace_char(game, charid_1_shadow, new_shadow)

    # ... resto de niveles
    return game
```

## Tests

- L4: cruzar mirror tile dispara shadow spawn
- L4: shadow corre west y se elimina
- L5: shadow steal marca potion consumida
- L12: shadow imita kid con mirror
- L12: tocar shadow fusiona y +1 HP

Estimación: 2 días.
