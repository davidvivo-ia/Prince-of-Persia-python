# Superpensada · Los 13 niveles jugables, vitaminados

> Deliberación de diseño (protocolo *superpensada*: encuadre, datos,
> consejo de mentes, divergencia, combate adversarial, síntesis,
> re-pensar, veredicto) para rehacer la jugabilidad nivel a nivel del
> motor `pop2026canon`. El resumen por nivel está en el README; aquí
> está el porqué y el cómo, con los riesgos y la condición de
> invalidación de cada decisión.

## Diagnóstico

La pregunta literal es "más trampas, luchas y puzles". La pregunta real
es otra: **los niveles se completan, pero no se recuerdan**. Cada uno
tiene su laberinto, sus rejas y sus placas, pero la densidad de
*decisiones* por sala es baja (una o dos), los guardias son pocos y
están siempre en el mismo sitio del recorrido (una sala de paso), las
pociones no obligan a elegir y casi nada es opcional: el jugador hace
la única ruta y sale. Un juego de 2026 se mide por lo que pasa por
minuto, no por las salas.

Lo que de verdad mueve el resultado (primeros principios):

1. **Decisiones por sala**: cada pantalla debe plantear al menos una
   pregunta con respuesta visible (¿paso corto o salto? ¿pego o esquivo?
   ¿esta placa abre o cierra? ¿este frasco cura o envenena?).
2. **Legibilidad**: toda trampa se anuncia (cuchilla que asoma, losa
   agrietada, pinchos) y toda causa tiene efecto a la vista o a una sala.
3. **Ritmo**: tensión (duelo, pasillo de trampas, carrera contra una
   reja) seguida de alivio (poción, mirador, sala de puzle lento).
4. **Verificabilidad**: todo lo que entra en la ruta obligatoria lo
   juega el bot sin guardias (`test_completability`) y el solucionador
   humano con guardias y cuchillas (`test_playability_human`, replays
   dorados). Lo que no se puede verificar no entra en la ruta
   obligatoria: va a una rama opcional.

Supuestos ocultos que marco para cuestionarlos luego: (a) "más" es
mejor; (b) los solucionadores aguantan cualquier combinación; (c) el
jugador medio sabe parar una estocada.

## Terreno (lo que el motor permite, verificado en el código)

- `[dato]` Verbos: correr, salto parado (2 celdas), salto con carrerilla
  (3), trepar y descolgarse, colgarse, paso corto, agacharse, duelo
  (parar en los frames 152-153 del rival, réplica tras parada).
- `[dato]` Trampas: pinchos (matan corriendo o cayendo; a paso corto se
  pasan), cuchillas (ciclo de 15 ticks), losas sueltas (caen a los 11
  ticks de peso; sobre una placa que abre la dejan accionada para
  siempre, sobre pinchos los desactivan), rejas (abren con placa y se
  cierran solas en ~18 s; una placa puede abrir varias rejas; una
  placa de cierre las cierra), puerta de salida (abre con su placa).
- `[dato]` Pociones: vida, vida máxima, veneno, pluma (caída suave 3
  pisos), tiempo (+30 s), frasco vacío.
- `[dato]` Enemigos: guardias (habilidad 0-11, vida por nivel según
  `TBL_GUARD_HP`), un esqueleto por nivel (evento `SKELETON_WAKE`:
  nace junto al jugador al pisar una columna; no muere), sombra en
  L4/L5/L6/L12, Jaffar en L12, ratón en L8. El motor instancia todos
  los guardias de una sala; la IA de cada uno busca al jugador.
- `[dato]` Las salas son ASCII de 3x10 y los enlaces salen de una
  cuadrícula; mover una sala cambia los enlaces de sus vecinas.
- `[tesis]` Caso base: en el POP1 original cada nivel tiene 2-5
  guardias, una o dos "ideas" mecánicas y 1-2 pociones grandes; lo que
  lo hace memorable no es la cantidad sino que cada idea se explora
  tres veces (presentar, retorcer, combinar).

