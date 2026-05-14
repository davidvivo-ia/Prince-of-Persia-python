# PLAN.md — Híbrido pragmático v4.1

> Mantiene el motor v4.0 (física continua) y suma las piezas que más
> acercan al feel POP1, sin reescribir el motor.
>
> **Decisiones de producto** confirmadas:
> 1. Combate gana ADVANCE/RETREAT como acciones discretas.
> 2. Mirror/clone guard aparece en un nivel.
> 3. Niveles multi-pantalla son la norma, no la excepción.
> 4. CAMPAIGN sube de 12 a 15 (alinea con LEVEL0..LEVEL14 del original).

## Asunciones declaradas (CLAUDE.md §1)

A1. **No tocamos el integrador físico** (R2 v4.0). Las nuevas acciones
    se mapean a impulsos discretos del propio integrador.

A2. **No replicamos los 200+ frames rotoscopiados** del original. La
    animación nueva sigue siendo `JointPose`+`Keyframe` interpolado.

A3. **Mirror guard es un único nivel especial**, no una mecánica
    recurrente — homenaje al "shadow" del original sin convertirlo en
    sistema.

A4. **15 niveles** = los 12 actuales + L00 "intro/tutorial" + L13
    "shadow" + L14 "escape" (que sustituye al actual `12_jaffar`
    moviendo el visir al 14).

## Decisiones que necesito antes de ejecutar

D1. **Implementación de ADVANCE/RETREAT**:

   - (a) **Acciones discretas con animación propia**: dos nuevos
     `Action.ADVANCE` y `Action.RETREAT` que aplican un impulso de
     0.5 celdas hacia adelante/atrás cuando hay sable empuñado y
     guardia adyacente. Bind a `LEFT`/`RIGHT` mientras `has_sword`
     y `_guard_adjacent`. Más auténtico. **Recomendado**.
   - (b) **Modifier sobre RUN**: cuando hay guardia adyacente, el RUN
     normal pasa a ser micro-paso (0.5 celdas). Sin acciones nuevas.
     Más simple pero pierde la dualidad explícita.

D2. **Nivel del Mirror**:

   - (a) **Mirror es nivel 13 — "Sombra"**: aparece un guard especial
     que copia los inputs del jugador con espejo (LEFT↔RIGHT). Un
     único nivel. Tras vencerlo, sigue al 14. **Recomendado**.
   - (b) **Mirror es jefe final (L15 nuevo)**: empuja la estructura
     a 15+1 niveles, más invasivo.

Si dices "decide tú": (a)+(a).

---

## Bloque H — Híbrido

### H1 · `Action.ADVANCE` / `Action.RETREAT`
- **Archivos**: `domain/actions.py`, `domain/physics_prince.py`,
  `domain/combat.py`, `domain/poses.py`, `presentation/input_device.py`,
  `tests/unit/test_combat.py`, `tests/unit/test_physics_prince.py`.
- **Hago**:
  - Añadir `Action.ADVANCE = 16`, `Action.RETREAT = 17` con
    `duration_ticks = 8`.
  - En `physics_prince._decide_action`: si `has_sword` y hay guardia
    adyacente (a determinar) y cmd es `LEFT`/`RIGHT`, devolver
    `ADVANCE`/`RETREAT` en lugar de `RUN/WALK`.
  - Impulso de 0.5 celdas en la dirección durante los ticks 2-4 de
    la animación.
  - Combat: durante ADVANCE/RETREAT el príncipe sigue siendo
    "intercambiable" (puede recibir golpes pero no ataca).
- **DoD**:
  - `test_advance_moves_half_cell_forward`.
  - `test_retreat_moves_half_cell_back`.
  - `test_advance_only_triggers_with_sword_and_guard_near`.
  - Render preview de la nueva pose.
- **Estimado**: 75 min.

### H2 · Mirror guard
- **Archivos**: `domain/guard.py`, `domain/tiles.py`,
  `application/level_generator.py` (no), `infrastructure/builtin_levels/13_shadow.poplv`,
  `tests/unit/test_guard.py`.
- **Hago**:
  - Añadir `Tile.SPAWN_MIRROR = 15`, carácter `'M'` (ojo: ya está
    para POTION_MAXHP. Uso `'m'` minúscula).
  - `Guard.is_mirror: bool`. Cuando `True`, en `guard.step` el AI
    copia los inputs del prince **espejados horizontalmente**.
  - Necesita acceso a `inp` del prince → cambio de signatura de
    `guard.step` o callback desde `game.advance`.
  - Diseñar L13: un cuarto con el prince y un mirror.
- **DoD**:
  - `test_mirror_guard_copies_prince_input_mirrored`.
  - L13 cargable y reachable.
- **Estimado**: 90 min.

### H3 · Multi-pantalla por defecto (40 cols)
- **Archivos**: `application/level_generator.py`,
  `presentation/theme.py`, `presentation/renderer.py`.
- **Hago**:
  - `level_generator.NARROW_COLS = 40` (era 20). `WIDE_COLS = 60`.
  - Todos los niveles built-in se reescalan a 40 columnas.
  - El renderer ya tiene cámara room-flick (T11 de v3); se conserva.
- **DoD**:
  - Cada nivel built-in `.poplv` tiene 40 columnas como mínimo.
  - Tests de `test_level_generator` pasan con la nueva anchura.
  - Demo bot termina L1 en frames razonables.
- **Estimado**: 60 min (sobre todo edición de .poplv).

### H4 · CAMPAIGN a 15
- **Archivos**: `application/campaign.py`, dos nuevos `.poplv`
  (`00_intro.poplv`, `14_escape.poplv`), renombrar `12_jaffar.poplv`
  → `14_jaffar.poplv` y crear nuevo `12_*.poplv` intermedio.
  Decisión más simple: `_HAND_CRAFTED` sube de 12 a 15 entradas;
  el resto procedural igual.
- **Hago**:
  - L00 "El Despertar" — tutorial sencillísimo.
  - L13 "La Sombra" — del H2.
  - L14 "El Visir" — versión expandida del 12 antiguo.
  - Total levels = 100 sigue (los procedurales bajan de 88 a 85).
- **DoD**:
  - `test_campaign_has_100_entries` sigue verde.
  - L00, L13, L14 cargan y son reachable.
- **Estimado**: 45 min.

### H5 · Quality gates + push
- **Hago**: ruff format/check, mypy strict, pytest, push.
- **Estimado**: 15 min.

---

## Tiempo total estimado

| Tarea | min |
|---|---|
| H1 ADVANCE/RETREAT | 75 |
| H2 Mirror guard | 90 |
| H3 Multi-pantalla default | 60 |
| H4 CAMPAIGN 15 | 45 |
| H5 audit + push | 15 |
| **Total** | **~285 min ≈ 5h** |

## Criterios de "hecho" para v4.1

- [ ] `Action.ADVANCE`/`RETREAT` con tests dedicados verdes.
- [ ] Mirror guard implementado y nivel 13 jugable.
- [ ] Todos los niveles hand-crafted ≥ 40 columnas.
- [ ] CAMPAIGN tiene 100 entradas con L00, L13, L14 añadidos.
- [ ] `pytest` ≥ 301 verdes (probablemente subirá a ~315).
- [ ] ruff format + check + mypy --strict limpios.
- [ ] CHANGELOG y plan.md actualizados.

---

*Pendiente: tus D1 y D2. No empiezo hasta tu OK.*
