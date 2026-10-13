# Changelog

Todas las novedades reseñables. Formato basado en [Keep a Changelog]; el
versionado sigue [SemVer].

[Keep a Changelog]: https://keepachangelog.com/es/1.1.0/
[SemVer]: https://semver.org/lang/es/

## [canon-0.19.0] — 2026-10-13

### Gráficos 2026: lienzo HD, personajes con esqueleto, tiles con volumen y post-proceso

La lógica canon no cambia; todo el arte sigue siendo procedural (sin
assets ni gráficos del original).

- **Lienzo HD 1280x852** (el canon a 4x): todo se pinta nítido a la
  resolución final. La interfaz se diseña en la escala clásica y pasa
  por ``layout.px``; las fuentes escalan solas. La ventana "2x" de los
  ajustes es el lienzo a 1:1 y el escalado por defecto pasa a *suave*
  (llena la pantalla completa sin bandas).
- **Personajes nuevos** (``poses.py`` + ``char_atlas.py``): esqueleto 2D
  con una pose por cada frame canon — carrera, arranque y frenada,
  giro con escorzo, saltos parado y con carrerilla, caídas,
  aterrizajes, agacharse, colgarse (las manos agarran la cornisa por
  IK), trepar, guardia, estocada, parada, herido, muertes (pinchos,
  cuchillas, desplome), beber y desenvainar. Miembros cónicos con tres
  tonos, contorno, supermuestreo x2 y vestuario por personaje (kid,
  guardia con turbante y chaleco, visir con túnica y turbante alto,
  princesa, esqueleto de huesos, sombra con ojos que brillan, ratón).
  Sprites cacheados por (frame, paleta, dirección) y pre-pintados poco a
  poco al empezar cada nivel.
- **Tiles con volumen** (``tile_atlas.py``): losas con cara superior y
  frontal biseladas, juntas, desgaste, sombra proyectada y cantos al
  aire; columnas cilíndricas con basa y capitel que se pintan *por
  delante* del personaje; rastrillo de hierro remachado; pinchos y
  cuchillas metálicos (con sangre); frascos de vidrio con líquido y
  brillo; puerta de salida con dovelas, escalera y hoja que sube;
  espejo, balcón con cielo nocturno, celosías, esqueleto y espada.
  Llamas de antorcha animadas en tres capas. Los pies pisan el centro
  de la losa.
- **Pared de fondo HD** generada con numpy: sillares con color propio,
  bisel, grano y manchas, humedad y musgo, regueros, cadenas y
  argollas; en el palacio, friso de azulejos, hornacinas lobuladas y
  tapices.
- **Post-proceso**: *bloom* (resplandor de llamas, pociones y chispas,
  ~2 ms), rayos de luz volumétricos, niebla que se arrastra por el
  suelo, filo de luz en el borde de las plataformas, gradación de color
  y luz de antorcha más cálida. Nueva opción "Resplandor".
- **Interfaz HD**: HUD con gemas de vida facetadas y franja de
  terciopelo, rótulos con sombra, paneles de vidrio con filo dorado,
  título y rótulos en oro metálico con halo; el menú de opciones
  siempre cabe en pantalla.
- **Póster del título** rehecho: cielo con nebulosa y estrellas que
  titilan (y fugaces), luna con halo, palacio en dos planos con
  ventanas que parpadean, nubes, cortinas de terciopelo y personajes
  bañados por la luna.
- Rendimiento: la pared y los tiles se componen una vez por cambio de
  estado; ~8 ms por frame en el lienzo HD con todos los efectos.
- 278 tests nuevos (``test_graphics_hd.py``): pose finita para cada
  frame de ``seqtbl``, pies en el suelo, manos en la cornisa al colgar y
  trepar, sprites espejados, los 31 tiles en ambos estilos, *bloom*.

## [canon-0.18.0] — 2026-10-13

### Edición 2026: presentación, audio, controles y ayudas modernas

La lógica canon no se toca; todo lo nuevo vive encima (``presentation/``,
``application/assist.py``, ``hints.py``, ``stats.py``) y se deriva del
estado inmutable del juego.

- **Modos de juego**: *moderno* — **Arenas del Tiempo** (mantener R /
  LB rebobina hasta 6 s, con medidor de arena que se recarga jugando;
  funciona también desde la pantalla de muerte) y **punto de control
  por sala** (morir te devuelve a la entrada de la sala con la vida
  llena; el reloj no se devuelve) — y *clásico 1989*.
- **Iluminación dinámica**: mapa de luz multiplicativo + brillo aditivo;
  antorchas que parpadean, halo del kid y de los enemigos, pociones y
  puerta de salida; luz fría en la mazmorra y cálida en el palacio
  (tabla canon ``tbl_level_type``). Pared de fondo con sillería
  procedural por sala (grietas, musgo, cadenas; azulejos y arcos en el
  palacio).
- **Partículas y juice**: polvo al aterrizar y al correr, chispas en
  las paradas, sangre, cascotes al romperse y estrellarse las losas,
  destellos de pociones y espada, ascuas de antorcha, motas en la luz;
  *hit-stop*, sacudida de cámara, destello de daño, pulso rojo con 1 HP,
  sombras bajo los personajes, transición deslizante entre salas y
  filtro sepia al rebobinar.
- **Audio**: SFX sintetizados con ruido filtrado y parciales metálicos
  (espadas, rejas, cuchillas, pinchos, losas), paneo estéreo según la
  posición; música procedural en modo *hijaz* (bordón + laúd) con capa
  de darbuka *maqsum* que entra en combate.
- **Mando** SDL GameController + teclado unificados (stick con
  detección de flanco en menús).
- **Menús**: principal, pausa (reanudar, reiniciar nivel, mapa,
  opciones, controles, salir), opciones persistentes en JSON, pantalla
  de controles, mapa de salas exploradas, pantalla de **nivel superado**
  con estadísticas.
- **Pistas contextuales** (una vez cada una): agarrarse, trepar,
  descolgarse, saltos, duelo, suelo suelto, placas, rebobinar.
- **Pantalla**: lienzo de 640x426 escalado a ventana redimensionable o
  pantalla completa (F11 / Alt+Enter), píxel nítido o suave, filtro CRT.
- **Accesibilidad**: sacudida y destellos desactivables, reloj siempre
  visible, volumen por canal; tipografía con símbolos (o palabras si el
  sistema no tiene una fuente con flechas).
- Coste de dibujo con todos los efectos: ~3,4 ms por frame.
- Tests: ajustes, escalado, entrada, rebobinado, checkpoints, pistas,
  estadísticas, mapa, eventos FX, partículas, audio y un recorrido del
  bucle real (título → nivel → pausa → opciones → juego). 916 tests.

## [canon-0.17.0] — 2026-10-10

### Trampas y enemigos rehechos sobre el código del original

Todas las trampas y toda la IA de los enemigos se han tirado y vuelto
a escribir siguiendo ``seg007.c``, ``seg002.c``, ``seg003.c`` y
``seqtbl.c`` de SDLPoP. Lo que había era una aproximación por celdas
con números inventados; esto son las mismas máquinas de estado.

**Trampas** (``traps.py`` / ``tick.py``):

