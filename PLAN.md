# PLAN.md — Refactor a platformer real

> Sustituye al PLAN anterior. Objetivo: el juego se siente como un
> platformer 2D moderno (Celeste/Hollow Knight tier de "game feel"),
> no como un roguelike por celdas.

## Diagnóstico del problema actual

- `Prince` (discreto, FSM por celdas) es el motor por defecto.
- `PhysicsPrince` con `(x, y)` float existe pero está como feature
  flag opt-in y nunca se promovió.
- Niveles son corredores horizontales planos: la mecánica de celda
  no premia precisión, así que nadie los diseñó verticales.
- Faltan los "10 mandamientos" del platformer 2026: coyote time,
  jump buffer, variable jump, air control, knockback, AABB
  pixel-perfect, animaciones con keyframes reales.

## Asunciones declaradas (CLAUDE.md §1)

A1. **Promovemos PhysicsPrince a motor único** y eliminamos el FSM
    discreto de `prince.step`. El módulo discreto se queda como
    archivo deprecated durante el refactor, se borra en R12.

A2. **Guard sigue siendo discreto** (`Position` int row/col) por
    ahora. Razón: la IA del guardia es por casillas y el coste de
    portarla a continuo es alto sin beneficio claro. El renderer
    interpolará visualmente. Si quieres guard continuo también, lo
    digo en R4 como variante.

A3. **Tile size de colisión = 1.0**. El AABB del príncipe es
    aproximadamente `0.55 × 0.90` celdas. La velocidad máxima por
    tick es < 0.5 celdas para evitar tunneling.

A4. **El reloj de juego sigue per-level** (decisión v3.0 que no
    cambia).

A5. **Pygame-ce sigue como capa de presentación**. No tocamos eso.

## Decisiones que necesito confirmar antes de ejecutar

D1. **¿Combate continuo o por celdas?**

   - (a) Combate sigue siendo "adyacencia por celda" — el príncipe
     calcula su celda derivada (`pos.to_cell()`) y reusa la lógica
     actual de hit windows + reach. Bajo riesgo. **Recomendado**.
   - (b) Combate también pasa a continuo: alcance por distancia
     Euclídea, parry como cono frontal. Más auténtico pero +3 h.

D2. **¿Wall jumps?**

   - (a) **No**. Más simple y fiel al POP original.
   - (b) Sí: el príncipe rebota de paredes verticales con dirección
     opuesta. Daría verticalidad extra pero rompe el espíritu del
     original.

   *Mi recomendación: (a).*

Cuando me digas D1 y D2 arranco. Si dices "decide tú" tomo
(a)+(a) por defecto.

---

## Bloque R — Refactor a platformer

### R1 · Constantes de game-feel
- **Archivos**: `src/pop2026/domain/physics.py`.
- **Hago**: añadir `COYOTE_TICKS=6`, `JUMP_BUFFER_TICKS=6`,
  `VAR_JUMP_CUT=0.5`, `AIR_ACCEL=0.025`, `GROUND_ACCEL=0.10`,
  `MAX_FALL_VEL=0.45`, ajustar `JUMP_VEL` a `-0.42`.
- **DoD**: módulo importa, constantes son ≥0 y mutuamente coherentes
  (test rápido).
- **Estimado**: 5 min.

### R2 · PhysicsPrince con game-feel completo
- **Archivos**: `src/pop2026/domain/physics_prince.py`,
  `tests/unit/test_physics_prince.py`.
- **Hago**: añadir a `PhysicsPrince` y `step()`:
  - `coyote_ticks_left` se resetea al estar grounded; permite saltar
    durante `COYOTE_TICKS` después de salir de plataforma.
  - `jump_buffer_ticks_left` se setea al pulsar JUMP; consume al
    aterrizar si > 0.
  - `jump_held: bool` permite *variable jump*: si se suelta JUMP y
    `vy < 0`, multiplicar `vy *= VAR_JUMP_CUT`.
  - `air_control`: si no grounded, `accel_x` reducido a `AIR_ACCEL`.
  - `knockback(direction)`: setea `vel.vx` con magnitud fija opuesta
    al atacante; bloquea control durante `KNOCKBACK_TICKS=10`.
