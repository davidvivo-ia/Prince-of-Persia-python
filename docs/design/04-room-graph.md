# `docs/design/04-room-graph.md` — Mapa, salas, formato `levels.dat`

> Padre: `00-architecture.md`. Define cómo se representa el mundo
> (grafo de salas), cómo se carga del binario `levels.dat`, y cómo se
> navega entre salas.

## 1. Modelo

```python
@dataclass(frozen=True, slots=True)
class GuardSpawn:
    col: int
    row: int
    direction: int    # -1 left, +1 right
    skill: int        # 0..11
    color: int        # variante visual
    hp: int           # del tbl_guard_hp[level]

@dataclass(frozen=True, slots=True)
class Room:
    id: int           # 1..24 (0 = "no room" / wall)
    fg: tuple[int, ...]    # 30 tiles foreground (3 filas × 10 cols)
    bg: tuple[int, ...]    # 30 modifiers o overlays
    link_n: int       # room id N o 0
    link_s: int
    link_e: int
    link_w: int
    guards: tuple[GuardSpawn, ...]

@dataclass(frozen=True, slots=True)
class Level:
    number: int                # 1..14
    rooms: tuple[Room, ...]    # hasta 24 rooms (idx 0 = no-room sentinel)
    start_room: int
    start_col: int
    start_row: int
    start_direction: int
    events: tuple[Event, ...]  # shadow_appear, skeleton_wake, etc.
```

`Event` codifica triggers especiales:

```python
@dataclass(frozen=True, slots=True)
class Event:
    kind: EventKind      # SHADOW_MIRROR, SHADOW_STEAL, SHADOW_STEP,
                         # SKELETON_WAKE, MOUSE_APPEAR, VIZIER_INIT
    room: int
    col: int = 0
    row: int = 0
    extra: int = 0
```

## 2. Formato `levels.dat`

Verificado: `sizeof(level_type) == 2305` bytes (de `types.h`). 14
niveles. Total = 14 × 2305 = 32 270 bytes + checksum.

Layout aproximado por nivel (extraído de `level_type` en SDLPoP):

| Offset | Bytes | Campo |
|---|---|---|
| 0    | 720 | `fg[720]` — foreground tiles (24 rooms × 30 tiles) |
| 720  | 720 | `bg[720]` — modifiers / overlays |
| 1440 | ~256 | `doorlinks_1`, `doorlinks_2` — links plate↔gate |
| 1696 | 96  | `roomlinks[24]` — 4 bytes/room (N, S, E, W) |
| 1792 | 24  | `guards_tile[24]` |
| 1816 | 24  | `guards_dir[24]` |
| 1840 | 24  | `guards_x[24]` |
| 1864 | 24  | `guards_skill[24]` |
| 1888 | 24  | `guards_color[24]` |
| ...  | resto | reserved / specials |

> Layout exacto requiere parsear `data/levels.dat` real. SDLPoP no
> incluye el binario en el repo (es propiedad de Broderbund). Para
> obtenerlo:
>
> - Opción A: usuario aporta `LEVELS.DAT` del POP1 original.
> - Opción B: mods de la comunidad princed.org tienen dumps text
>   (`apoplexy` editor exporta `.plv`).
> - Opción C: hardcodear los 14 niveles a mano desde walkthroughs
>   (semi-canónico).

## 3. Tile encoding

Cada byte del `fg[]` codifica 1 tile:
- **5 bits bajos**: piece (0..31 — los `tiles_*` del enum)
- **3 bits altos**: modifier (variante visual o sub-state)

`bg[]` codifica modifiers extra (state inicial de gates, dirección de
spikes, etc.).

Helper canónico:

```python
def decode_tile(byte: int) -> tuple[int, int]:
    """Devuelve (piece, modifier)."""
    return byte & 0x1F, (byte >> 5) & 0x07
```

## 4. Parser