- Losa suelta: al pisarla (o al golpearla desde abajo saltando) el
  modifier cuenta 1..11 y CAE aunque el kid ya no esté encima; una losa
  que se estrella en su fila sólo la hace temblar (0x80). La losa que
  cae es un *mob* con gravedad (+3 hasta 29): arrastra las losas
  sueltas que atraviesa, baja de sala en sala, al estrellarse deja
  escombros (los pinchos de esa celda quedan inutilizados, una poción
  se destruye, una antorcha pasa a "antorcha con escombros"), sacude
  las losas de la fila, acciona el botón sobre el que cae (un OPENER
  queda abierto para siempre) y quita 1 HP al kid si le cae en la cabeza.
- Pinchos: recogidos hasta que el kid se acerca por encima
  (``check_spike_below``, también desde el aire); salen (1..4), se
  quedan 15 ticks fuera (0x8F..0x80), se recogen (6..8). Corriendo
  mueres sólo mientras salen; aterrizar de un salto o una caída con
  ellos fuera o saliendo mata; andar con cuidado entre ellos es seguro.
  Un cuerpo clavado los deja fijos (0xFF).
- Cuchillas: paradas (abiertas) hasta que el kid llega a su fila
  (aterrizar, empezar a caer, cambiar de sala o fila): arrancan con los
  desfases canon 15, 12, 9, 6, 13, 10... y ciclan 1..15; muerden en el
  frame 2; se paran al irse el kid de la fila; sangre tras un mordisco.
- Botones: un OPENER pisado por una losa o por un muerto queda
  accionado para siempre (``died_on_button`` / escombros).
- Los guards también mueren en cuchillas y pinchos; una caída que no
  sea suave los mata (canon ``land``).

**Enemigos** (``guard.py`` / ``combat.py`` / ``seqtbl.py``):

- Frames y secuencias canon: en guardia 158/170/171, estocada del kid
  151→154 (la punta hiere en el 154) y del guard con preparación 168,
  parada 169→150 (y 161), estocada tras parar, estocada parada (167),
  herido (172-174 con retroceso), desplome 179-185, avance 6 px,
  retroceso 5 px, giro en guardia.
- Impacto por píxeles (``char_opp_dist``): se hiere entre 12 (8 si el
  rival va desarmado) y 28 px; la estocada se para si el rival tiene la
  hoja en 150/161 a menos de 29 px. **Un kid desarmado muere de una
  estocada.** Si ambos conectan a la vez sólo cuenta la del kid.
- IA ``autocontrol_guard_active``: línea de visión con la regla de
  "ve pero no viene" (losa suelta, cuchillas, gate cerrada o hueco por
  medio), se aparta a menos de 12 px, bloquea con ``blockprob`` /
  ``impblockprob``, ataca con ``strikeprob`` / ``restrikeprob`` a 12-28
  px y avanza con ``advprob`` fuera de ese rango (nunca mientras el kid
  está en plena estocada si su skill > 0), estocada preventiva al kid
  que llega corriendo o saltando, refractario tras ser herido, se gira
  si el kid le pasa por detrás, persigue al kid a la sala vecina y le
  sigue por un borde si abajo es seguro. Empieza en reposo (frame 166)
  y se pone en guardia al ver al kid. El esqueleto y el visir usan la
  misma IA.
- El kid sólo ataca, para, avanza o retrocede desde los frames de
  guardia (canon ``swordfight``); su parada se adelanta un frame si el
  rival ya está pinchando. Desenvaina solo cuando un enemigo le ve a
  menos de 90 px, o se gira si lo tiene a la espalda.
- Render: poses por frame canon (parada, estocada, herido, reposo),
  pinchos que salen y se recogen, cuchillas por frame, losas que
  tiemblan y caen, escombros.
- Bug: los flags de los eventos scripted (sombra fusionada, esqueleto
  despierto, visir, ratón) se perdían cada tick porque la recogida de
  items los leía del juego anterior; la fusión con la sombra en L12
  daba +1 HP máximo en cada tick de contacto. Ahora ocurre una vez.
- Regla canon ``justblocked``: al guard cuya estocada acaba de ser
  parada le cuesta bloquear la réplica durante 4 ticks
  (``impblockprob``). Es como se vence al visir, que bloquea siempre:
  parar y contraatacar desde la parada (``blocktostrike``).
- Bot humano: en vez de una ristra fija de estocadas, una política
  reactiva de duelo (para cuando el rival lanza la estocada, replica
  desde la parada, pincha a distancia de hoja, se acerca o retrocede)
  — lo que hace un jugador;
  en combate sólo considera batirse o moverse; prefiere llegar entero
  (cada HP perdido cuesta como 150 ticks de camino) y la posición en
  píxeles forma parte del estado de combate. Replays dorados
  regenerados. Con el combate canon el bot humano completa los
  **niveles 1 y 3 originales** (en el 1: espada al otro lado del nivel,
  CLOSER saltado, duelo con el guard y plate de salida); en el 2 la
  política de duelo vence al primer guard pero la búsqueda agota el
  presupuesto en las salas siguientes.

## [canon-0.16.0] — 2026-10-10

### Cornisas, caídas y gates como en el original

Verificado contra `seg005.c` / `seg006.c` / `seg007.c` de SDLPoP.

- **↑ de pie** (`check_jump_up`): si hay cornisa delante-arriba, salta y
  se agarra; si el suelo está justo encima y detrás-arriba hay hueco,
  se agarra a su borde trasero con el cuerpo sobre el vacío (así se
  trepa un pozo de cornisas de espaldas al hueco — L2 original). Si no,
  salto vertical.
- **↓ de pie de espaldas a un borde** (`down_pressed`): descolgarse por
  él (seq 68 CLIMB_DOWN); si no hay borde detrás, agacharse. Se elimina
  el ↓+SHIFT mirando al hueco (no existe en el original).
- **Colgado** (`control_hanging`): ↑ trepa, SHIFT mantiene el agarre,
  sin SHIFT se suelta. Los pies cuelgan a ras del suelo de la fila del
  cuerpo (`y_land[row+1]`): por eso descolgarse "resta un piso".
- Las cornisas, el hueco para las manos y la celda del cuerpo se
  resuelven a través de salas vecinas (norte / sur / este / oeste),
  como `get_tile`. Un muro no es cornisa (`tile_is_floor(WALL)` = 0);
  una gate cerrada tampoco. `BIGPILLAR_TOP` deja de ser suelo.
- **Caídas**: un piso es una FILA (63 px), no una sala. 1 fila segura,
  2 filas 1 HP, 3 filas mortal; el aterrizaje ocurre con los pies en la
  superficie (antes se aterrizaba al entrar en la banda, acortando la
  caída). Antes una caída de 3 filas no hacía daño.
- **Gates** (`animate_door` / `trigger_gate`): pisar la plate dispara
  una apertura que continúa sola (+4/frame hasta 188 → 238) y luego
  baja 1/frame; franqueable mientras ≥ 24 (~18 s). Un CLOSER cierra de
  golpe. El modifier 1 del DAT = gate abierta de inicio
  (`load_alter_mod`). Los trobs animan en todas las salas.
- Una gate que baja sobre el kid lo aplasta (canon).
- Los botones y las losas sueltas sólo se activan con los pies en el
  suelo (canon ``check_press``): saltar por encima de un CLOSER ya no
  cierra la gate (L1 original, sala 20).
- Salto largo desde parado: exactamente 3 celdas (dx 42) y los pies
  vuelven a la superficie al terminar — fiable en plataformas de una
  celda (L3 original, sala 14).