- **DoD**: tests:
  - `test_coyote_allows_jump_after_leaving_ledge`.
  - `test_jump_buffer_consumed_on_landing`.
  - `test_releasing_jump_cuts_height`.
  - `test_air_control_weaker_than_ground`.
  - `test_knockback_blocks_input`.
- **Estimado**: 75 min.

### R3 · Game.advance usa PhysicsPrince por defecto
- **Archivos**: `src/pop2026/domain/game.py`,
  `src/pop2026/domain/prince.py` (deprecation),
  `tests/unit/test_game.py`.
- **Hago**:
  - `Game.prince: PhysicsPrince` (cambio de tipo).
  - `new_game(level)` construye `PhysicsPrince` con `initial(spawn)`.
  - `advance()` llama a `physics_prince.step` en lugar de
    `prince.step`.
  - `prince.py` queda como módulo deprecated con docstring que
    explica el reemplazo. Los tests viejos (`test_prince.py`,
    `test_hang.py`) se marcan `@pytest.mark.skip(reason="discrete
    prince deprecated; superseded by physics_prince")` con plan de
    borrar en R12.
  - Flag `POP2026_PHYSICS_V2` desaparece (físicas son default).
- **DoD**:
  - `test_game_advance_uses_continuous_position`.
  - Demo bot pasa nivel 1 (hand-crafted, simple).
- **Estimado**: 90 min.

### R4 · Combate continuo-vs-celda (depende de D1)
- **Si D1=(a)**: minimal — `Combat._adjacent` recibe el príncipe
  continuo y deriva celda con `pos.to_cell()`. Resto idéntico. ~15
  min.
- **Si D1=(b)**: rewrite — alcance Euclídeo, parry como cono frontal
  60°. ~3 h. Tests nuevos.

### R5 · Tile interactions continuo
- **Archivos**: `src/pop2026/domain/game.py`,
  `src/pop2026/domain/level.py`.
- **Hago**: `_process_tile_interactions` lee `prince.pos.to_cell()`
  para resolver qué tile pisa. Placa, pociones, exit, spikes:
  todos por celda derivada. Spikes letales si `vel.vy >
  SPIKE_LETHAL_VY=0.3`.
- **DoD**: tests para cada interacción.
- **Estimado**: 30 min.

### R6 · Reachability ajustada a físicas reales
- **Archivos**: `src/pop2026/domain/reachability.py`,
  `tests/unit/test_reachability.py`.
- **Hago**: recalcular `JUMP_REACH` y `MAX_FALL_DROP` a partir de
  las constantes nuevas. Una parabola con `JUMP_VEL=-0.42` y
  gravedad alcanza ~3 celdas horizontales. Ajustar.
- **DoD**: tests pasan con los nuevos rangos.
- **Estimado**: 20 min.

### R7 · Renderer lee `pos.x/pos.y` directos
- **Archivos**: `src/pop2026/presentation/renderer.py`.
- **Hago**:
  - `_smooth_feet(prince)` ahora hace
    `feet_x = prince.pos.x * tile_w`, `feet_y = (prince.pos.y +
    half_h) * tile_h + hud_top`. No anim offset (la posición YA es
    continua).
  - Mantener anim offset solo para guards (siguen discretos).
  - Eliminar las llamadas a `offset_for(action, ticks)` para el
    príncipe; sustituir por `poses.interpolate(action, phase)` con
    `phase = ticks_in_action / duration_ticks(action)`.
- **DoD**: render headless de cualquier estado no peta; preview
  manual ok.
- **Estimado**: 45 min.