## El consejo deliberó

- **El diseñador de niveles (Mechner / Miyamoto)**: cada nivel, un
  tema mecánico explorado tres veces; la primera vez segura, la última
  combinada con un enemigo. Nada de trampas "porque sí".
- **El diseñador de puzles (Blow)**: la reja y la placa son el único
  puzle real del motor. Hay que sacarle todas las variantes: placa
  lejana con carrera, placa de cierre que hay que saltar, losa que cae
  sobre la placa (la "llave"), placa que abre dos rejas a la vez, reja
  opcional que guarda el tesoro.
- **El diseñador de combate (Platinum)**: los duelos cambian si el
  terreno cambia: guardia en una cornisa estrecha, guardia tras una
  losa suelta (si retrocedes caes), guardia junto a la placa que
  necesitas (el "portero"), guardia entre dos cuchillas. Cuatro roles,
  no un guardia genérico repetido.
- **El economista del tiempo (speedrunner)**: el reloj de 60 minutos y
  las medallas Veloz dan valor a los atajos. Un atajo con pluma o una
  losa que evita un rodeo son decisiones, no regalos.
- **El tester (QA)**: cada mecánica nueva en la ruta obligatoria es un
  riesgo con los solucionadores. Esqueletos y guardias dobles pueden
  dejar un nivel "incompletable" para el bot aunque un humano lo pase.
- **La voz disonante 1 (el purista)**: el original es sobrio; saturar
  de trampas lo convierte en otro juego. Cada añadido debe caber en el
  vocabulario de 1989.
- **La voz disonante 2 (el jugador casual)**: ya mueres bastante. Más
  guardias sin más vida es frustración. Hay que compensar con pociones
  de vida en los puntos de tensión y con los modos moderno y rebobinar.
- **La voz oscura (el que vende el juego)**: pon el tesoro detrás de
  una reja que se ve y no se alcanza; la gente vuelve por él. `[limpio]`
  (es diseño, no manipulación).
- **El arquitecto del motor**: no cambies la cuadrícula de salas: los
  enlaces, los replays y la decoración dependen de ella. Vitamina
  *dentro* de las salas y añade eventos y enlaces de rejas.

Tensión principal: densidad (Platinum, Blow, el vendedor) contra
verificabilidad y sobriedad (QA, purista, casual). Resolución: **todo
lo arriesgado va a ramas opcionales** (tesoros tras rejas, atajos),
y la ruta obligatoria crece en guardias y trampas que los
solucionadores ya han demostrado manejar.

## Divergencia (lo que se barajó)

1. Rehacer las cuadrículas desde cero. Descartado: cuesta mucho, rompe
   todo lo verificado, y el problema no es la topología.
2. Dos guardias por sala. Descartado en la ruta obligatoria (el
   solucionador se bate con el más cercano y el otro le pincha por la
   espalda); posible como opción en "difícil" más adelante.
3. Esqueleto en más niveles. Aceptado donde hay un pozo o una losa cerca
   para librarse de él (L8, L9, L12), porque no muere.
4. Rejas de tesoro: una reja visible que guarda la poción grande, con la
   placa en otro sitio o bajo una losa. Aceptado en 8 niveles: es
   opcional, da exploración y no toca a los solucionadores.
5. Placas que abren dos rejas (la de la ruta y la del tesoro). Aceptado.
6. Placas de cierre en pasillos de trampas (saltas la placa o pierdes la
   reja). Aceptado en L2, L5 y L12.
7. Pociones trampa (veneno junto a la cura) como decisión de lectura.
   Aceptado con moderación (L2, L6, L12): se distinguen por el color.
8. Pluma como atajo vertical en L10 (bajar la torre de un salto).
   Aceptado: es la idea lateral; convierte la torre en una decisión.
