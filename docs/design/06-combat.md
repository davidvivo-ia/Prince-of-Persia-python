# `docs/design/06-combat.md` — Combate cuerpo a cuerpo

## 1. HP

```python
START_HITP = 3
MAX_HITP_ALLOWED = 10
TBL_GUARD_HP = (4, 3, 3, 3, 3, 4, 5, 4, 4, 5, 5, 5, 4, 6, 0, 0)
                # nivel 1..14 (15-16 = sentinelas)
```

`take_hp(char, amount)` resta y devuelve False si murió (`hp_curr <= 0`).

## 2. Secuencias de combate

(De `seqtbl.c`, validadas en audit.)

| Acción | Seq id | Frames | Notas |
|---|---|---|---|
| Draw sword | `seq_55_draw_sword` | 207-210 | Tras shift+up |
| Engarde | `seq_57_engarde` | ~150-156 | Postura de combate |
| Ready | (continuación) | 156-160 | Idle con espada |
| Strike (kid) | `seq_75_strike` | 165-170 | Golpe principal |
| Strike (guard) | `seq_58_guard_strike` | (guard frames) | Golpe del guard |
| Block | `seq_61_blocktostrike` | 161-164 | Parry → strike |
| Blocked strike | `seq_blockedstrike` | — | Tras parry exitoso |
| Advance | `seq_advance` | — | Micro-paso adelante |
| Retreat | `seq_retreat` | — | Micro-paso atrás |
| Sheathe | `seq_64_sheathe` | 230-240 | Guardar espada |

## 3. Resolución

Cada tick, si ambos chars tienen sword drawn y comparten room/row,
en distancia 1-2 cols:

```python
def resolve_combat(kid: Char, guard: Char) -> tuple[Char, Char]:
    # Detección de ventanas de impacto del frame
    kid_window = is_strike_window(kid.frame)
    guard_window = is_strike_window(guard.frame)
    kid_blocking = is_block_window(kid.frame)
    guard_blocking = is_block_window(guard.frame)

    new_kid, new_guard = kid, guard

    # Kid golpea
    if kid_window and not guard_blocking and adjacent(kid, guard):
        new_guard = take_hp(guard, 1)
        if not new_guard.alive >= 0:
            new_guard = play_seq(new_guard, SEQ_85_STABBED_TO_DEATH)

    # Guard golpea
    if guard_window and not kid_blocking and adjacent(guard, kid):
        new_kid = take_hp(kid, 1)
        if not new_kid.alive >= 0:
            new_kid = play_seq(new_kid, SEQ_85_STABBED_TO_DEATH)

    return new_kid, new_guard
```

## 4. Ventanas (frame ranges canónicos)

Aproximadas — extracción exacta de SDLPoP en implementación:

```python
STRIKE_FRAMES = {153, 154, 155}  # ventana de impacto del strike
BLOCK_FRAMES = {158, 159, 160, 161}  # ventana de bloqueo
```

(Valores ilustrativos.)

## 5. Tests

- `take_hp(char, 1)` baja hp y mantiene alive si > 0
- `take_hp` con hp=1 dispara `alive >= 0` (muerto)
- 3 strikes consecutivos al guard nivel 1 (hp=4) requieren 4 hits, no 3
- Parry en frame de block evita daño

Estimación: 2 días.