- Bots: dirección y cuenta atrás de las gates forman parte del estado;
  A* por tiempo + distancia (las gates se cierran: hay que correr), con
  la distancia consciente de gates cerradas y por fases (espada si el
  nivel la tiene y el kid no, plate de la salida, salida);
  macros canon (↑ agarra y trepa, ↓ descuelga, run-jump + SHIFT agarra
  la cornisa de enfrente, salto largo desde parado, carreras largas).
- Hito: los **niveles 1, 2 y 3 originales** los completa el bot con el
  motor tal cual (el 3 incluye la carrera contrarreloj canon de la gate
  y el salto con agarre desde la losa suelta); el 1 también en modo
  humano (guards, chompers, 3 HP, sin espada hasta recogerla: ida al
  oeste a por la espada saltando el CLOSER, vuelta y duelo). El solver de topología
  busca en dos fases: abrir la exit door (objetivo: su plate) y, desde
  ahí, llegar a ella.
- Pantalla de título: controles actualizados.

## [canon-0.15.0] — 2026-10-10

### Geometría del original

El motor adopta la geometría del POP1 tal cual: **el char ocupa la celda
del suelo que pisa**; ``y`` es la altura de los pies dentro de la fila
(``FEET_Y`` = de pie en la superficie, el borde inferior de la fila). Se
acabaron los parches de "celda de debajo": items, plates, trampas, gates
y muros viven en la fila del suelo, como en LEVELS.DAT.

- Física: soporte en la celda propia; aterrizaje EN la celda de suelo;
  un char en el aire no baja de la superficie si su celda es suelo (el
  salto se desliza a ras; la caída aterriza); head-bump al subir contra
  el piso de arriba; muros y gates bloquean en la celda propia.
- Agarre canon: las manos alcanzan la cornisa en diagonal
  (col+fwd, row-1); cuerpo en el aire; vale subiendo y cayendo. Trepar
  deja al char EN la cornisa. Descolgarse por el borde: cuerpo en la
  celda de delante, una fila más abajo. Sin "shimmy" (POP1 no lo tiene).
- Niveles fan: `_canonize_rows` baja los items de la fila 1 a la fila
  del suelo (fila 2) y sube spawn, guards y doorlinks a esa fila. El
  carver de huecos verticales se mantiene.
- Render: la losa de suelo va en el borde INFERIOR de la celda (canon) y
  se pinta bajo todo tile-suelo con item; pies del char en ``y``.
- Importador: filas del DAT tal cual (sin desplazamientos).
- Saltos retunados a la nueva base (run-jump desciende sin hundirse en
  el suelo; salto largo 45 unidades).
- Replays dorados regenerados; suite de topología 14/14.
- Hito: el **nivel 1 original** (LEVELS.DAT, cargado localmente — los
  datos de Ubisoft no se incluyen) lo completa el bot de topología con
  el motor tal cual.

## [canon-0.14.0] — 2026-10-10

### Los verbos del original

- **Salto largo desde parado** (ARRIBA+dirección): libra 2 celdas y
  aterriza en la tercera, como el POP1. ARRIBA a secas sigue siendo el
  salto vertical (trepar / agarrar la cornisa de arriba).
- **Paso cuidadoso** (SHIFT+dirección): avanza una celda y NUNCA cae
  por el borde — el controller mira el suelo de delante y te detiene
  en el filo (canon).
- **Descolgarse de un borde** (ABAJO+SHIFT en un filo): el kid se
  descuelga y queda colgado de la cornisa que pisaba; ARRIBA vuelve a
  subir, ABAJO suelta y cae un piso sin daño — el movimiento esencial
  del original para bajar sin perder vida.
- **En guardia automática**: con espada, el kid desenvaina y se pone en
  guardia solo al tener un guard a ≤ 3 celdas en su fila (canon).
- **Semántica de fila canon** para los niveles importados: una gate
  cerrada o un muro en la celda de DEBAJO bloquean la columna (en el
  original el kid ocupa la fila del suelo); spawn y guards del DAT se
  colocan una fila por encima de su tile. Los originales siguen siendo
  sólo parcialmente jugables (faltan trepar entre pisos y la geometría
  exacta de cornisas); la campaña fan-recreation es la jugable.
- Tests nuevos de los cuatro verbos (8) y del bloqueo por fila (2);
  replay dorado de L6 regenerado (la guardia automática cambia el
  timing del combate). Suite en 816 verdes.

## [canon-0.13.0] — 2026-10-09

### Jugado de verdad: L1, L2, L10 por el loop real con teclas inyectadas

Un arnés (`scratchpad/play_real.py`) resuelve el nivel en modo humano,
reproduce la secuencia de teclas por el loop REAL del CLI (title → card
→ playing, autosave, audio) y captura pantallazos. Mirándolos aparecieron
fallos que ningún test veía:

- **El kid caminaba por dentro del techo**: al subir por un hueco del
  carver y moverse en horizontal dentro de una celda de suelo, el
  aterrizaje lo dejaba "de pie" en row 0 y recorría el nivel embebido en
  la losa superior, saltándose chompers, guards y gates. Fix: aterrizar
  exige entrar en el sólido DESDE ARRIBA, y en el aire no se entra de
  lado en suelo estructural (losa, muro, loose); los dinteles con suelo
  (DOORTOP_WITH_FLOOR) y los items-suelo siguen siendo atravesables.
- **Sprite fuera de la ventana** en los bordes de sala: el mapeo de `x`
  sub-tile sumaba el centro de celda Y el offset. Ahora recorre el ancho
  útil de la celda (15 %–85 %).
- **Gate dibujada al revés**: los barrotes "salían del suelo" al abrir.
  Ahora cuelgan del dintel y suben, con travesaños.
- **Exit door** era una barra morada: ahora arco de piedra de dos celdas
  con hueco oscuro y escalones.
- **Antorcha**: `BLEND_ADD` ignora el alpha y pintaba un sol. Rediseño
  (soporte, mango, llama con núcleo) y halo por intensidad RGB.
- Sprite del kid definido desde el primer frame (frame 15).

Y cerrando el exploit del techo afloraron bloqueos reales de nivel:

- **L6 sala 8 / L3**: gates con la plate al otro lado (legado); plate
  movida al lado de aproximación.
- **L13 sala 3**: pit de 3 celdas flanqueado por spikes en ambos bordes —
  el único salto aterrizaba en los pinchos. Spikes a una celda del borde.
- **Chompers desfasados**: todos los de una sala arrancaban en fase 0 en
  sincronía — dos chompers a 3 celdas eran un muro. Ahora cada uno lleva
  su desfase (canon), es un puzzle de ritmo.
- **Guards intocables**: bloqueaban incluso en su refractario tras
  atacar; un skill 7 (98 % de bloqueo) era invencible. Ahora, como en el
  canon, la ventana para herirles es justo después de su golpe.
- **Morir no terminaba la partida**: nada incrementaba el contador
  `alive` tras una muerte a espada o por caída, así que el juego se
  quedaba en PLAYING con el kid congelado a 0 HP (sólo las trampas
  cerraban la partida). Ahora todo char muerto cuenta frames y a los 30
  se registra LOST_DIED. Tests de regresión para espada y caída.
- **L1 sala 10**: chomper al entrar y guard al fondo — dos retos
  separados en el primer nivel, no encadenados.
- **Guards + chompers**: con bloqueo corporal, un guard plantado al otro
  lado de un chomper obligaba a cruzar las cuchillas bajo su espada y
  rebotar en ellas (L1 sala 10). Ahora el guard no se coloca pegado a un
  chomper y nunca empuja al kid de vuelta a uno.