### R8 · Niveles hand-crafted con verticalidad real
- **Archivos**: `src/pop2026/infrastructure/builtin_levels/*.poplv`.
- **Hago**: rediseñar los 12 niveles con plataformas a alturas
  variadas. Cada nivel introduce o repite una mecánica:
  1. Tutorial: caminar, exit. Plano.
  2. Sable: pickup en plataforma elevada (debe trepar).
  3. Guardia: en plataforma intermedia, baja con drop.
  4. Pinchos: gaps con pinchos abajo, debe saltar.
  5. Placa+gate: placa en plataforma alta, gate arriba.
  6. Suelos sueltos: cadena de plataformas que caen.
  7. Dos guardias: en plataformas distintas, secuencia.
  8. Trepar: ascenso vertical, mezcla de saltos y climbs.
  9. Maze: laberinto vertical con backtrack.
  10. Patrulla larga: corredor de 40 celdas con plataformas.
  11. Pinchos forest: precisión de salto, sin red.
  12. Visir: arena vertical, plataforma central, jefe.
- **DoD**: cada nivel pasa el demo bot con seed=42 en <8000 frames,
  excepto los conocidos human-only (3, 7, 10, 12).
- **Estimado**: 90 min.

### R9 · Generador procedural rediseñado
- **Archivos**: `src/pop2026/application/level_generator.py`,
  tests.
- **Hago**: layout con 2-3 plataformas a distintas alturas,
  conectadas por saltos o caídas controladas. Reachability sigue
  validando.
- **DoD**: property test `every_generated_level_is_reachable`
  sigue verde (puede requerir relajar parámetros).
- **Estimado**: 60 min.

### R10 · Demo bot adaptado a físicas continuas
- **Archivos**: `src/pop2026/application/demo_player.py`.
- **Hago**: el bot vuelve a leer `pos.to_cell()` para decidir.
  JUMP_R desaparece, se reemplaza por mantener `RIGHT + JUMP`. Air
  control implícito.
- **DoD**: bot pasa niveles 1-2 hand-crafted.
- **Estimado**: 45 min.

### R11 · Audio transitions actualizado
- **Archivos**: `src/pop2026/presentation/audio.py`.
- **Hago**: detectar saltos, aterrizajes, golpes en el nuevo
  modelo (transición de action symbol, igual que antes). Adaptar.
- **DoD**: SFX se disparan en eventos.
- **Estimado**: 15 min.

### R12 · Limpieza + tests viejos + docs
- **Archivos**: `prince.py` discreto borrado; tests `test_prince.py`
  y `test_hang.py` migrados o borrados; `physics_prince` renombrado
  a `prince`.
- **Hago**: limpieza final, CHANGELOG v4.0.0, ADR 0007, postmortem
  actualizado.
- **DoD**: gates verdes, demo bot pasa muestra representativa, push.
- **Estimado**: 45 min.

---

## Tiempo total y dependencias

```
R1 ─→ R2 ─→ R3 ─→ R4 ─→ R5 ─→ R6
                       ↓
                       R7 ←→ R8 ─→ R10
                                  ↓
                                  R11 ─→ R12
```

- **Serie**: ~9 h.
- **Paralelizable (R7, R8, R9 después de R3-R6)**: ~6 h.

## Criterios de "hecho" para v4.0

- [ ] `prince` antiguo borrado.
- [ ] `Game.prince` es `PhysicsPrince`.
- [ ] Coyote time + jump buffer + variable jump funcionan
      (tests dedicados).
- [ ] Renderer dibuja sin anim offset para el príncipe.
- [ ] Los 12 niveles hand-crafted tienen al menos 2 alturas
      diferentes.
- [ ] Demo bot pasa muestra (1, 13, 26, 51, 76).
- [ ] 290+ tests verdes, cobertura dominio ≥ 90%.
- [ ] CHANGELOG, README, ADR 0007 actualizados.

---

*Pendiente: tu D1 y D2.*
