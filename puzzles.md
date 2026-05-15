# puzzles.md — Diseño de puzzles para los 15 niveles

> Inspirado en la **mecánica** de los niveles del Prince of Persia
> original (1989, J. Mechner). No copio ningún layout concreto del
> material original — cada nivel aquí es **diseño propio** que recrea
> la **idea de puzzle** del juego clásico con las primitivas que
> nuestro motor 2026 soporta: `FLOOR`, `LOOSE_FLOOR`, `SPIKES`,
> `GATE`, `PRESSURE`, pociones, `SWORD`, guardias, jefe, esqueleto
> y el clon-espejo.
>
> **Anchura fija**: 40 columnas (2 "salas" de 20 cols con room-flick).
> **Altura fija**: 6 filas.
> **Convención de filas**:
> - row 0: techo (FLOOR)
> - row 1-2: aire (decoración / techo bajo)
> - row 3: fila del príncipe (camino principal)
> - row 4: suelo principal (FLOOR / LOOSE_FLOOR / gaps)
> - row 5: base (FLOOR — atrapa caídas)

## Doctrina general

1. **Cada nivel introduce o combina una mecánica nueva.** No se
   añaden 5 cosas en un mismo nivel — el jugador entiende el sistema
   poco a poco.
2. **Las dos salas se usan**: la solución del puzzle suele requerir
   pasar por la primera para preparar algo de la segunda (placa de
   presión, recogida de poción, recogida de espada).
3. **Reachability garantizada por BFS** (`tests/unit/test_reachability`).
4. **El demo bot completa los 10 niveles "fáciles"** (sin RNG de
   combate) en ≤ 12 000 ticks (`tests/integration/test_demo_bot_wins`).
5. **Los niveles de combate** (`03`, `07`, `10`, `11`, `14`) son
   RNG-dependientes para el bot pero **siempre completables por un
   humano** con timing.

---

## L01 · La Celda — *El despertar* — *Tutorial sin obstáculos*

**Inspiración POP1**: el nivel de la celda. Despiertas, no tienes
sable, sólo hay que caminar y entender los controles.

**Puzzle**: ninguno. **Skill**: caminar.

**Layout**:
- Sala 1: prince en col 2, corredor abierto.
- Sala 2: corredor abierto que termina en EXIT.

**Solución**: caminar derecha hasta el exit.

---

## L02 · El Sable — *La hoja olvidada*

**Inspiración POP1**: encuentras una espada tirada en el suelo y
descubres que servirá para los guardias siguientes.

**Puzzle**: pasar por encima del sable para recogerlo
(auto-pickup). **Skill**: caminar.

**Layout**:
- Sala 1: prince → sable (`S`) → corredor.
- Sala 2: corredor abierto → EXIT.

---

## L03 · El Guardia — *Primer combate*

**Inspiración POP1**: el primer guardia que sale a por ti. Sin
espada estás muerto.

**Puzzle**: recoger sable en sala 1, derrotar al guardia que custodia
la sala 2. **Skill**: combate (STRIKE / PARRY / ADVANCE).

**Layout**:
- Sala 1: prince → sable.
- Sala 2: guardia → EXIT.

---

## L04 · Pinchos y Poción — *El suelo te quiere y no te quiere*

**Inspiración POP1**: trampas de pinchos + brebajes de curación.

**Puzzle**: saltar sobre pinchos. Si tomas daño, hay una poción
verde en el camino para curarte. **Skill**: salto direccional
(`RIGHT` + `JUMP`).

**Layout**:
- Sala 1: prince → poción + ^ ^ (dos pinchos en serie).
- Sala 2: ^ ^ ^ (tres pinchos) → EXIT.

---

## L05 · La Placa — *Llave por presión*

**Inspiración POP1**: pisar una baldosa para abrir una reja.

**Puzzle**: la primera placa (`_`) abre la reja siguiente (`|`).
La segunda placa abre la segunda reja. **Skill**: identificar las
parejas placa-gate.

**Layout**:
- Sala 1: prince → placa_1 → gate_1.
- Sala 2: placa_2 → gate_2 → EXIT.

**Bot-solvable**: las placas están EN el camino directo.

---

