# `docs/design/07-guard-ai.md` — IA del guardia

## 1. Skill table

`NUM_GUARD_SKILLS = 12` (0..11). Cada nivel tiene un skill por defecto
en `guards_skill[24]`. Tabla canónica (reverso de SDLPoP):

```python
@dataclass(frozen=True)
class GuardSkill:
    prob_block: float       # 0..1 probabilidad de parry tras strike enemigo
    prob_strike_after_block: float
    refractory: int         # ticks de descanso tras un movimiento
    advance_chance: float   # prob de hacer advance vs idle

GUARD_SKILLS: tuple[GuardSkill, ...] = (
    GuardSkill(0.10, 0.20, 12, 0.10),  # skill 0: torpe
    GuardSkill(0.20, 0.30, 10, 0.20),
    GuardSkill(0.30, 0.40, 8,  0.30),
    GuardSkill(0.40, 0.50, 7,  0.40),
    GuardSkill(0.50, 0.55, 6,  0.50),
    GuardSkill(0.60, 0.60, 5,  0.55),  # skill 5: estándar
    GuardSkill(0.65, 0.70, 5,  0.60),
    GuardSkill(0.75, 0.75, 4,  0.65),
    GuardSkill(0.80, 0.80, 4,  0.70),
    GuardSkill(0.85, 0.85, 3,  0.75),
    GuardSkill(0.90, 0.90, 3,  0.80),
    GuardSkill(0.95, 0.95, 2,  0.90),  # skill 11: jaffar
)
```

> Valores ilustrativos — refinar tras dump exacto de SDLPoP.

## 2. Estados

```python
class GuardState(IntEnum):
    PATROL = 0
    ALERT = 1     # vio al kid, va hacia él
    COMBAT = 2    # dentro de rango de espada
    DEAD = 3
```

## 3. Decisión por tick

```python
def guard_tick(guard: Char, kid: Char, room: Room, rng: Rng) -> Char:
    if guard.alive >= 0:
        return guard  # muerto, no actúa

    skill = GUARD_SKILLS[guard.skill]

    # ¿Ve al kid?
    if same_room(guard, kid) and same_row(guard, kid):
        dist = abs(guard.curr_col - kid.curr_col)

        if dist <= 1:
            # COMBAT
            if is_strike_window(kid.frame):
                # Kid me va a golpear
                if rng.coin(skill.prob_block):
                    return start_seq(guard, SEQ_BLOCK)
                # No bloqueé — recibo daño en el resolver
                return guard
            # Mi turno: strike o advance
            if rng.coin(skill.advance_chance):
                return start_seq(guard, SEQ_58_GUARD_STRIKE)
            return guard

        if dist <= 6:
            # ALERT — avanza hacia el kid
            return advance_toward(guard, kid)

    # PATROL — anda hacia adelante hasta toparse con pared o borde
    return patrol(guard, room)
```

## 4. No cruza salas (default)

Los guards por defecto **no salen de su sala**. Hay un flag en
`guards_dir` que permite cross-room (raro, niveles avanzados).

## 5. Knockback

Tras recibir un strike no bloqueado, el guard hace `seq_84_run`
(retrocede unos tiles).

## 6. Tests

- skill 0 falla parry el 90% del tiempo
- skill 11 parry 95%
- guard ve kid a dist ≤ 6 → ALERT
- guard no cruza link de sala (default)
- patrol invierte dirección al toparse pared

Estimación: 2 días.
