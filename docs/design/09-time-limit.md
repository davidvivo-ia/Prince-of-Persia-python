# `docs/design/09-time-limit.md` — Tiempo límite

## Constantes canónicas

```python
START_MINUTES_LEFT = 60
START_TICKS_LEFT = 719   # ticks fraccionarios primer minuto
TICKS_PER_MINUTE = 720
```

A 12 FPS lógicos, 720 ticks = 60s. 60 minutos = 43 200 ticks.

## Modelo

```python
@dataclass(frozen=True)
class TimeState:
    minutes_left: int = 60
    ticks_left: int = 719   # decrementa cada tick lógico
```

## Decremento

```python
def tick_time(time: TimeState) -> TimeState:
    if time.minutes_left <= 0:
        return time
    if time.ticks_left > 0:
        return replace(time, ticks_left=time.ticks_left - 1)
    return TimeState(minutes_left=time.minutes_left - 1, ticks_left=719)
```

## Game over por timeout

Si `minutes_left == 0 and ticks_left == 0`:
- Game state → `LOST_TIMEOUT`
- Cinemática: "La princesa muere"
- (Canon: en realidad muestra "Time's up. Princess dies." y fin)

## Display

HUD muestra `minutes_left` solo cuando:
- El jugador pulsa una tecla concreta (tab o L1)
- O al beber una `time_potion` (+30s = +6 ticks de minuto)

En cualquier otro momento, no se muestra (intencionalmente — para
crear tensión).

## Time potions

`tiles_10_potion` con modifier "time":
- `minutes_left = min(60, minutes_left + 30 / 60)`  → +0.5 min
- (Canon: +30s exactos según comunidad)

## Tests

- decrement avanza 720 ticks per minuto
- minutes=0 ticks=0 → game over timeout
- time potion suma 30s, no excede 60 min

Estimación: 1 día.