9. Pociones de tiempo escondidas al final de ramas peligrosas. Aceptado.
10. Guardia en la sala de la salida (el último duelo). Aceptado en los
    niveles de mazmorra (L1, L3) y de huida (L13).

## Combate adversarial

- **Pre-mortem**: "un año después, los niveles nuevos se abandonan en
  el 3". Causas probables: (a) la curva de guardias sube antes que la
  vida (3 HP y guardias de habilidad 3 en L2); (b) una placa de cierre
  mal colocada hace trampa; (c) el esqueleto persigue sin escapatoria.
  Mitigación: vida de campaña (+1 poción grande cada dos niveles),
  poción de vida antes de cada "portero", placas de cierre siempre con
  una celda de aire a cada lado para saltarlas, esqueletos sólo con
  losa o pozo a menos de dos salas.
- **Red team**: "las rejas de tesoro son relleno". Réplica: cada una
  exige una mecánica distinta (losa-llave, carrera, salto de placa) y
  da la medalla Explorador y la poción grande; sin ellas el nivel es
  una línea.
- **Steelman del purista**: "en 1989 cada nivel cabía en la cabeza".
  Se mantiene: ninguna sala gana más de una trampa nueva y un guardia, y
  las cuadrículas no cambian.
- **Falsación**: si el bot o el solucionador no completan un nivel con
  la ruta obligatoria nueva, la mecánica sale de la ruta (se cambia o
  pasa a opcional). Si el tiempo de referencia de la medalla Veloz se
  duplica, el nivel se ha pasado de denso.
- **Cola**: un guardia en la sala de la salida con el jugador a 1 HP es
  ruina; por eso hay una poción de vida a una sala de cada salida con
  guardia.
- **Sesgos**: anclaje en "más = mejor" → el criterio es decisiones por
  sala, no tiles por sala; confirmación → se verifica con dos
  solucionadores distintos, no con mi lectura.

## Síntesis: el plan por nivel

Formato: tema mecánico · set piece · guardias (habilidad) · puzles ·
trampas · pociones · rama opcional. Las cuadrículas no cambian.

### L1 Mazmorra — "La escuela"
Tema: un verbo por sala. Set piece: el pozo de la sala 3 y la losa
que te deja caer sobre el primer guardia. Guardias: 10 (0), 16 (0) y
**nuevo portero en la 18, junto a la puerta** (0): el nivel acaba en
duelo. Trampas nuevas: cuchilla antes de la losa de la 11 (hay que
cronometrar y no pararse), pinchos en la 17 por el lado del guardia.
Pociones: vida en la 2 y la 13; **tiempo en la 6** detrás de la losa.
Rama opcional: la poción grande de la 12 queda **tras una reja** que
abre la placa de la 6: pisa la placa, déjate caer por la losa y corre
hacia el oeste antes de que se cierre (la 12 ya no comunica con la 11).

### L2 Cuerpo de guardia — "La guarnición"
Tema: duelos con terreno. Guardias: 2 (1), 9 (3), 16 (2), **nuevos**
14 (2, entre cuchilla y pinchos) y **20, junto a la salida** (3).
Puzles: la reja de la 4 gana una **placa de cierre** entre la placa y la
reja (hay que saltarla a la carrera); la losa de la 8 sigue siendo la
llave de la placa de la 18. Trampas: tres cuchillas en la 3; pinchos
dobles en la 12. Pociones: **veneno junto a la cura** en la 7; vida
máxima en la 11.

### L3 Osario — "Lo que no muere"
Tema: el esqueleto y las losas. Set piece: despertar al esqueleto en
la 1 y perderlo por las losas de la 2 y la 4. Guardias: 6 (2), 15 (2),
**nuevos** 12 (2, portero de la placa) y **16 junto a la puerta** (3).
Puzles: la placa de la 12 abre la reja de la 7; **reja de tesoro** en la
18 (poción grande) que abre la losa de la 17 al caer sobre una placa
nueva. Trampas: cuchillas de la 14 ahora dobles; pinchos en la 8.
Pociones: vida 11, tiempo 13.

