# Sistema de diseño — pop2026

## Concepto

> *Una mazmorra que respira en violeta y oro, dibujada con la mano de
> 1989 pero el aliento de 2026.*

Fusión moderna-retro. Píxeles geométricos generados por código (sin
sprites bitmap), animación con poses interpoladas, scanlines opcionales,
beeps PC-speaker reales sintetizados.

## Paleta — *"Persia Nocturna"*

Cinco colores semánticos + 2 utilitarios. Contraste verificado WCAG AA
contra `bg` y `bg-elev`.

| Token        | Hex       | Rol                                            |
|--------------|-----------|------------------------------------------------|
| `bg`         | `#1A1325` | Fondo (mazmorra profunda)                      |
| `bg-elev`    | `#2A1F3D` | Fondo elevado, paneles, tiles de pared         |
| `primary`    | `#E8D9A8` | Príncipe, texto principal (pergamino)          |
| `accent`     | `#C77DFF` | Resaltados, potion-cure, victoria (violeta)    |
| `success`    | `#8FE388` | Curar HP, llegar a salida (verde lima)         |
| `warning`    | `#F2C14E` | Temporizador <10 min (oro polvoriento)         |
| `error`      | `#E63946` | HP <2, sangre, guardia hostil (rojo aerolito)  |
| `muted`      | `#6E5F8A` | Tile inactivo, sombra (lila apagado)           |

Contraste primary/bg = 11.2:1 ✓ AAA. accent/bg = 7.4:1 ✓ AAA.
error/bg = 6.8:1 ✓ AA. warning/bg = 9.1:1 ✓ AAA.

## Tipografía

- UI: **JetBrains Mono** (incluida vía `pyfontstash`/fallback sistema)
  o, en su defecto, la fuente mono del sistema. Tamaño base 18px en
  ventana 960x600.
- Texto narrativo (cinemáticas): misma familia, peso semi-bold, espaciado
  letra +1.
- HUD numérico: tabular nums (cifras de igual anchura) para que el reloj
  no "salte".

## Espaciado

Sistema basado en **8px**. Todos los gaps son múltiplos: 8, 16, 24, 32,
48, 64. Tile lógico = **24x24 px**, ventana lógica = **40x25 tiles**
(960x600 px), ventana real = ventana lógica x escala 1x/2x (configurable).

## Iconografía

Glyphs ASCII y formas geométricas dibujadas a primitivas pygame:

| Elemento     | Forma                                          |
|--------------|------------------------------------------------|
| Príncipe     | Cuerpo trapezoidal `primary`, cabeza círculo   |
| Guardia      | Cuerpo trapezoidal `error`, sable como línea   |
| Floor        | Rectángulo `bg-elev` con bisel claro arriba    |
| Spikes       | Triángulos `muted`/`error` cuando activos      |
| Loose floor  | Rectángulo con fisura diagonal                 |
| Gate         | Barrotes verticales `warning`                  |
| Pressure     | Placa con flecha hundida                       |
| Potion ↑HP   | Frasco bulboso `success`                       |
| Potion poison| Frasco bulboso `error`                         |
| Exit         | Arco `accent` con halo glow                    |

## Estados clave

| Estado       | Descripción visual                                          |
|--------------|-------------------------------------------------------------|
| `splash`     | Logo "POP·2026", subtítulo, parpadeo "ENTER"                |
| `playing`    | Vista cuarto + HUD (reloj, HP, nivel)                       |
| `paused`     | Vista atenuada al 30%, banner "PAUSA · ESPACIO"             |
| `dialog`     | Cinemática entre niveles, texto centrado                    |
| `dead`       | Pantalla roja flash, mensaje, "R reiniciar"                 |
| `victory`    | Pantalla violeta con texto cinematográfico                  |
| `loading`    | Punto pulsante centrado                                     |

## Accesibilidad

- **Teclado completo**, no se requiere ratón.
- Modo **alto contraste** (`--high-contrast`) que sustituye `bg` por
  negro puro y `primary` por blanco.
- Modo **sin parpadeos** (`--no-flash`) que desactiva flashes en muerte.
- HP no depende solo de color: barra **+ número**.
- Reloj con cifras tabulares siempre visible.
- Texto traducible (es por defecto, en disponible vía `LANG=en`).

## Toque distintivo

**Scanlines fosforescentes con respiración (breath)**. Líneas
horizontales sutiles (alpha 18) sobre toda la pantalla. Cada 4 s, su
alpha oscila ±6 puntos: la pantalla "respira" como un monitor CRT
caliente. Es la firma estética del proyecto. Se puede desactivar con
`--no-crt`.

## Bindings de teclado

| Tecla              | Acción                                |
|--------------------|---------------------------------------|
| `←` / `A`          | Mover/empujar a la izquierda          |
| `→` / `D`          | Mover/empujar a la derecha            |
| `↑` / `W`          | Saltar / escalar arriba               |
| `↓` / `S`          | Agacharse / soltarse / escalar abajo  |
| `Shift`            | Caminar (más lento, más preciso)      |
| `Space`            | Sable: golpear                        |
| `Q`                | Sable: parar (parry)                  |
| `Esc`              | Pausa / menú                          |
| `R`                | Reiniciar nivel (solo si muerto)      |
| `F1`               | Ayuda                                 |
| `F11`              | Pantalla completa                     |

## Audio

- **PC speaker sintetizado**: ondas cuadradas (numpy) de 1 canal, 11025
  Hz, mezcladas a pygame.mixer. Sin samples externos.
- FX clave: paso, salto, choque sable, espada cae, grito muerte,
  tile que se rompe, beep del reloj a 5 min.
- Volumen master: `--volume 0..100`, default 70.
- Silencio total: `--mute`.

## Animación

- Cada acción del príncipe tiene **3 poses**: inicio, medio, fin.
- A 60 fps interpolamos linealmente posición/tamaño entre poses.
- Pausas micro (2 frames de hold) en los hits de combate dan la
  sensación rotoscópica (Mechner llamaba a esto "weight").
