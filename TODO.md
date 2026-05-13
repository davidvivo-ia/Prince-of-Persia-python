# TODO — v1.1 y más allá

## Limitaciones conocidas v1.0

- **Movimiento por celda completa**, no por píxel. El alma de POP está,
  pero la sensación de "pasos cortos / largos" no llega al ASCII.
- **Solo 3 niveles** built-in. Los 12 originales son trabajo de contenido.
- **HANG/CLIMB simplificados**: no hay "colgarse de borde y soltarse a
  voluntad" como en el original.
- **Boss único** (skill 2) sin script especial: comparte IA con el
  guardia normal.
- **Sin cinemáticas** entre niveles: solo transición instantánea.
- **Render TUI no incluido** (vector pygame-ce únicamente).

## Priorizado para v1.1

1. **Niveles 4–12**: portar layouts del original o diseñar nuevos en
   `.poplv`. El motor ya los soporta.
2. **Físicas sub-celda**: añadir `sub_col ∈ [0, TILE_W)` al `Prince` y
   `Guard` para movimiento suave a 60 fps. Mantener API compatible
   guardando la celda discreta como propiedad derivada.
3. **Sistema de animación por keyframes**: cada acción define una serie
   de poses (offsets de torso, brazos, piernas) y el renderer interpola.
   Daría la sensación rotoscópica que hoy queda solo sugerida.
4. **Cinemáticas entre niveles**: pantalla intermedia con texto y arte
   ASCII; pausa el reloj durante la transición.
5. **Editor de niveles `pop2026-edit`**: TUI Textual minimalista para
   editar ficheros `.poplv` con preview de paleta.

## Backlog menor

- Localización inglesa de los mensajes del juego (variable `LANG`).
- Modo *speedrun*: HUD detallado, splits por nivel, exportación.
- Replay: grabar inputs por seed → reproducir partidas humanas.
- Modo "fantasma" del replay como adversario.
- Modo daltonismo: paletas alternativas.
- Configuración por TOML en `$XDG_CONFIG_HOME/pop2026/config.toml`.
- Documentar `keybindings.md` separado.

## Deuda técnica

- `presentation/app.py` mezcla composition root y bucle de demo. Separar
  en `composition.py` y `engine.py`.
- `combat.resolve` itera sobre guardias dos veces; aceptable para n≤8
  guardias por nivel, pero conviene un solo paso si crece.
- Las anotaciones `# type: ignore[attr-defined]` deberían desaparecer
  cuando `pygame-ce` publique `py.typed` (issue upstream pendiente).