### L4 Galería del espejo — "El otro yo"
Tema: la sombra y las placas de cierre. Guardias: 8 (3), 14 (3),
**nuevos** 2 (3, sobre los pinchos: pelea a paso corto) y **20** (3,
portero de la placa de la salida). Puzles: la 15 mantiene placa-cierre-
reja; en la 11, bajo el pozo de la 3, un **tesoro tras reja**: aterrizas
sobre la placa y corres al oeste antes de que cierre (vida máxima). Trampas: losas sobre el vacío en la
16/17; cuchillas dobles en la 12. Pociones: veneno 13 (ya), pluma 20.

### L5 Salón del ladrón — "Lo que te roban"
Tema: perder y recuperar. Guardias: 8 (3), 10 (3), 20 (3), **nuevos**
16 (3, entre cuchilla y pinchos) y 12 (3). Puzles: la reja de la 7
gana una **placa de cierre** delante de la cuchilla de la 6; en la 13,
al fondo del ala oeste, un **tesoro tras reja**: placa, pinchos a paso
corto y la reja (vida máxima); hay que ser rápido y cuidadoso a la vez. Pociones: vida 4 (la que roba la sombra), vida 13, tiempo
20.

### L6 La escalinata — "Saltar a ciegas"
Tema: saltos con la sombra. Guardias: 4 (4), 10 (4), 15 (4), **nuevos**
12 (4, te espera al caer por el pozo de la 7, en suelo liso) y 16 (4,
bajo la cornisa, antes de la cuchilla de la 17: un duelo pegado a una
cuchilla es una trampa, no un reto). Puzles: la losa de la 6 sobre la
placa de la 11 (llave de la reja de la 8) se conserva; la placa de la
18 abre la salida **y** la reja de tesoro de la misma sala, con una
cuchilla entre la reja y la vida máxima. Pociones: **veneno junto a la cura** en la 11. Trampas:
pinchos triples en la 14, cuchilla en la 17.

### L7 Entrañas de la montaña — "El vacío"
Tema: caer con cabeza (pluma, losas, pozo de tres pisos). Guardias:
6 (5), 19 (5), 22 (5), **nuevos** 13 (5, junto a la poción) y 21 (5,
entre las cuchillas). Puzles: la placa de la 4 abre la reja de la 7;
**reja de tesoro** en la 15 con poción de tiempo, abierta por la losa
de la 9 al caer sobre una placa nueva en la 16. Trampas: losas triples
en la 17, cuchillas dobles en la 10.

### L8 Cavernas — "Lo que vive abajo"
Tema: oscuridad y huida. Set piece: **esqueleto** que despierta en la 16
junto al montón de huesos; la losa de la 16 es la escapatoria. Guardias:
15 (4), 19 (4), **nuevos** 11 (4, te espera al caer del pozo) y 14 (4,
portero de la placa de la salida). Puzles: el
ratón abre la salida (se conserva); la galería alta (2-9) es la rama
opcional con sus pociones. Trampas: losas triples 4,
cuchillas 7 y 17.

### L9 La tumba — "Los que vigilan"
Tema: cuchillas y porteros. Set piece: **esqueleto** que despierta bajo el
pozo (17) y sólo se pierde trepando por la cornisa. Guardias: 6 (5), 18 (5), 20 (5), **nuevos** 12 (5)
y 19 (5, portero de la poción grande). Puzles: la 4 mantiene su placa
de cierre; en la 19, **tesoro tras reja** con placa, cuchilla y un
portero dentro. Pociones: tiempo 20.

