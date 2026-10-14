"""Identidad visual de cada uno de los 14 niveles.

El POP1 original sólo distingue mazmorra y palacio (``tbl_level_type``).
Aquí cada nivel tiene además su propia atmósfera — paleta de la piedra,
luz ambiente, color de las antorchas, niebla, rayos de luz, partículas
ambientales y decoración de la pared — sin tocar la geometría ni las
reglas canon. Datos puros (sin pygame): los consumen ``backdrop``,
``tile_atlas`` y ``fx``.
"""

from __future__ import annotations

from dataclasses import dataclass

RGB = tuple[int, int, int]

PALACE_LEVELS: frozenset[int] = frozenset({4, 5, 6, 10, 11, 14})
"""Canon ``tbl_level_type``: 1 = palacio, 0 = mazmorra."""


def level_is_palace(number: int) -> bool:
    return number in PALACE_LEVELS


PARTICLE_KINDS: frozenset[str] = frozenset(
    {"dust", "drips", "embers", "sand", "petals", "spores", "ash", "moths"}
)
DECOR_KINDS: frozenset[str] = frozenset(
    {
        "cracks",
        "streaks",
        "moss",
        "chains",
        "rings",
        "cobwebs",
        "bones",
        "skull_niches",
        "stalactites",
        "roots",
        "crystals",
        "windows",
        "niches",
        "tile_band",
        "tapestry",
        "banners",
        "candles",
        "glyphs",
        "rubble",
        "roses",
        "veins",
    }
)
MASONRY: frozenset[str] = frozenset({"blocks", "rough", "marble", "brick"})
SKIES: frozenset[str] = frozenset({"night", "moon", "dusk", "dawn"})


@dataclass(frozen=True, slots=True)
class LevelTheme:
    key: str
    title: str
    """Nombre del ambiente (para el rótulo y el mapa)."""
    palace: bool
    masonry: str
    stone: RGB
    mortar: RGB
    hi: RGB
    accent: RGB
    tile_tint: RGB
    """Multiplicador (0-255) de la paleta de losas y columnas."""
    ambient: RGB
    torch: RGB
    fog: RGB
    shafts: int
    shaft_color: RGB
    rim: RGB
    lift: RGB
    """Negros levantados de la gradación de color."""
    particles: tuple[str, ...]
    decor: tuple[str, ...]
    sky: str = "night"
    stone_var: int = 12
    damp: float = 0.0
    """Manchas de humedad al pie de cada piso (0 = ninguna)."""


_DUNGEON_TILE = (255, 255, 255)