- **Replays dorados** (`tests/canon/replays/L<n>.txt`): el bot humano
  resuelve cada nivel una vez y guarda la secuencia de teclas; el test
  la reproduce con el motor real (guards, chompers, HP de campaña) en
  segundos, como los replays de SDLPoP. `POP_REGEN_REPLAYS=1` vuelve a
  resolver con el A*. Un replay que no se puede regenerar = el nivel
  dejó de ser completable por un humano.
- Bot humano: macro de parada+contraataque, carreras largas, clave de
  estado con micro-estado de combate, cuota de presupuesto por sala y
  HP medio de campaña (3 + nivel/2, tope 10).
- **L1 sala 9**: gate movida a col 6, fuera de la vertical del pit de la
  sala 3 (caer encima de una reja dejaba al kid de pie en el techo).

## [canon-0.12.0] — 2026-10-09

### Jugabilidad humana verificada: espada persistente, guards que bloquean

Revisión adversarial desde el punto de vista de una PERSONA con teclado
(hasta ahora toda la verificación era con un bot sin guards ni
chompers). Hallazgos y arreglos:

- **La espada no persistía entre niveles**: del L2 en adelante el kid
  afrontaba a los guards desarmado. Ahora `Char.has_sword` (canon
  `have_sword`) viaja en `Session` y en el save; a partir de L2 el kid
  siempre la lleva (envainada, ARRIBA+SHIFT la desenvaina).
- **Cualquier kid podía "desenvainar"** una espada que no tenía
  (ARRIBA+SHIFT sin haberla cogido). Ahora exige `has_sword`.
- **Los guards no bloqueaban el paso**: se les atravesaba corriendo y el
  combate era opcional. Ahora un guard vivo bloquea la aproximación
  horizontal (canon) — hay que luchar. Las caídas desde arriba no se
  congelan sobre un guard.
- **L5**: un guard de skill 3 (bloquea el 78 % de los golpes) a 4 celdas
  del spawn mataba al jugador antes de poder reaccionar. Trasladado a
  la arena (sala 8).
- **Test de jugabilidad humana** (`test_playability_human.py`): bot A*
  con guards reales, chompers, 3 HP y macro de lucha — los 13 niveles
  jugables se completan en estas condiciones (~45 s de suite).
- Título: controles reales del juego (saltar, trepar, bloquear, pausa,
  tiempo), sin glifos que la fuente no renderiza.
- Save v3 (migración automática desde v1/v2). Suite en 804 verdes.

## [canon-0.11.0] — 2026-07-16

### Pulido "juego 2026": 60 fps suaves, continuar partida, juice

- **Interpolación 12→60 fps**: la lógica sigue a 12 FPS canon, pero el
  renderer interpola la posición de cada char entre el tick anterior y
  el actual — se acabó el movimiento a saltos de celda. Con snap
  automático en cambios de sala y teleports (respawn, grab).
- **Autosave + continuar**: la campaña se guarda sola al empezar cada
  nivel y en cada respawn (JSON en `~/.local/share/pop2026canon/`).
  En la pantalla de título, `C` continúa la partida guardada (nivel,
  HP máximo, reloj y muertes). El save se borra al completar el juego
  y migra automáticamente desde la versión 1 del formato.
- **Screen shake**: aterrizajes con daño (8 frames) y muerte (12).
- **Antorchas vivas**: halo pulsante animado a 60 fps por celda.
- Tests nuevos: interpolación (5) y roundtrip del save con muertes (2).
  Suite en 790 verdes.

## [canon-0.10.0] — 2026-07-16

### Alineación con el canon SDLPoP + importador de LEVELS.DAT

Estudio de los repos de referencia (Mechner Apple II, SDLPoP, PrinceJS,
mininim) — análisis completo en `docs/canon_sources.md`. Adoptado del
desensamblado DOS (hechos mecánicos reimplementados, cero código
copiado, cero datos de Ubisoft en el repo):

- **Tablas de guard reales** (skill 0..11): strikeprob, restrikeprob,
  blockprob, impblockprob, advprob, refractimer y extrastrength de la
  versión DOS. El skill 8 es el guard pasivo scriptado; el 4 lleva
  +1 HP; los 10/11 bloquean siempre sin refractory. La IA usa ahora
  `prob_strike` de tabla en vez de una fórmula inventada.
- **`tile_is_floor` canon**: TODO tile soporta peso salvo EMPTY,
  DOORTOP, BIGPILLAR_TOP y celosías — torches, potions, plates,
  swords, spikes y chompers son tiles-suelo, como en el original.
- **Semántica dual de interacción**: plates/potions/sword/spikes/
  chompers/exit se detectan en la celda del kid Y en la de debajo
  (nuestro kid está una fila por encima del tile que pisa).
- **Exit door canon**: la puerta de salida con plate asociada requiere
  abrirse (permanente); la puerta de ENTRADA (sala de spawn) ya no
  cuenta como victoria — antes los niveles importados se "ganaban" al
  tocar la puerta por la que entras.
- **Importador de LEVELS.DAT** (`infrastructure/levels_dat.py` +
  `--levels-dat`): carga los niveles ORIGINALES desde una copia propia
  del juego (contenedor DAT v1, directorio res20NN.bin o blob suelto).
  Decodifica salas, links, tiles+modifiers (potions remapeadas),
  guards, cadenas de doorlinks y spawn (con la inversión canon de
  start_dir). Verificado localmente contra los 14 niveles DOS;
  jugabilidad de los originales aún parcial (ver doc).
- Bot de completabilidad: macro nuevo de salto vertical + grab + climb.
- Suite en 783 verdes; los 14 niveles fan-recreation siguen
  demostrablemente completables.

## [canon-0.9.0] — 2026-07-16

### Juego completo: los 14 niveles demostrablemente completables

Un bot A* de macro-acciones (andar / correr / saltar / esperar) juega
ahora cada nivel tick a tick con `advance()` real y DEMUESTRA que llega
de spawn a exit door (y a la princesa en L14). Es un test permanente
(`test_completability.py`, 14 casos, ~10 s). Lo que hubo que arreglar
para conseguirlo:

- **Timing de gates canon**: cerraban en 7 ticks (~0.6 s) — imposible
  cruzar desde la plate. Ahora estado interno 0..140: abren en ~0.6 s,
  cierran en ~12 s, atravesables mientras estén ≥ 57 % abiertas.
- **Distancias de salto canon**: el run-jump volaba ~20 unidades (ni
  1 celda de pit). Recalibrado a ~56 unidades: libra exactamente 3
  celdas y muere en la 4ª, como el POP1. Carrera a 1 tile/4 ticks.
- **STOP_RUN congelado**: el controller reiniciaba la secuencia de
  frenado cada tick sin teclas — el kid nunca volvía a STAND.
- **Carver de huecos verticales** en `_build_level`: un agujero en el
  suelo (pit o loose) perfora el techo de la sala de abajo. Sin esto,
  TODOS los descensos del juego aterrizaban encima del techo del piso
  inferior.
- **Aterrizaje por entrada de celda**: sólo se aterriza sobre un sólido
  en el que se ENTRA durante el tick — antes, caminar dentro de una
  plataforma (DT_F) o iniciar caída dentro del hueco del techo
  tele-transportaba al kid encima.
- **Head-bump**: subir en un salto contra el suelo del piso de arriba
  aplana el arco (no se atraviesan techos).