### L10 La torre — "Bajar"
Tema: descender la torre. Idea lateral: **poción de pluma en la 3** —
con ella se baja el pozo de la torre de un salto (atajo para la
medalla Veloz) en vez de cornisa a cornisa. Guardias: 2 (5), 9 (5),
15 (5), 20 (5), **nuevos** 6 (5, en la celosía) y 13 (5, entre
cuchillas). Puzles: en la 20, **tesoro tras reja** con su placa y un guardia
dentro (vida máxima). Pociones: tiempo 17.

### L11 Lo alto de la torre — "La azotea"
Tema: rejas en cadena. Guardias: 2 (5), 15 (3), 20 (4), **nuevos** 8
(5, entre pinchos) y 17 (5). Puzles: la losa de la 13 sobre la placa de
la 5 (llave) se conserva; la arena de la 2 esconde el **tesoro tras reja**
(placa, reja y vida máxima) detrás de su guardia. Trampas: cuchillas 16, pinchos 4 y
17.

### L12 Dominios del visir — "La corte"
Tema: todo junto. Set piece: Jaffar en la 7 y la fusión con la sombra
en la 5. Guardias: 1 (6), 3 (7), 15 (8), 20 (8), 24 (8), **nuevos** 11
(7) y 19 (8, entre cuchillas). **Esqueleto** en la 23, en el camino del
tesoro, con la losa suelta a la espalda. Puzles: cadena 13/16/21 → reja 14 y placa de cierre en la 21
(se conservan); la 24 guarda el **tesoro tras reja** con su
placa y el último guardia dentro. Pociones: **veneno junto a la cura** en la 5.

### L13 La huida final — "Sin mirar atrás"
Tema: velocidad. Antes no había guardias: ahora **tres** (6): en la 8,
en la 15 (portero de la placa de la salida) y en la 18 junto a la
puerta. Pociones: la de la 11 pasa a **tiempo**. Trampas: losas de la
17 sobre el vacío, cuchillas de la 10 y 16.

### L14 Aposentos
Sin cambios: es la cinemática jugable del reencuentro.

## Recomendación

Hacerlo en dos tandas (L1-L7, L8-L13), verificando cada nivel con el
bot y regenerando su replay dorado antes de pasar al siguiente.
Confianza en que la ruta obligatoria sigue siendo completable: 85 %
por nivel con guardias nuevos; 60 % en los tres con esqueleto (si el
solucionador no lo esquiva, el esqueleto pasa a una sala opcional).

## Lo que enseñó la verificación

- `[dato]` El bot sin guardias completó los trece niveles a la primera
  salvo L6, donde una reja de tesoro cruzaba un corredor obligatorio:
  las rejas de tesoro sólo caben en fondos de saco.
- `[dato]` El solucionador humano falló en L8 y L6 por la misma causa:
  un guardia a dos celdas de una cuchilla. El duelo obliga a retroceder
  y retroceder hacia la cuchilla es morir. Regla nueva: **el lado por el que
  se retrocede en un duelo tiene que ser suelo liso**; el guardia va
  antes o después del pasillo de trampas, no justo detrás de la cuchilla.
- `[dato]` Los esqueletos de L3, L9 y L12 pasaron la verificación: en la
  ruta obligatoria sólo si nacen detrás del jugador o en un fondo de
  saco; L8 lo pasa porque la losa de la 16 está más allá.

## Riesgos y señales de invalidación

- El solucionador humano no completa un nivel → se quita la última
  adición de la ruta obligatoria (primero esqueleto, luego guardia,
  luego trampa) hasta que vuelva a completarlo.
- El tiempo de referencia de la medalla Veloz (`PAR_SECONDS`) tiene que
  subir más de un 50 % → el nivel está sobrecargado.
- Un guardia nuevo mata al bot humano en más de la mitad de los intentos
  en modo difícil → bajar su habilidad un punto.

## Huecos

- No hay pruebas con jugadores reales: la dificultad percibida se
  calibra con el bot y con el HP medio de campaña.
- El esqueleto no muere; si el jugador no encuentra la losa o el pozo,
  la huida depende de correr. Se documenta en la pista contextual.
