# ADR 0005 — Lenguaje visual: vector-retro CRT

## Contexto

Tenemos pygame-ce (ADR 0001) pero sin sprites bitmap. Hay que decidir
una estética coherente.

## Opciones

1. **Pixel art procedural**: emular sprites de 16×16 dibujados píxel a
   píxel desde código. Posible pero tedioso.
2. **Vector geométrico**: formas simples (rect, polygon, circle) en
   colores semánticos. Tres dimensiones: silueta + bisel + sombra.
3. **Mixto**: vector para tiles, "sprite procedural" (poses como
   conjuntos de rects) para actores.

## Decisión

**Opción 3: vector para entorno, "skeleton-of-rects" para actores**.

El príncipe es ~7 rectángulos: cabeza (círculo), torso (trapecio),
brazos (rect rotado), piernas (2 rects), sable (línea). Cada pose
modifica posiciones y ángulos. La interpolación entre poses produce la
sensación rotoscópica.

Encima, **CRT layer**: scanlines + vignette + leve resplandor por color
en bordes. Es la firma visual.

## Consecuencias

- **+** Producible 100% por código.
- **+** Escalado vectorial sin pixel-art aliasing.
- **−** No es "retro fiel". Es retro reinterpretado. Asumido
  conscientemente como [LICENCIA CREATIVA].
