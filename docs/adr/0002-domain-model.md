# ADR 0002 — Modelo de dominio: dataclasses frozen + FSM explícita

## Contexto

El comportamiento del príncipe y los guardias en el original son
máquinas de estados con transiciones disparadas por (input + colisión +
tick). En 6502 estas FSMs eran tablas de saltos por offset.

## Opciones

1. **Estado como string + funciones libres**: simple pero invita a la
   "stringly typed" plague.
2. **Estado como `IntEnum` + diccionario de transiciones**: explícito y
   serializable.
3. **OOP State pattern (clases por estado)**: idiomático en libros
   antiguos pero sobreingeniería aquí.
4. **`pydantic` para entidades**: validación gratis pero coste de
   construcción y mutabilidad por defecto.

## Decisión

- **Estados**: `IntEnum` (`Action`, `CombatStance`, `GuardMode`).
- **Entidades**: `@dataclass(frozen=True, slots=True)` (`Prince`,
  `Guard`, `Tile`, `Level`).
- **Transiciones**: funciones puras `(state, input, world) → state` en
  módulos del dominio.
- **Pydantic v2** se reserva a fronteras IO (`SaveGame`, configuración
  CLI).

## Consecuencias

- **+** Dominio testeable sin pygame ni filesystem.
- **+** Inmutabilidad → debugging y replay triviales (clonar es libre).
- **−** Cada paso genera un objeto nuevo. Para 60 fps con ~10 entidades
  es despreciable.