- **Bloqueo aéreo**: las gates cerradas también cortan los saltos (el
  vuelo termina en caída recta) — se acabó saltarse los puzzles.
- **Rediseños**: L10 The Tower baja ahora en zigzag (cada caída es de
  1 piso con aterrizaje en suelo firme); L1 accede al piso inferior por
  loose en la sala 12 y sus gates tienen plate en el lado de
  aproximación; L6/L9 igual (patrón heredado "plate al otro lado de la
  gate" eliminado).
- Verificado además: 0 caídas obligatorias letales en los 14 niveles y
  geometría planar intacta.

## [canon-0.8.1] — 2026-07-16

### Presentación canon: geometría 32x63, losas POP, audio conectado

- **Fix de geometría raíz**: `layout.py` usaba 14 px de ancho de tile —
  pero 14 son unidades de *lógica* (TILE_SIZE_X de SDLPoP); el tile en
  pantalla del POP1 mide 32x63. Ahora tile 64x126 (2x): la sala pasa de
  280 px de ancho (todo parecía muro) a 640 px con proporción original.
- **Suelo tipo losa**: FLOOR ya no llena el tile completo de ladrillo —
  losa en el tercio superior con superficie iluminada, cara de ladrillo
  y sombra colgante, como las plataformas del original. Spikes nacen
  del borde inferior de la celda; grietas del loose dentro de la losa.
- **Chars a proporción POP1**: reescalado 1.5x del atlas (el kid ocupa
  ~90 px de los 126 de un piso). Pies apoyados en la losa (offset -2).
- **Loose caído se dibuja como agujero** (coherente con la física).
- **Variación visual determinista** por sala/celda: sillares hundidos,
  ventanas ocasionales en el back wall y tintes de sillería en 1 de
  cada 3 losas (lección del port C++ de referencia: 5 texturas de
  bloque + decoración rompen la monotonía).
- **Audio conectado**: el CLI ahora crea el `Beeper` y llama a
  `play_transitions` cada tick — el juego dejó de ser mudo (saltos,
  aterrizajes, espadas, gates, muerte...).
- **L10**: plataforma intermedia en la sala 2 — el drop de entrada ya
  no cuesta 1 HP obligatorio (verificado con simulador de caídas sobre
  los 14 niveles: ninguna caída obligatoria es letal).

## [canon-0.8.0] — 2026-07-16

### Física completa + campaña de 14 niveles jugable de principio a fin

El motor tenía tres agujeros estructurales que hacían el juego
imposible de jugar como POP y de ganar: no había aterrizaje (la caída
libre atravesaba suelos para siempre), no había colisión horizontal
(el kid atravesaba muros y gates "cerradas"), y `WON_GAME` no lo
disparaba nadie. Arreglos:

- **Física de caídas** (`domain/physics.py`):
  - Aterrizaje real: la caída libre termina al entrar en tile sólido.
    Daño por distancia acumulada (`Char.fall_dist`): 1 piso seguro,
    2 pisos −1 HP, 3 pisos muerte (canon POP1).
  - Walk-off: pisar el vacío (pit o loose caído) inicia caída.
  - Colisión horizontal (`blocks_body_at`): muros y gates cerradas
    bloquean el cuerpo; los pilares son decorado (canon). Las gates
    abiertas por plate (LevelState.open_gates) dejan de bloquear.
  - Loose floors caídos (`fallen_floors`) dejan agujero físico real.
  - Muerte en abismo (caer sin sala al sur).
  - `Char.landed_fall_y` registra la velocidad de impacto para el
    check letal de spikes.
- **Guards conscientes del terreno**: no atraviesan sólidos ni se
  tiran a los pits — se quedan al borde mirando al kid.
- **Campaña completa** (`application/session.py` nueva):
  - Reloj de 60 min global: sigue corriendo entre niveles y muertes.
  - hp_max ganado con pociones persiste entre niveles y respawns.
  - Morir reinicia el nivel (Enter); timeout = derrota definitiva.
  - Exit door encadena L1→…→L13→L14; alcanzar a la princesa en L14
    dispara `WON_GAME` (antes era imposible ganar).
- **Pociones completas**: FLOAT activa caída-pluma real (225 ticks,
  ninguna caída mata); TIME +30 s al reloj (con tope de 60 min);
  MAX_HP con tope canon de 10 corazones.
- **CLI** (`cli.py`): fases title→card→playing→dead/victory/defeat,
  pausa (P), tiempo bajo demanda (TAB), R reinicia la campaña, fix del
  bug que consumía la cola de eventos dos veces por frame (el Enter se
  perdía según el orden de llegada).
- **HUD**: HP del guard visible en la sala (derecha, como el original).
- **Tests**: +27 (física de caídas/colisiones, sesión de campaña,
  pociones, reunión con la princesa). Suite en 759 verdes, mypy
  strict limpio.

## [canon-0.7.0] — 2026-05-15

### Combate REAL + trampas verificadas + IA de guard

Auditoría profunda del gameplay tras feedback "los niveles no tienen
sentido, la lucha no funciona". Confirmado: los guards eran estatuas
inertes, el kid los mataba sin oposición. Arreglos:

- **IA de guard** (`domain/guard.py` nueva):
  - FSM determinista por seed (tick + room + idx).
  - Estados: idle / face / advance / strike / block.
  - Cuando el kid está adyacente, el guard ataca con probabilidad
    creciente según skill (0..11), bloquea strikes entrantes según
    `prob_block` del skill.
  - Avanza hacia el kid si está en la misma row a distancia >1.
  - Cooldown (`refractory`) tras cada strike/block.
  - Integrada en `tick.advance` entre special chars y combat.
- **`Char.skill: int`** nuevo campo para los 12 niveles canon de skill.
  Guards spawnan con `SwordStatus.DRAWN` y skill heredado del GuardSpawn.
- **Combat fixes**:
  - `can_strike` exige attacker.sword == DRAWN (antes el kid sin
    espada hacía daño — bug).
  - Tras conectar un strike, `_exit_strike_window` avanza la secuencia
    del atacante para salir de los frames 165-167 y evitar multi-hit
    triple en la misma animación.
  - `take_hp` no letal devuelve al char a Action.STAND (no parálisis
    HURT permanente, gameplay responsivo).
- **Tests de gameplay end-to-end** (`test_gameplay.py` nuevo, 10 tests):
  - Guard adyacente mata al kid pasivo en pocos ticks.
  - Guard distante avanza hacia el kid.
  - Kid con espada mata al guard usando STRIKE repetido.
  - Kid sin espada NO hace daño (regresión documentada).
  - Chomper mata al kid en su fase letal.
  - Spike mata al kid aterrizando con fall_y alto.
  - Loose floor cae tras LOOSE_FLOOR_DELAY ticks.
  - Gate cerrada es sólida.
  - Kid recoge sword pisándola (`SwordStatus.DRAWN`).
  - Mouse de L8 abre la gate de su sala.

**Tests**: 687 verdes (677 previos + 10 gameplay). mypy strict + ruff
limpios.

## [canon-0.6.0] — 2026-05-15

### Plataformas multi-altura intra-sala + L14 jugable + diversidad canon

Refactor profundo de las salas planas: ahora cada nivel mezcla plataformas
elevadas, arenas con columnas y salas escalonadas para que el juego se
sienta como POP1 — saltos verticales, posiciones elevadas, combate en
arena con cobertura, no sólo corredores.

- **Helpers nuevos**: `_platform_rows(platform_cols, pit_cols)` mete
  plataforma DOORTOP_WITH_FLOOR en row 1 (segundo piso interno);
  `_split_rows(upper_cols, lower_cols, pit_cols)` da una sala
  escalonada con plataforma elevada a un lado; `_arena_rows(pillar_pair)`
  da una sala-arena con dos columnas BIGPILLAR enmarcando el combate.
- **L14 jugable** (3 salas): pórtico de entrada con plataforma y
  antorchas → galería de escaleras con lattices y doortop ceremonial →
  cámara real con pillars y la princesa esperando.
- **Refactor de salas**: ~25 salas reelaboradas en L1, L2, L3, L4, L5,
  L6, L7, L8, L9, L11, L12 para usar plataformas, splits o arenas en
  lugar de corredores planos.
- **Tests de plataforma** (`test_pathfinding.py` extendido):
  - `test_no_more_than_two_flat_corridors_per_level`: cada nivel
    jugable tiene ≤2 salas que son corredores planos puros.
  - `test_level_has_platform_features`: cada nivel usa al menos una
    plataforma elevada (DOORTOP_WITH_FLOOR en row 1) o lattice
    escalable.

**Tests**: 677 verdes (651 previos + 26 nuevos plataforma/contenido).
mypy strict + ruff format+check limpios.

## [canon-0.5.0] — 2026-05-15

### Niveles canon **completos** 18-24 salas + hang-shuffle + path-finding

Tirón largo para llevar los niveles al tamaño/complejidad del canon real:

- **Reescritura completa de `levels_canon.py`**: nuevo sistema declarativo
  basado en `_RoomSpec` + `_build_level`. Helpers ricos: `_floor_rows`,
  `_drop_rows`, `_pillar_rows`, `_lattice_rows`, `_balcony_rows`,
  `_doortop_rows`. Cada nivel se construye como lista de specs.
- **Niveles a tamaño canon**: L1=18, L2=20, L3=18, L4=20, L5=20, L6=18,
  L7=22, L8=20, L9=20, L10=20, L11=20, L12=24, L13=18, L14=1. Total
  ~257 salas (vs. 80 antes).
- **Layouts multi-piso** con loops, galerías paralelas, sub-rooms
  secretos, salas-cripta accesibles por drop sur.
- **Diversidad de tiles**: usadas BIGPILLAR_TOP/BOTTOM (columnas
  estructurales), LATTICE_PILLAR (rejas escalables), BALCONY_LEFT/RIGHT,
  DOORTOP_WITH_FLOOR (multi-piso intra-sala), TORCH, POTION con
  variantes HEAL/MAX_HP/POISON/FLOAT/TIME/EMPTY.
- **Doorlinks complejos**: múltiples plates por gate, plates lejanas que
  abren gates en otra sala, puzzles locales (plate+gate same-room).
- **Hang-shuffle + release-hang en `physics.py`**: `hang_shuffle(char,
  room, direction)` mueve lateralmente colgado de cornisa; `release_hang`
  pasa a IN_FREEFALL. Integrado en `tick.advance` cuando el char está en
  HANG_STRAIGHT y hay input left/right.
- **Test de path-finding BFS** (`test_pathfinding.py`):
  - `test_level_exit_room_reachable_from_spawn`: cada nivel jugable
    tiene exit alcanzable por grafo de salas.
  - `test_no_orphan_rooms`: máx 2 salas secretas por nivel.
  - `test_level_cell_pathing_partial`: BFS celda-a-celda confirma que
    el spawn alcanza al menos 2 salas distintas.
  - `test_tile_diversity_across_levels`: ≥15 tipos de tile usados.
  - `test_uses_lattice_tiles`, `test_uses_pillar_and_balcony`,
    `test_potions_have_diverse_modifiers`.

**Tests**: 651 verdes (575 previos + 11 hang-shuffle + 65 pathfinding/
content/diversity). mypy strict + ruff format+check limpios.

## [canon-0.4.0] — 2026-05-15

### Poster canon + intro animada + level cards en todos los niveles

Cinemática y presentación visual al nivel del original (tributo
procedural, sin reproducir el arte):

- **`presentation/poster.py`** nuevo: poster procedural en 5 capas
  (cielo nocturno con estrellas titilantes → luna llena con halo →
  palacio de minaretes con cúpula central y ventanas iluminadas →
  cortinas rojas con pliegues + cordones dorados → siluetas de
  princesa/Jaffar/prince/guard usando el atlas con paletas). API
  `draw_poster(...)` con `PosterCast` y `curtain_openness` 0..1
  para animar apertura.
- **`LEVEL_CASTS`** mapea cada nivel 1..14 a un cast narrativo:
  L3 sólo prince, L4-6 prince+vizier (sombra), L12 trío completo,
  L13 sin vizier (ya derrotado), L14 reunion con princesa.
- **Intro animada** (`screens/title.py`): cortinas cerradas + fade
  desde negro → easing cubic out → cortinas abriéndose mientras el
  título aparece a partir del 45% → estado estable con controles.
  Duración 3.5 s.
- **Level cards** (`screens/cutscene.py`): cada nivel se presenta
  con el poster + cast del nivel como fondo y un panel central con
  nombre, número, tagline y "Pulsa ENTER" parpadeante.
- **CLI**:
  - `pop2026canon poster --level N --out file.png --time T`: genera
    PNG del poster (level=0) o level card de un nivel concreto.
  - `pop2026canon --skip-intro`: salta la cinemática y empieza en
    el level card.
  - Game loop ahora tiene fases TITLE → LEVEL_CARD → PLAYING →
    ENDING con transiciones por ENTER.
- **Paleta**: nuevos `poster_curtain`, `poster_curtain_dark`,
  `poster_sky`, `poster_sky_light`, `poster_moon`, `poster_palace`,
  `poster_palace_dark`, `poster_gold`, `poster_gold_dark`.

**Tests**: 575 verdes (564 previos + 11 en `test_poster.py` que
cubren cast por nivel, render sin crash, comparativa de cortinas
y level card de cada nivel). mypy strict + ruff limpios.

## [canon-0.3.0] — 2026-05-15

### Niveles 4-13 refinados con layouts canon ricos

Los stubs corredor-plano de L4-L13 se reemplazan por layouts con
mecánicas variadas y progresión coherente:

- **L4 The Mirror**: loose en sala 1, slalom de pinchos, pit central que
  fuerza runjump, mirror + potion, plate+chomper, gate doorlinked al
  exit con guard skill 3.
- **L5 The Thief**: triple loose en sala 2 (slalom rápido), chomper+spike,
  potion objetivo del shadow, segundo loose, plate→gate doorlink al
  exit.
- **L6 The Steps**: pit grande en sala 1 (cols 4-6) que dispara
  shadow_step en frame 43, plate+chomper en sala 3, doorlink a gate
  sala 2, guard skill 4 con spike adyacente.
- **L7 The Mountains**: layout en "L" con drop sur por col 8, jardín
  de pinchos, loose escalonadas en el piso bajo, doble chomper.
- **L8 The Caverns**: drop al sur cols 4-5, 4 loose floors en sala 4,
  doble chomper, gate locked que sólo el mouse abre.
- **L9 The Tomb**: dos skeletons + jardín de spikes + doble chomper +
  plate→gate doorlink + potion heal.
- **L10 The Tower**: torre puramente vertical con drop_rooms de
  plataformas estrechas en cada nivel + spike garden + guards skill 5.
- **L11 The Tower II**: combina horizontal + vertical, doble chomper,
  loose intermedia, drop final con plate+gate locales.
- **L12 The Vizier**: 8 salas con spike, doble chomper, potion max_hp,
  pit con loose, mirror+potion heal para fusión, arena del vizier
  skill 11 con spikes laterales.
- **L13 Final Run**: 4 salas en carrera — triple chomper en cadencia,
  spike garden con loose intermedia, pit con spikes a los lados.

**Helpers nuevos**: `_corridor(..., pit_cols=..., no_ceiling=...)` y
`_drop_room(..., floor_cols=...)` para layouts verticales.

**Tests**: 564 verdes (541 previos + 23 nuevos en
`test_levels_content.py` que validan tiles+eventos+room counts+links).
mypy strict + ruff limpios.

## [canon-0.2.0] — 2026-05-15

### Motor canon — cierre final

Tras el commit `4d49b97` (FASES 0→3.8) este release cierra los flecos
documentados como deuda técnica en el motor `pop2026canon`:

- **Doorlinks plate→gate específicos**: nuevo `DoorLink` dataclass en
  `domain/level.py`, campo `doorlinks: tuple[DoorLink, ...]` en `Level`.
  El bucle `_tick_traps` consulta `level.plates_for_gate(...)` para
  decidir si una gate se abre. Reemplaza el modelo "cualquier plate abre
  cualquier gate" del prototipo. Doorlinks declarados en L6 y L11.
- **Mouse abre gates sin plate (L8)**: `trigger_mouse_appear` fuerza
  `state=7` + `open_gate` en las gates de la sala sin doorlink. Tests
  cubren la apertura y la no-apertura de gates desconectadas.
- **Seqtbl extendido a 40 secuencias operativas**: añadidas ENGARDE,
  ADVANCE, RETREAT, BLOCK_STRIKE, BLOCK_TO_STRIKE, PUT_SWORD_AWAY,
  RUNTURN, BUMP, BUMPED_FALL, HARD_LAND, MED_LAND, GUARD_FALL,
  JUMP_HANG_MIDAIR, EXIT_LEVEL. Cubre todo el combate canon + locomoción
  + transición final. SND_BUMP, SND_HARDLAND, SND_EXIT añadidos.
- **Packaging integrado**: `pyproject.toml` ahora declara `pop2026canon`
  en `[tool.hatch.build.targets.wheel].packages` y `[project.scripts]`
  (`pop2026canon = "pop2026canon.cli:app"`). `[tool.coverage.run]` cubre
  los dos paquetes.

**Tests**: 532 verdes (523 previos + 11 doorlinks + 9 seqtbl + sanity
mouse-gate). `mypy --strict` y `ruff format+check` limpios en los 39
archivos del motor canon.

## [4.2.0] — 2026-05-14

### Pulido jugable + polish visual

**Gameplay:**

- `input_device.poll()` ahora emite `jump_pressed` / `jump_held`
  como canal independiente de `command`, permitiendo *running jump*
  real para el jugador humano (antes una sola tecla a la vez).
- Knockback equilibrado tras experimentar bajadas (mantenido
  `VX=0.30`, `TICKS=10` para asegurar separación de combatientes).
- Test de integración `test_demo_bot_wins.py` parametrizado con
  10 niveles fáciles: garantiza que cambios futuros no rompen
  jugabilidad básica con seed determinista.

**Visuales:**

- Animación de muerte: colapso gradual del torso durante 30 ticks
  con interpolación lineal y charco de sangre creciente bajo el
  cuerpo a partir del 70% de la animación.
- Respiración sutil del príncipe en pose `STAND`: bob vertical
  de 1 px usando `sin(ticks * 0.06)`.
- Estela del sable durante la ventana de impacto (STRIKE/LUNGE):
  3 capas con `BLEND_ADD` en color acento + chispa blanca en la
  punta. Mucho más legible que la línea simple anterior.

**Tests**: 320 verdes (310 anteriores + 10 nuevos bot wins).

## [4.1.0] — 2026-05-14

### Híbrido pragmático: micro-pasos + sombra + multi-pantalla

- **`Action.ADVANCE` / `Action.RETREAT`** — micro-pasos de medio
  tile cuando el príncipe tiene sable y un guardia está a
  ≤ `COMBAT_NEAR_CELLS` (2 celdas). LEFT/RIGHT pasan a ser
  paso corto en lugar de carrera, evocando el duelo del original.
- **Mirror guard** — `Guard.is_mirror`: clon-espejo que copia el
  input del príncipe con LEFT↔RIGHT invertidos. Nuevo
  `Tile.SPAWN_MIRROR` (carácter `'m'`).
- **`L13 'La Sombra'`** — duelo cuerpo a cuerpo contra el clon.
- **`L14 'El Trono'` y `L15 'La Huida'`** — niveles finales
  hand-crafted. `HAND_CRAFTED_COUNT` sube de 12 a 15.
- **Multi-pantalla por defecto** — `NARROW_COLS=40` (antes 20),
  `WIDE_COLS=60` (antes 40). Todos los `.poplv` built-in
  reescalados a 40 columnas.

### Tests

- `test_advance_moves_half_cell_forward`,
  `test_retreat_moves_half_cell_back`,
  `test_advance_only_triggers_with_sword_and_guard_near`.
- `test_mirror_walks_opposite_when_prince_moves_left/right`,
  `test_mirror_copies_strike`.
- Suite total: **310 verdes**.

## [4.0.0] — 2026-05-14

### Cambio fundamental — platformer real

El motor pasa de FSM-por-celdas (esencialmente roguelike con
disfraz de plataformas) a **physics-based platformer** con
coordenadas continuas. `PhysicsPrince` reemplaza al `Prince`
discreto como motor por defecto.

### Game-feel platformer 2026

- **Coyote time** (6 ticks): saltar después de dejar una plataforma.
- **Jump buffer** (6 ticks): JUMP pulsado en el aire se consume al
  aterrizar.
- **Variable jump height**: soltar JUMP durante el ascenso corta
  la velocidad vertical en 0.45×.
- **Air control**: aceleración horizontal en el aire `0.025`
  vs `0.10` en suelo.
- **Knockback dirigido**: golpe del enemigo empuja al príncipe en
  sentido opuesto y bloquea input por 10 ticks.
- `JUMP_VEL=-0.55` (pico ~2.5 celdas), `JUMP_REACH=4` celdas.
- `last_impact_vy` propaga la velocidad de aterrizaje; spikes
  letales solo si vy ≥ `SPIKE_LETHAL_VY=0.30`.

### Combate continuo (R4)

- **Alcance Euclídeo**: STRIKE 1.0 celdas, LUNGE 2.0 celdas en
  distancia float (no por adyacencia entera).
- **Cono frontal de parada**: PARRY solo bloquea si el defensor
  mira hacia el atacante.
- **Knockback** aplicado vía `with_damage(from_direction=±1)`.

### Verticalidad real

- L8 y L11 rediseñados con plataformas intermedias que requieren
  jump precision.
- Reachability BFS ajustada a los nuevos rangos
  (`JUMP_REACH=4`, `MAX_FALL_DROP=8`).

### Tests

- `test_physics_prince.py`: 5 tests nuevos sobre los game-feel
  essentials (coyote, buffer, var jump, air, knockback).
- `test_combat.py`: migrado a `PhysicsPrince`; 5 tests nuevos para
  alcance Euclídeo, cono de parry y knockback.
- 301 tests verdes, ruff/format/mypy --strict limpios.

### Compat

- `domain/prince.py` (Prince discreto) queda como módulo
  deprecated. Sus tests siguen pasando como referencia histórica.
- `physics_prince.PhysicsPrince` queda alias-importado como `Prince`
  en `combat.py` y `renderer.py` para compatibilidad de tipos.
- `InputFrame` gana `jump_held: bool` para soportar variable jump.

---

## [3.0.0] — 2026-05-13

### Modernizado / añadido en v3.0

- **100 niveles encadenados** en 4 actos de 25:
  Acto I "Mazmorra" (1-25), Acto II "Prisión" (26-50),
  Acto III "Palacio" (51-75), Acto IV "Torre" (76-100).
- **12 niveles hand-crafted** (los originales de v1.0) + **88 procedurales**
  por semilla determinista. Misma `--seed` reproduce la misma campaña
  byte a byte.
- **Generador procedural** en `application/level_generator.py`:
  esqueleto + densidad + actores + validación BFS + reintentos.
- **Reachability BFS** en `domain/reachability.py`: garantiza que cada
  nivel generado tiene al menos un camino del spawn al exit.
- **Curva de dificultad** declarativa en `application/difficulty.py`:
  monótona dentro de cada acto, escalón al cambiar; jefe en cada local
  24, esqueleto inmortal aparece en Acto IV a partir del local 12.
- **Tiempo por nivel** (no global): cada nivel arranca con su propio
  cronómetro derivado del acto (90/75/60/50 segundos).
- **Auto-save tras cada nivel ganado** hasta el 100; `--resume` carga
  la partida.
- **HUD** muestra acto + `N/100`.
- **Cinemáticas por acto** (4 escenas + final 100): `act1`, `act2`,
  `act3`, `act4`, `victory100`.
- **Música ambient por zona** (4 loops sintetizados): dungeon, prison,
  palace, throne. Cada acto tiene su pista.
- **CLI** acepta `--start-level [1..100]`, `--difficulty hard`,
  `--resume`, `--seed`, etc.
- **Tests**: 290+ verdes en menos de 2 s, 90 % cobertura en dominio,
  property tests con hypothesis para invariantes del generador.
- ADR 0006: justificación del enfoque procedural híbrido.

### Bugs corregidos en v3.0

- BFS de alcanzabilidad ya **no permite saltar sobre rejas cerradas**
  (antes la trayectoria horizontal del salto direccional ignoraba la
  celda intermedia).
- Esqueleto inmortal solo aparece a partir de Acto IV, local 12 (antes
  aparecía en todo el Acto IV por una constante mal asignada).

---

## [1.0.0] — 2026-05-13

### Preservado del original

- **Géneros de obstáculos**: pinchos (`spikes`), suelo suelto que se
  rompe al pisarlo (`loose floor`), placas de presión que abren puertas
  (`pressure → gate`), pociones curativas y venenosas.
- **Mecánica de combate**: sable, golpe (`strike`), parar (`parry`),
  daño doble por la espalda. Dos niveles de habilidad del guardia.
- **Tiempo límite global** que decrementa frame a frame.
- **Físicas con peso**: cada acción ocupa varios ticks antes de aplicar
  el desplazamiento; las caídas duelen y matan a partir de 4 celdas.
- **Animación rotoscópica** reinterpretada con interpolación de poses
  geométricas y duraciones de acción cuidadas.
- **Atmósfera de mazmorra**: paleta nocturna, oro polvoriento, violetas.

### Modernizado

- **Python 3.13+** con `pyproject.toml`, gestión con `uv`,
  `src/` layout.
- **Arquitectura hexagonal** con capas `domain / application /
  infrastructure / presentation`. Dominio puro y testeable sin SDL.
- **Tipos estrictos**: `mypy --strict` pasa en toda `src/`.
- **Calidad**: `ruff` + `ruff format` limpios, cobertura ≥90 % en
  dominio.
- **RNG determinista** inyectado (LFSR-8). Toda partida es reproducible
  con `--seed N`.
- **Modo demo determinista** con `--demo --seed N`: una IA simple lleva
  al príncipe hasta la salida sin intervención humana.
- **Render procedural** con pygame-ce: cero sprites bitmap, todo se
  dibuja con primitivas. Cero blobs binarios en el repositorio.
- **Audio sintetizado** estilo PC-speaker generado con numpy.
- **Overlay CRT** con scanlines (firma visual).
- **Persistencia XDG** (JSON validado con Pydantic).
- **Formato de niveles** `.poplv` texto plano, editable con `vim`.

### Añadido

- **12 niveles** de campaña con nombres y subtítulos:
  `01_cell`, `02_sword`, `03_guard`, `04_traps`, `05_plate`,
  `06_loose`, `07_duo`, `08_climb`, `09_maze`, `10_patrol`,
  `11_spikes`, `12_jaffar`. Diseños propios en formato `.poplv`.
- **Campaña encadenada** con reloj global de 60 minutos conservado
  entre niveles (homenaje al original).
- **Pantalla de título** con logo, subtítulo y parpadeo del prompt.
- **Cartas de nivel** intermedias con número, título narrativo y
  subtítulo.
- **Pantallas finales** de victoria y derrota con opción de reintento.
- **Tile sable `S`**: se recoge al pisarlo y habilita el combate.
- **Salto direccional**: ``JUMP`` mientras corres/andas hace `JUMP_R`
  (salto largo para cruzar huecos).
- **Trepar repisas**: ``UP`` ante una cornisa válida hace `CLIMB_UP`.
- **Demo determinista** mejorada: gestiona combate y reconocimiento de
  trampas. Gana 11/12 niveles sin intervención humana.
- CLI con Typer: `--demo`, `--seed`, `--frames`, `--start-level`,
  `--skip-title`, `--headless`, `--no-crt`, `--mute`, `--version`.
- Launcher `persia.py` para Windows/macOS/Linux sin `uv`.
- Tests unitarios, de integración y de propiedad (hypothesis).
- CI GitHub Actions con matriz Python 3.13 y 3.14.
- 5 ADRs documentando decisiones clave.

### Licencias creativas tomadas

- **[LICENCIA CREATIVA] Granularidad de celda en vez de píxel**: el
  movimiento avanza una celda por acción completada. Preserva la
  sensación de peso pero simplifica la física para v1.0. Ver
  `docs/original_program_analysis.md` §3.
- **[LICENCIA CREATIVA] Reloj global pausable**: en el original el
  cronómetro corría incluso en el menú. Aquí se pausa al abrir pausa.
- **[LICENCIA CREATIVA] Estética vector-retro**: en lugar de imitar los
  sprites rotoscopiados con bitmaps, dibujamos siluetas geométricas con
  scanlines CRT. Ver `docs/adr/0005-visual-language.md`.
- **[LICENCIA CREATIVA] 12 niveles propios**: los diseños de los
  niveles son nuestros, en formato `.poplv` ASCII; no reproducen los
  layouts concretos del original. La progresión de dificultad y los
  nombres narrativos son originales.

### Bugs corregidos respecto del original

- **Reloj corría en pausa** → el menú pausa el cronómetro.
- **Salto-en-el-borde permitía doble salto** → exigimos al menos 2
  píxeles (1 celda) de superficie bajo los pies para saltar.
- **Espadazo fantasma tras muerte de guardia** → al morir un guardia se
  purga el flag pendiente.

[1.0.0]: https://github.com/davidvivo-ia/Prince-of-Persia-python/releases/tag/v1.0.0