## L06 · Ladrillos Sueltos — *Lo que parece firme*

**Inspiración POP1**: suelos sueltos que ceden bajo tus pies.

**Puzzle**: caminar sobre suelos sueltos te hace caer al piso de
abajo (row 5, también FLOOR — sobrevives). Hay que aceptar la
caída y seguir desde abajo. **Skill**: aceptar la caída.

**Layout**:
- Sala 1: prince + poción heal (`+`) → 4 loose floors (`=`).
- Sala 2: 5 loose floors → EXIT.

---

## L07 · Dos Hierros — *Dúo*

**Inspiración POP1**: dos guardias en secuencia, una poción en
medio.

**Puzzle**: combate doble con curación intermedia. **Skill**:
combate + gestión de HP.

**Layout**:
- Sala 1: sable → guardia 1.
- Sala 2: poción heal → guardia 2 → EXIT.

---

## L08 · La Cornisa — *Salto con carrerilla*

**Inspiración POP1**: secciones donde necesitas saltar un foso
sin caer en pinchos.

**Puzzle**: foso de pinchos en sala 2 que sólo se cruza con
running jump (RIGHT + JUMP simultáneo). Plataforma decorativa
arriba sugiere la trayectoria. **Skill**: running jump.

**Layout**:
- Sala 1: corredor + plataformas decorativas arriba.
- Sala 2: foso de pinchos → EXIT.

---

## L09 · Reja y Trampa — *Cuatro puertas, cuatro placas*

**Inspiración POP1**: maze con múltiples placas/rejas
encadenadas.

**Puzzle**: 4 parejas placa-gate alternadas. Cada placa abre la
gate más cercana. **Skill**: paciencia, leer el mapa.

**Layout**:
- Sala 1: placa_1 → gate_1 → poción → placa_2 → gate_2.
- Sala 2: placa_3 → gate_3 → poción → placa_4 → gate_4 → EXIT.

---

## L10 · La Patrulla — *Tres centinelas*

**Inspiración POP1**: niveles avanzados con varios guardias
patrullando.

**Puzzle**: combate múltiple con HP limitado. **Skill**: timing.

**Layout**: sable → guardia × 3 espaciados → EXIT.

---

## L11 · Camino de Pinchos — *La hilera*

**Inspiración POP1**: gauntlet de pinchos.

**Puzzle**: pinchos espaciados a 7 cols permiten un running jump
de cada uno. **Skill**: salto rítmico.

**Layout**: prince → 4 pinchos espaciados → EXIT.

---

## L12 · El Visir — *Antesala*

**Inspiración POP1**: cámara antesala con plate + gate antes del
jefe.

**Puzzle**: la placa de sala 1 abre la gate de sala 2; tras la
gate hay un guardia jefe (`G`, skill=2) que custodia el exit.
**Skill**: navegación + combate jefe.

**Layout**:
- Sala 1: prince → sable → placa → corredor.
- Sala 2: gate → boss → EXIT.

---

## L13 · La Sombra — *Espejo*

**Inspiración POP1**: el nivel 12 del original donde tu sombra
te imita.

**Puzzle**: el clon-espejo (`m`) copia tus inputs invertidos
horizontalmente. Recoge sable, derrótalo. **Skill**: combate
contra IA-espejo.

**Layout**:
- Sala 1: prince → sable.
- Sala 2: mirror guard → EXIT.

---

## L14 · El Trono — *Salón ceremonial*

**Inspiración POP1**: el salón del visir con trampas y guardias.

**Puzzle**: sala 1 tiene sable + placa que abre gate de sala 2.
Sala 2 tiene boss + poción de max HP escondida tras la gate.
**Skill**: navegación + boss.

**Layout**:
- Sala 1: prince → sable → placa → corredor.
- Sala 2: gate → poción max-hp → boss → EXIT.

---

## L15 · La Huida — *Carrera final*

**Inspiración POP1**: el escape final cronometrado.

**Puzzle**: gauntlet completo: spike + guardia + spike + boss.
**Skill**: todo lo aprendido.

**Layout**:
- Sala 1: prince → sable → ^ → guardia → ^.
- Sala 2: poción heal → guardia → boss → EXIT.
