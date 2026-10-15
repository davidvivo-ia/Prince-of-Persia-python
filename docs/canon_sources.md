# Fuentes canon estudiadas y qué adoptamos de cada una

Análisis comparativo (jul-2026) de los repositorios de referencia del
POP1 frente a este motor (`pop2026canon`). Ordenados de más canónico a
más derivado.

## 1. `jmechner/Prince-of-Persia-Apple-II` (el original)

Ensamblador 6502 del Apple II (1985-89), subido por Jordan Mechner en
2012. Incluye la documentación de 1989 para los equipos de porting.
*Source-available* (estudio/modificación permitidos), **sin** derechos
sobre la franquicia (Ubisoft). Para nosotros es la referencia histórica
y la documentación de diseño; el código 6502 no es fuente práctica de
constantes (la versión DOS difiere en timings).

## 2. `NagyD/SDLPoP` (el filón)

Port C open source del **desensamblado de la versión DOS** — la lógica
completa y legible: colisiones, timers, IA de guardias, física. Es
nuestra fuente primaria de *hechos mecánicos* (valores numéricos y
formatos, reimplementados aquí desde cero en Python):

| Hecho | Fuente SDLPoP | Estado en pop2026canon |
|---|---|---|
| Tabla de skills de guard 0..11 (strike/restrike/block/impblock/advance /255, refractory, extrastrength) | `seg002.c` | ✅ adoptada tal cual (`GUARD_SKILLS`) |
| Umbrales de caída: `fall_y` <22 suave, <33 −1HP, ≥33 mortal | `seg005.c::land` | ✅ equivalente por distancia (nuestro tick acumula celdas; calibrado a 1 piso seguro / 2 daño / 3 muerte) |
| `tile_is_floor`: TODO es suelo salvo EMPTY, BIGPILLAR_TOP, DOORTOP y celosías | `seg006.c` | ✅ adoptado en `tiles.SOLID` |
| HP de guard por nivel + extrastrength | `data.h` | ✅ (`TBL_GUARD_HP` + `extra_hp`) |
| Formato binario de nivel (2305 B) y encoding de doorlinks | `types.h`, `seg007.c` | ✅ importador propio (`infrastructure/levels_dat.py`) |
| `start_dir` guardado invertido (`direction = ~start_dir`) | `seg003.c` | ✅ |
| Modifiers de potion del DAT (3=feather, 5=poison) ≠ nuestro enum | `types.h` | ✅ remapeados al importar |
| Gates: abren rápido, bajan lento y aceleran | `seg007.c` | ~ aproximado (0..140, abre 7 ticks, cierra 140) |

## 3. Los demás

- **`adamgreen/Prince-of-Persia-Apple-II`**: fork que sí ensambla
  (toolchain Merlin moderno). Relevante sólo para arqueología.
- **`oklemenz/PrinceJS`**: mecánicas en alto nivel (JS/Phaser); útil
  como segunda opinión de comportamiento, no de constantes.
- **`oitofelix/mininim`**: motor desde cero (C+Lua) con editor — la
  referencia de "motor moderno con niveles canon", análoga a lo nuestro.
- **`VictorBusque/prince-of-persia-1989`** (C++/OpenGL, ya estudiado):
  de aquí adoptamos el principio del *mapa continuo* (los grids 2D de
  `levels_canon.py` y el carver de huecos verticales).

## Diferencias deliberadas de nuestro motor

1. **Fila del personaje**: en SDLPoP el char *ocupa* la fila del tile
   que pisa (por eso `check_spiked` lee el tile en la posición del
   char). Nuestro motor sitúa al char una fila POR ENCIMA del tile que
   lo soporta. Compensación: las interacciones (plates, potions, sword,
   spikes, chompers, exit door) comprueban la celda propia **y la de
   debajo** (`tick.py`).
2. **Daño por caída**: medimos distancia acumulada (`fall_dist`) en vez
   de velocidad — con nuestra geometría de celdas la velocidad satura
   antes de poder distinguir 2 de 3 pisos. Umbrales calibrados al mismo
   resultado jugable que el canon.
3. **Niveles**: los 14 niveles del repo son *fan-recreation* (no
   distribuimos datos de Ubisoft) y están verificados completables por
   el bot A* (`test_completability.py`). Con `--levels-dat` se cargan
   los niveles ORIGINALES desde una copia propia del juego.

## Estado del importador de niveles originales

`pop2026canon --levels-dat <LEVELS.DAT | dir res20NN.bin>`.

Verificado localmente contra los 14 niveles de la versión DOS: la
estructura decodifica correcta (salas, links, tiles, guards, cadenas de
doorlinks, spawn). Jugabilidad: parcial — p. ej. el L3 original permite
explorar ~10 salas. Para completar los originales al 100 % faltan:

- semántica de fila canónica (punto 1 de arriba) en suelos de la fila 0,
- el set completo de verbos hang/climb encadenados (subir pisos es
  obligatorio en los niveles reales),
- CLOSER (botón que cierra gates) y timers por entrada de doorlink.

La campaña por defecto (fan-recreation) no depende de nada de esto.

## Lectura recomendada

El *code review* de Fabien Sanglard
(`fabiensanglard.net/prince_of_persia`) sobre cómo Merlin y las
directivas ORG mapeaban el código del Apple II en RAM.
