# ADR 0007 — Físicas continuas como motor por defecto

## Contexto

Hasta v3.0 el motor era un FSM por celdas discretas: cada acción
duraba N ticks y al final saltaba a la celda siguiente. Esto convertía
al juego en "roguelike con disfraz de plataformas" — sin coyote time,
sin jump buffer, sin air control, sin colisión píxel-perfect. Los
niveles eran corredores horizontales porque la mecánica de celda no
premiaba la precisión.

`PhysicsPrince` con coordenadas continuas (`PositionF`, `Velocity`,
AABB) existía desde v2.0 como flag opt-in (`POP2026_PHYSICS_V2`) pero
nunca se promovió a default.

## Opciones consideradas

1. **Parche sobre el FSM discreto**: añadir coyote/buffer/var-jump
   pero mantener celdas. Resultado: sigue siendo discreto, sigue sin
   ser un platformer.
2. **Refactor profundo**: promover `PhysicsPrince` a único motor;
   reescribir combate, tile interactions, renderer; rediseñar
   niveles con verticalidad.
3. **Reescritura desde cero**: tirar todo y empezar otro motor.

## Decisión

**Opción 2 — Refactor profundo**.

Doce tareas atómicas R1-R12:

- R1 — constantes de game-feel (`COYOTE_TICKS`, `JUMP_BUFFER_TICKS`,
  `VAR_JUMP_CUT`, `GROUND_ACCEL`, `AIR_ACCEL`, `KNOCKBACK_*`,
  `SPIKE_LETHAL_VY`).
- R2 — `PhysicsPrince` con coyote + buffer + variable jump + air
  control + knockback. 5 tests dedicados.
- R3 — `Game.advance` usa `PhysicsPrince` por defecto;
  `StepResult.impact_vy` propaga la velocidad de aterrizaje para que
  los spikes sigan funcionando.
- R4 — combate continuo con distancia Euclídea y cono frontal de
  PARRY; knockback dirigido aplicado vía `with_damage(from_direction)`.
- R5 — tile interactions usan `prince.pos.to_cell()` (property
  derivada).
- R6 — reachability BFS ajustada a los nuevos rangos
  (`JUMP_REACH=4`, `MAX_FALL_DROP=8`).
- R7 — renderer dibuja al príncipe desde `body.pos.x/y` continuos.
- R8 — niveles L8 y L11 con plataformas intermedias (verticalidad).
- R9 — generador procedural mantiene la misma firma; los nuevos
  rangos de reachability lo cubren.
- R10 — demo bot usa `jump_held=True` para aprovechar variable jump.
- R11 — audio events siguen disparando con las acciones simbólicas
  del nuevo motor (sin cambios).
- R12 — docs + push.

## Consecuencias

**Positivas**

- Es un platformer 2D real con las cinco mecánicas no negociables.
- El combate gana profundidad: distancia Euclídea + parry direccional
  + knockback hacen que cada intercambio tenga peso.
- La arquitectura hexagonal aguantó: `PhysicsPrince` vive en
  `domain/`, `combat` y `renderer` solo cambiaron tipos.
- 301 tests verdes; `ruff format` + `ruff check` + `mypy --strict`
  limpios.

**Negativas**

- `domain/prince.py` (Prince discreto) queda como código muerto en
  runtime. Sus tests siguen pasando como referencia histórica pero
  no validan nada del motor real.
- `combat.py` y `renderer.py` usan
  `from pop2026.domain.physics_prince import PhysicsPrince as Prince`
  por simetría sintáctica. Cualquiera que abra esos ficheros tiene
  que saber que `Prince` es realmente `PhysicsPrince`.
- El demo bot necesita más sofisticación para superar niveles con
  verticalidad real (L4, L8, L11). Por ahora gana L1-L2 y los
  procedurales planos; los verticales son skill-checks humanos.

## Alternativas para v5.0

- Borrar definitivamente `domain/prince.py` y sus tests (R12 lo
  pospone porque no son críticos y eliminarlos no aporta valor
  inmediato).
- Implementar pathfinding A* en el demo bot.
- Niveles L1-L7 con verticalidad real (hoy son corredores).
- Sub-tick physics para evitar tunneling a velocidades altas.
