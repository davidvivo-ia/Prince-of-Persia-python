# ADR 0001 — Capa de presentación: pygame-ce

## Contexto

Prince of Persia (1989) es un plataformas con scroll por cuarto,
sprites animados de 4 px de paso y colisiones a nivel de píxel. La guía
del proyecto fija el criterio:

> *Si el original usa modo gráfico real (sprites, scroll, colisiones
> píxel) -> pygame-ce.*

## Opciones consideradas

1. **Textual TUI**: rápido de desarrollar, accesible por SSH, pero
   recrear inerciales y combate frame-perfect en celdas de carácter
   distorsiona el juego.
2. **pygame-ce con assets bitmap**: lo más cercano al original, pero
   requiere arte propio que no podemos producir en una sola sesión sin
   herramientas externas.
3. **pygame-ce con dibujo procedural (primitivas)**: aprovecha la
   precisión píxel y permite cero dependencias de archivos binarios.
4. **pyglet / arcade**: menos comunidad, sin ventajas sobre pygame-ce.

## Decisión

**Opción 3 — pygame-ce con primitivas geométricas**.

Cada actor y tile se dibuja con `pygame.draw` (rect, polygon, line,
circle). Esto da una estética *vector-retro* coherente con el sistema
de diseño "Persia Nocturna" y elimina dependencia de assets bitmap, sin
sacrificar el píxel-perfect físico que el original exige.

## Consecuencias

- **+** Cero blobs binarios en el repo (solo texto y código).
- **+** Editor de niveles trivial (texto ASCII).
- **+** Permite headless tests con `SDL_VIDEODRIVER=dummy`.
- **−** No replica la rotoscopía pictórica original. Lo compensamos con
  interpolación de poses y micro-pausas (ver `design.md`).
- **−** pygame-ce añade ~15 MB de dependencias frente a un TUI puro.