THEMES: dict[int, LevelTheme] = {
    1: LevelTheme(
        key="l1",
        title="Mazmorra",
        palace=False,
        masonry="blocks",
        stone=(92, 94, 122),
        mortar=(30, 30, 44),
        hi=(140, 142, 170),
        accent=(46, 74, 48),
        tile_tint=_DUNGEON_TILE,
        ambient=(84, 88, 124),
        torch=(255, 168, 64),
        fog=(46, 50, 66),
        shafts=1,
        shaft_color=(34, 42, 62),
        rim=(30, 32, 50),
        lift=(6, 7, 16),
        particles=("dust", "drips"),
        decor=("cracks", "streaks", "moss", "chains", "rings"),
        damp=0.5,
    ),
    2: LevelTheme(
        key="l2",
        title="Cuerpo de guardia",
        palace=False,
        masonry="blocks",
        stone=(86, 96, 112),
        mortar=(28, 32, 40),
        hi=(132, 146, 160),
        accent=(52, 70, 40),
        tile_tint=(246, 252, 255),
        ambient=(80, 90, 116),
        torch=(255, 160, 58),
        fog=(40, 48, 58),
        shafts=0,
        shaft_color=(30, 40, 56),
        rim=(30, 36, 48),
        lift=(6, 8, 14),
        particles=("dust", "embers"),
        decor=("cracks", "moss", "chains", "rings", "banners"),
        damp=0.35,
    ),
    3: LevelTheme(
        key="l3",
        title="Osario",
        palace=False,
        masonry="blocks",
        stone=(88, 98, 92),
        mortar=(26, 32, 28),
        hi=(132, 146, 136),
        accent=(60, 86, 46),
        tile_tint=(236, 248, 236),
        ambient=(72, 92, 84),
        torch=(220, 200, 120),
        fog=(40, 60, 46),
        shafts=0,
        shaft_color=(30, 46, 38),
        rim=(30, 44, 36),
        lift=(4, 10, 8),
        particles=("dust", "moths"),
        decor=("cracks", "cobwebs", "bones", "skull_niches", "moss"),
        damp=0.6,
    ),
    4: LevelTheme(
        key="l4",
        title="Galería del espejo",
        palace=True,
        masonry="marble",
        stone=(160, 144, 136),
        mortar=(70, 58, 56),
        hi=(204, 190, 180),
        accent=(40, 92, 140),
        tile_tint=(250, 246, 250),
        ambient=(116, 108, 124),
        torch=(255, 186, 100),
        fog=(44, 44, 60),
        shafts=2,
        shaft_color=(52, 60, 96),
        rim=(44, 40, 46),
        lift=(10, 8, 14),
        particles=("dust",),
        decor=("niches", "tile_band", "windows", "veins"),
        sky="moon",
    ),
    5: LevelTheme(
        key="l5",
        title="Salón del ladrón",
        palace=True,
        masonry="blocks",
        stone=(150, 124, 102),
        mortar=(66, 48, 40),
        hi=(186, 160, 132),
        accent=(40, 84, 130),
        tile_tint=(255, 250, 240),
        ambient=(122, 106, 110),
        torch=(255, 176, 80),
        fog=(52, 44, 40),
        shafts=1,
        shaft_color=(60, 52, 44),
        rim=(44, 36, 28),
        lift=(12, 7, 6),
        particles=("dust",),
        decor=("niches", "tile_band", "tapestry", "candles"),
    ),
    6: LevelTheme(
        key="l6",
        title="La escalinata",
        palace=True,
        masonry="marble",
        stone=(118, 122, 150),
        mortar=(46, 48, 68),
        hi=(170, 176, 206),
        accent=(60, 70, 150),
        tile_tint=(232, 236, 255),
        ambient=(96, 104, 140),
        torch=(255, 190, 110),
        fog=(40, 46, 72),
        shafts=2,
        shaft_color=(58, 70, 120),
        rim=(36, 40, 62),
        lift=(6, 8, 18),
        particles=("dust", "moths"),
        decor=("windows", "niches", "tile_band", "veins"),
        sky="moon",
    ),
    7: LevelTheme(
        key="l7",
        title="Entrañas de la montaña",
        palace=False,
        masonry="rough",
        stone=(110, 96, 84),
        mortar=(36, 30, 26),
        hi=(156, 140, 120),
        accent=(70, 72, 40),
        tile_tint=(252, 236, 220),
        ambient=(96, 86, 92),
        torch=(255, 164, 70),
        fog=(54, 46, 40),
        shafts=1,
        shaft_color=(56, 48, 40),
        rim=(44, 36, 30),
        lift=(10, 7, 6),
        particles=("sand", "dust"),
        decor=("roots", "cracks", "stalactites", "rubble"),
        damp=0.2,
    ),
    8: LevelTheme(
        key="l8",
        title="Cavernas",
        palace=False,
        masonry="rough",
        stone=(70, 78, 92),
        mortar=(18, 22, 30),
        hi=(116, 126, 146),
        accent=(40, 120, 130),
        tile_tint=(226, 236, 248),
        ambient=(58, 70, 96),
        torch=(255, 156, 70),
        fog=(30, 52, 60),
        shafts=0,
        shaft_color=(30, 50, 60),
        rim=(26, 46, 56),
        lift=(4, 8, 14),
        particles=("drips", "spores"),
        decor=("stalactites", "crystals", "cracks", "moss"),
        damp=0.7,
    ),
    9: LevelTheme(
        key="l9",
        title="La tumba",
        palace=False,
        masonry="blocks",
        stone=(132, 112, 82),
        mortar=(46, 36, 24),
        hi=(176, 156, 120),
        accent=(110, 70, 40),
        tile_tint=(255, 240, 210),
        ambient=(104, 90, 80),
        torch=(255, 170, 70),
        fog=(60, 50, 34),
        shafts=1,
        shaft_color=(64, 54, 36),
        rim=(46, 38, 26),
        lift=(12, 8, 4),
        particles=("sand", "dust"),
        decor=("glyphs", "skull_niches", "cobwebs", "bones", "cracks"),
    ),
    10: LevelTheme(
        key="l10",
        title="La torre",
        palace=True,
        masonry="blocks",
        stone=(132, 126, 140),
        mortar=(54, 50, 60),
        hi=(180, 174, 190),
        accent=(50, 80, 140),
        tile_tint=(244, 244, 255),
        ambient=(104, 104, 132),
        torch=(255, 182, 96),
        fog=(44, 46, 66),
        shafts=2,
        shaft_color=(56, 64, 104),
        rim=(40, 40, 58),
        lift=(8, 8, 16),
        particles=("dust",),
        decor=("windows", "tile_band", "niches"),
        sky="night",
    ),
    11: LevelTheme(
        key="l11",
        title="Lo alto de la torre",
        palace=True,
        masonry="blocks",
        stone=(150, 120, 120),
        mortar=(60, 44, 46),
        hi=(196, 166, 160),
        accent=(140, 70, 60),
        tile_tint=(255, 240, 236),
        ambient=(124, 100, 108),
        torch=(255, 176, 90),
        fog=(64, 44, 48),
        shafts=2,
        shaft_color=(90, 54, 48),
        rim=(50, 36, 36),
        lift=(14, 7, 8),
        particles=("dust", "embers"),
        decor=("windows", "tile_band", "tapestry"),
        sky="dawn",
    ),
    12: LevelTheme(
        key="l12",
        title="Dominios del visir",
        palace=False,
        masonry="brick",
        stone=(92, 66, 84),
        mortar=(30, 18, 28),
        hi=(140, 104, 126),
        accent=(130, 30, 40),
        tile_tint=(240, 220, 236),
        ambient=(92, 70, 96),
        torch=(255, 140, 70),
        fog=(56, 28, 40),
        shafts=0,
        shaft_color=(60, 30, 44),
        rim=(50, 28, 40),
        lift=(12, 4, 10),
        particles=("embers", "ash"),
        decor=("banners", "candles", "cracks", "chains"),
    ),
    13: LevelTheme(
        key="l13",
        title="La huida final",
        palace=False,
        masonry="blocks",
        stone=(96, 78, 78),
        mortar=(32, 22, 22),
        hi=(146, 118, 112),
        accent=(120, 40, 30),
        tile_tint=(244, 226, 220),
        ambient=(96, 72, 74),
        torch=(255, 140, 60),
        fog=(60, 34, 30),
        shafts=0,
        shaft_color=(60, 34, 30),
        rim=(56, 30, 28),
        lift=(14, 5, 4),
        particles=("ash", "embers", "dust"),
        decor=("rubble", "cracks", "chains", "streaks"),
    ),
    14: LevelTheme(
        key="l14",
        title="Aposentos de la princesa",
        palace=True,
        masonry="marble",
        stone=(146, 112, 114),
        mortar=(80, 56, 60),
        hi=(196, 164, 160),
        accent=(170, 60, 100),
        tile_tint=(255, 244, 244),
        ambient=(108, 88, 104),
        torch=(255, 176, 110),
        fog=(70, 50, 60),
        shafts=2,
        shaft_color=(84, 62, 76),
        rim=(54, 40, 46),
        lift=(14, 9, 12),
        particles=("petals", "dust"),
        decor=("roses", "niches", "candles", "windows", "veins"),
        sky="dawn",
    ),
}

_BY_KEY: dict[str, LevelTheme] = {t.key: t for t in THEMES.values()}


def theme_for(level_number: int) -> LevelTheme:
    """Tema del nivel (los números fuera de 1..14 usan el de su tipo)."""
    t = THEMES.get(level_number)
    if t is not None:
        return t
    return THEMES[4] if level_number in PALACE_LEVELS else THEMES[1]


def theme_by_key(key: str) -> LevelTheme:
    return _BY_KEY.get(key, THEMES[1])
