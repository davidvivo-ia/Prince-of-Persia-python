# `docs/design/10-audio.md` — Audio

## Estado actual

`pop2026/presentation/audio.py` ya tiene `Beeper` con jingles
sintéticos cuadrado/triangular y `play_transitions(prev, now)` que
detecta cambios de estado y dispara SFX.

**Se conserva** en el motor canónico, ampliado.

## Catálogo de SFX requeridos

| Nombre | Trigger | Existe |
|---|---|---|
| `step` | Cada paso del kid | ✓ |
| `bump` | Choque contra pared | ✗ añadir |
| `jump` | Salto | ✓ |
| `land_soft` | Aterrizaje sin daño | ✓ |
| `land_hard` | Aterrizaje con daño | ✗ añadir |
| `grab` | Hang ledge | ✓ |
| `climb` | Trepar | ✗ añadir |
| `strike` | Strike de espada | ✓ |
| `clash` | Espadas chocan | ✓ |
| `parry` | Bloqueo exitoso | ✓ |
| `hurt` | Kid recibe golpe | ✓ |
| `death_kid` | Kid muere | ✓ |
| `death_guard` | Guard muere | ✗ añadir |
| `chomp` | Chomper se cierra | ✗ añadir |
| `spike` | Pinchos extiende | ✗ añadir |
| `loose_crack` | Loose floor cruje | ✗ añadir |
| `loose_fall` | Loose floor cae | ✗ añadir |
| `gate_open` | Gate empieza a abrirse | ✓ |
| `gate_close` | Gate empieza a cerrarse | ✗ añadir |
| `plate` | Pisar plate | ✗ añadir |
| `pickup_sword` | Recoger espada | ✓ |
| `drink_potion` | Beber poción | ✓ |
| `mirror_break` | Romper espejo (L4) | ✗ añadir |
| `shadow_appear` | Shadow nace | ✗ añadir |
| `victory_level` | Pasar de nivel | ✓ |
| `victory_final` | Ending | ✗ añadir |
| `princess_cry` | Cinemática | ✗ añadir |

## Música ambiente

Por zona (mantener `zone_for_level`):
- `dungeon` (niveles 1-3): notas bajas, marcial
- `palace` (niveles 4-8): orquestal medio-oriental
- `throne` (niveles 9-12): tensión
- `ending` (13-14): triunfo

Implementadas en `audio.py`. **Mantener tal cual**, sólo añadir
"ending" si falta.

## Tests

- Cada nombre de SFX produce buffer no vacío
- `play_transitions` dispara SFX correcto en cada transición

Estimación: 1 día (sólo añadir los SFX faltantes; framework ya existe).