```python
# src/pop2026canon/infrastructure/levels_dat.py

LEVEL_BYTES = 2305

@dataclass(frozen=True, slots=True)
class RawLevel:
    fg: bytes           # 720
    bg: bytes           # 720
    doorlinks: bytes
    roomlinks: bytes    # 96
    guards_tile: bytes  # 24
    guards_dir: bytes
    guards_x: bytes
    guards_skill: bytes
    guards_color: bytes

def load_levels_dat(path: Path) -> tuple[RawLevel, ...]:
    data = path.read_bytes()
    if len(data) < LEVEL_BYTES * 14:
        raise ValueError(f"levels.dat truncado: {len(data)} bytes")
    out = []
    for i in range(14):
        chunk = data[i * LEVEL_BYTES : (i + 1) * LEVEL_BYTES]
        out.append(_parse_level(chunk))
    return tuple(out)


def _parse_level(chunk: bytes) -> RawLevel:
    return RawLevel(
        fg=chunk[0:720],
        bg=chunk[720:1440],
        doorlinks=chunk[1440:1696],
        roomlinks=chunk[1696:1792],
        guards_tile=chunk[1792:1816],
        guards_dir=chunk[1816:1840],
        guards_x=chunk[1840:1864],
        guards_skill=chunk[1864:1888],
        guards_color=chunk[1888:1912],
    )


def materialize_level(raw: RawLevel, level_number: int) -> Level:
    """Construye un Level inmutable desde el dump binario."""
    rooms = []
    for room_idx in range(24):
        fg_room = raw.fg[room_idx * 30 : (room_idx + 1) * 30]
        bg_room = raw.bg[room_idx * 30 : (room_idx + 1) * 30]
        # roomlinks[i] = (N, S, E, W) — 4 bytes
        links = raw.roomlinks[room_idx * 4 : room_idx * 4 + 4]
        # guards
        guard_tile = raw.guards_tile[room_idx]
        guard_dir = raw.guards_dir[room_idx]
        guard_x = raw.guards_x[room_idx]
        guard_skill = raw.guards_skill[room_idx]
        guard_color = raw.guards_color[room_idx]
        guards = ()
        if guard_tile != 0xFF:  # 0xFF = no guard
            row = guard_tile // 10
            col = guard_tile % 10
            hp = TBL_GUARD_HP[level_number - 1]
            guards = (GuardSpawn(
                col=col, row=row, direction=guard_dir,
                skill=guard_skill, color=guard_color, hp=hp,
            ),)
        rooms.append(Room(
            id=room_idx + 1,
            fg=tuple(b & 0x1F for b in fg_room),
            bg=tuple(b for b in bg_room),
            link_n=links[0], link_s=links[1],
            link_e=links[2], link_w=links[3],
            guards=guards,
        ))
    # Start position viene de un campo aparte del dat
    # (TODO: localizar el offset exacto)
    return Level(
        number=level_number,
        rooms=tuple(rooms),
        start_room=1, start_col=2, start_row=0, start_direction=-1,
        events=load_events_for_level(level_number),
    )
```

## 5. Eventos por nivel (`domain/events.py`)

Hardcoded — no están en `levels.dat`, son **lógica del juego**:

```python
EVENTS_PER_LEVEL: dict[int, tuple[Event, ...]] = {
    3: (
        # Skeleton wake en sala 1 cuando kid en cierta col
        Event(EventKind.SKELETON_WAKE, room=1, col=2),
    ),
    4: (
        # Mirror en sala 4. Al saltar a través, shadow nace
        Event(EventKind.SHADOW_MIRROR, room=4, col=4),
    ),
    5: (
        # Shadow steal potion en sala 24
        Event(EventKind.SHADOW_STEAL, room=24),
    ),
    6: (
        # Shadow step desde sala 1 cuando frame=43
        Event(EventKind.SHADOW_STEP, room=1, extra=43),
    ),
    8: (
        # Mouse aparece para abrir gate del exit
        Event(EventKind.MOUSE_APPEAR, room=24),  # TODO confirmar
    ),
    12: (
        # Shadow fusion en sala 15
        Event(EventKind.SHADOW_FUSION, room=15),
        # Vizier (Jaffar) spawn
        Event(EventKind.VIZIER_INIT, room=23),  # TODO confirmar
    ),
    13: (
        Event(EventKind.PRINCESS_REUNION, room=1),  # TODO
    ),
}
```

## 6. Navegación entre salas

Cuando el kid cruza un borde:

```python
def cross_border(char: Char, level: Level) -> Char:
    room = level.rooms[char.room - 1]  # rooms 1-indexed
    if char.curr_col < 0:
        target = room.link_w
        if target == 0: return bumped(char)
        return replace(char, room=target, curr_col=9)
    if char.curr_col > 9:
        target = room.link_e
        if target == 0: return bumped(char)
        return replace(char, room=target, curr_col=0)
    if char.curr_row < 0:
        target = room.link_n
        if target == 0: return bumped(char)
        return replace(char, room=target, curr_row=2)
    if char.curr_row > 2:
        target = room.link_s
        if target == 0: return death_by_falling(char)  # cayó al vacío
        return replace(char, room=target, curr_row=0)
    return char
```

## 7. Renderer ↔ Room

El renderer pinta sólo la sala donde está el kid (`game.kid.room`).
Cambio de sala = **flick** instantáneo (no scroll).

Para el efecto "ver la sala adyacente" en transiciones suaves
(opcional, no canónico), el renderer puede pintar la sala destino
desplazada — pero el motor canónico hace flick crudo.

## 8. Tests

`tests/canon/test_04_room_graph.py`:
- `load_levels_dat` con dump válido produce 14 levels
- `materialize_level` desde RawLevel produce 24 rooms con links
- `cross_border` cambia de sala correctamente
- Sin link en dirección = bumped
- Sin link sur = caída a la muerte (si action freefall) o blocked
- Cada nivel tiene su `events` correcto cargado

## 9. Riesgos

- **Acceso a `levels.dat`**: no en repo SDLPoP. Plan B: hardcoded a
  partir de mapas comunidad princed.org. Plan C: usuario aporta.
- **Layout exacto del 2305-byte record**: requiere cross-check con
  `apoplexy` editor o reverse del C struct.
- **Door links**: la mecánica de plate→gate puede requerir más bytes
  de los anticipados (256 estimados puede no ser exacto).

## 10. Estimación

3 días: 1 día parser binario, 1 día materializar Level + Room, 1 día
events + tests.
