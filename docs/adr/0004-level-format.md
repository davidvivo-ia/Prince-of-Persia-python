# ADR 0004 — Formato de niveles: texto ASCII `.poplv`

## Contexto

El original guarda niveles como blobs binarios en disquete. No nos sirve
ese formato. Necesitamos algo:

- Editable a mano.
- Versionable en git (diff legible).
- Cargable sin parsers ad-hoc complejos.

## Opciones

1. JSON / YAML: legible pero verboso para una grid 2D.
2. TMX (Tiled): formato estándar pero requiere Tiled como editor y XML.
3. **Texto ASCII custom**: cada carácter = un tile. Una habitación = N
   líneas. Niveles encadenan habitaciones con separadores.

## Decisión

**Texto ASCII** con tabla:

```
.   = empty (air)
#   = floor (solid)
=   = loose floor (cae al pisar)
^   = spikes
|   = gate (cerrada por defecto)
_   = pressure plate (abre gates etiquetadas)
+   = potion (curativa)
-   = potion (veneno)
@   = prince spawn
g   = guard spawn (skill 1)
G   = guard spawn (skill 2, jefe)
>   = exit
```

Niveles en `infrastructure/builtin_levels/01_dungeon.poplv` etc.

## Consecuencias

- **+** Editor = `vim`.
- **+** Tests pueden inline-definir niveles con triple-string.
- **−** Sin metadatos por celda (cosas como "esta gate la abre ESTA
  placa"). Resolvemos con: la gate más cercana en línea recta a una
  placa pulsada es la que abre. Suficiente para v1.0.
