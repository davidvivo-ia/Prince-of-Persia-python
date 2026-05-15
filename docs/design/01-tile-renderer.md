# `docs/design/01-tile-renderer.md` — Tile renderer

> Padre: `00-architecture.md`. Define el sistema de renderizado de
> tiles del nuevo motor.

## 1. Geometría

Canon (`types.h`):
- `TILE_SIZEX = 14`
- `TILE_SIZEY = 63`
- `SCREEN_TILECOUNTX = 10`, `SCREEN_TILECOUNTY = 3`

Una sala = 10 × 3 = **30 tiles = 140 × 189 px** en resolución
canónica.

**Decisión**: respetamos la proporción 14:63 (1:4.5) pero escalamos
al doble (28×126 → sala 280×378 px). Razones:
- Cabe en pantalla 1280×768 con HUD arriba de 48 px
- Ratio idéntico — la silueta del nivel coincide con SDLPoP

Constante final: `TILE_W = 28`, `TILE_H = 126` (revisable, en
`presentation/layout.py`).

## 2. Capas

```
Capa 0  back-wall          — pared del fondo (sombra, columnas, antorchas)
Capa 1  bg-tiles           — tiles que están "detrás" del char (lattice down, etc.)
Capa 2  chars-behind       — chars que van detrás del fg (princess en abrazo)
Capa 3  fg-tiles           — suelos, paredes, gates, chompers
Capa 4  chars-front        — el kid en primer plano
Capa 5  overlay            — torch flames, falling debris, dust
Capa 6  hud                — barra superior (tiempo, hp, sword status)
Capa 7  cinematic-overlay  — fades, texto, mensajes
```

## 3. Atlas de tiles

```
src/pop2026canon/presentation/tile_atlas.py
```

Cada tile expuesto como función `draw_<name>(surface, x, y, *, modifier, palette)`.
31 funciones (una por `tiles_*` del enum). Implementaciones:

| Tile | Función | Modifier usage |
|---|---|---|
| 0 empty | noop | — |
| 1 floor | `draw_floor` | textura banda |
| 2 spike | `draw_spike` | extended/retracted state |
| 3 pillar | `draw_pillar` | — |
| 4 gate | `draw_gate` | open/closed amount (0..7) |
| 5 stuck | `draw_stuck_button` | — |
| 6 closer | `draw_button` | pressed/released |
| 7 doortop_with_floor | `draw_tapestry_top` | variant |
| 8 bigpillar_bottom | `draw_bigpillar_b` | — |
| 9 bigpillar_top | `draw_bigpillar_t` | — |
| 10 potion | `draw_potion` | type (heal/empty/max/poison/float/time) |
| 11 loose | `draw_loose_floor` | shake state |
| 12 doortop | `draw_tapestry` | variant |
| 13 mirror | `draw_mirror` | broken/intact |
| 14 debris | `draw_debris` | — |
| 15 opener | `draw_pressure_plate` | pressed |
| 16-17 level_door | `draw_exit_door` | open/closed |
| 18 chomper | `draw_chomper` | jaw position 0..4 |
| 19 torch | `draw_torch` | flame frame 0..3 |
| 20 wall | `draw_wall` | — |
| 21 skeleton | `draw_skeleton_tile` | woke/idle |
| 22 sword | `draw_sword_pickup` | — |
| 23-24 balcony | `draw_balcony` | side |
| 25-29 lattice | `draw_lattice_*` | — |
| 30 torch_with_debris | `draw_torch_debris` | flame + debris |

Cada función dibuja procedurally con la paleta tributo (PALETTE actual
sobrevive). NO se usan sprites bitmap.

## 4. Render loop

```python
def render(surface, game_prev, game_curr, t):
    """t ∈ [0, 1) — interpolación entre dos ticks lógicos."""
    room = game_curr.level.rooms[game_curr.kid.room]

    # Capa 0
    draw_back_wall(surface, room, game_curr.flags)

    # Capa 1 — bg tiles
    for r, c in iter_tiles(room):
        if room.bg[r * 10 + c]:
            draw_tile(surface, room.bg[r * 10 + c], (c, r), layer="bg")

    # Capa 2 — chars que van detrás
    for char in chars_behind(game_curr):
        draw_char_interp(surface, find_prev(game_prev, char), char, t)

    # Capa 3 — fg tiles
    for r, c in iter_tiles(room):
        if room.fg[r * 10 + c]:
            draw_tile(surface, room.fg[r * 10 + c], (c, r), layer="fg")

    # Capa 4 — chars en primer plano
    for char in chars_front(game_curr):
        draw_char_interp(surface, find_prev(game_prev, char), char, t)

    # Capa 5 — overlays animados (antorchas, partículas)
    draw_overlays(surface, game_curr, t)

    # Capa 6 — HUD
    draw_hud(surface, game_curr)
```

## 5. Interpolación visual 12→60 FPS

El kid se mueve 1 tick lógico cada 5 frames visuales. Para suavizar:

- En cada frame visual: `pos_visual = lerp(pos_prev, pos_curr, t)`
- Sólo para chars en movimiento (frame con `dx`/`dy` activos).
- Tiles, gates, chompers: no interpolan — son "snap" entre estados.
- Loose floors al caer: pueden interpolar el sprite shake.

## 6. Room transitions (room-flick)

Cuando el kid cruza el borde E/W/N/S de una sala:
- `game.kid.room` cambia al `room_link[dir]`
- `kid.curr_col/row` se ajusta al borde opuesto
- El renderer detecta el cambio de room y hace **flick** (corte
  directo, no scroll) — como POP1 original

## 7. Dependencias

- `pygame-ce` (ya en el proyecto)
- `math` para interpolación
- No assets externos (todo procedural)

## 8. Tests

`tests/canon/test_01_tile_renderer.py`:
- Cada `draw_<tile>` produce una `Surface` de tamaño esperado
- Snapshot test: render de una sala 10×3 fija contra imagen-base
- Render con `tiles_4_gate` modifier 0..7 produce 8 imágenes
  distintas (gate progresivamente abriéndose)

## 9. Estimación

3 días: 1 capa back+fg, 1 día char draw + interpolación, 1 día
overlays + HUD + tests.
