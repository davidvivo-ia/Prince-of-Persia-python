"""Idioma de la interfaz: español (fuente) e inglés.

El código escribe los textos en español; ``tr(texto)`` devuelve la
traducción al idioma activo o el propio texto si no hay entrada (así
una cadena nueva nunca rompe nada: sale en español). Las cadenas con
variables se traducen antes de formatear (``tr("Muertes: {n}")``).

``set_language`` es el único estado global; la app lo fija al arrancar
y cada vez que cambia el ajuste ``language``.
"""

from __future__ import annotations

LANGUAGES: tuple[str, ...] = ("es", "en")
LANGUAGE_NAMES: dict[str, str] = {"es": "ESPAÑOL", "en": "ENGLISH"}

_state: dict[str, str] = {"code": "es"}

EN: dict[str, str] = {
    # --- menú principal / pausa -------------------------------------
    "Continuar": "Continue",
    "Nueva partida": "New game",
    "Niveles": "Levels",
    "Opciones": "Options",
    "Controles": "Controls",
    "Salir": "Quit",
    "PAUSA": "PAUSED",
    "Reanudar": "Resume",
    "Reiniciar nivel": "Restart level",
    "Mapa": "Map",
    "Salir al título": "Quit to title",
    # --- opciones ---------------------------------------------------
    "OPCIONES": "OPTIONS",
    "Modo de juego": "Game mode",
    "MODERNO": "MODERN",
    "CLÁSICO 1989": "CLASSIC 1989",
    "Moderno: rebobinar y reaparecer en la sala. Clásico: reglas de 1989.": (
        "Modern: rewind time and respawn in the room. Classic: 1989 rules."
    ),
    "Dificultad": "Difficulty",
    "NORMAL": "NORMAL",
    "DIFÍCIL": "HARD",
    "Difícil: guardias más diestros y 45 minutos. Vale para partidas nuevas.": (
        "Hard: deadlier guards and 45 minutes. Applies to new games."
    ),
    "Idioma": "Language",
    "ESPAÑOL": "ESPAÑOL",
    "ENGLISH": "ENGLISH",
    "Volumen general": "Master volume",
    "Música": "Music",
    "Efectos": "Sound effects",
    "Pantalla completa": "Fullscreen",
    "También F11 o Alt+Enter.": "Also F11 or Alt+Enter.",
    "Tamaño de ventana": "Window size",
    "Escalado": "Scaling",
    "SUAVE": "SMOOTH",
    "ENTERO NÍTIDO": "INTEGER SHARP",
    "Iluminación dinámica": "Dynamic lighting",
    "Partículas": "Particles",
    "Filtro CRT": "CRT filter",
    "Resplandor": "Bloom",
    "Halo de llamas y destellos.": "Glow of flames and sparks.",
    "Postproceso de cine": "Cinematic post-processing",
    "Grano de película y aberración cromática.": "Film grain and chromatic aberration.",
    "Sacudida de cámara": "Screen shake",
    "Accesibilidad.": "Accessibility.",
    "Destellos de daño": "Damage flashes",
    "Accesibilidad: fotosensibilidad.": "Accessibility: photosensitivity.",
    "Pistas": "Hints",
    "Fantasma del récord": "Record ghost",
    "Tu mejor carrera del nivel corre a tu lado.": "Your best run of the level races beside you.",
    "Récord: {t}": "Record: {t}",
    "¡Nuevo récord!": "New record!",
    "Tiempo total: {t}  ·  Muertes: {d}  ·  Medallas: {m}": (
        "Total time: {t}  ·  Deaths: {d}  ·  Medals: {m}"
    ),
    "Reloj siempre visible": "Always show timer",
    "Volver": "Back",
    "SÍ": "ON",
    "NO": "OFF",
    # --- controles --------------------------------------------------
    "CONTROLES": "CONTROLS",
    "Acción": "Action",
    "Teclado": "Keyboard",
    "Mando": "Gamepad",
    "Correr": "Run",
    "Saltar · trepar": "Jump · climb",
    "Salto largo parado": "Standing long jump",
    "Agacharse · descolgarse": "Crouch · climb down",
    "Agarrarse · paso corto": "Grab · careful step",
    "Atacar": "Attack",
    "Parar (en guardia)": "Parry (en garde)",
    "Rebobinar (moderno)": "Rewind (modern)",
    "Pausa · mapa": "Pause · map",
    "Reloj": "Timer",
    "Cruceta / stick": "D-pad / stick",
    "↑ + dirección": "↑ + direction",
    "A + dirección": "A + direction",
    "ESPACIO / J": "SPACE / J",
    "R  (mantener)": "R  (hold)",
    "Enter / B para volver": "Enter / B to go back",
    "Mando conectado": "Gamepad connected",
    # --- HUD / mapa -------------------------------------------------
    "NIVEL": "LEVEL",
    "GUARDIA": "GUARD",
    "ESQUELETO": "SKELETON",
    "SOMBRA": "SHADOW",
    "ENEMIGO": "ENEMY",
    "MAPA": "MAP",
    # --- tarjeta de nivel -------------------------------------------
    "NIVEL {n} de 14": "LEVEL {n} of 14",
    "Pulsa ENTER": "Press ENTER",
    "Despiertas en una mazmorra del palacio.": "You wake in a dungeon beneath the palace.",
    "El visir ha tomado el trono. Detenlo.": "The vizier has seized the throne. Stop him.",
    "Algo se mueve entre los huesos olvidados.": "Something stirs among forgotten bones.",
    "Un espejo... ¿muestra al enemigo verdadero?": "A mirror... does it show the true enemy?",
    "Tu propia sombra te roba lo que aún tenías.": "Your own shadow steals what you had left.",
    "Salta. La sombra salta contigo.": "Jump. The shadow jumps with you.",
    "Las montañas del palacio se alzan.": "The mountains of the palace rise.",
    "Cuevas. Un ratón inesperado.": "Caves. An unexpected mouse.",
    "La tumba. Más esqueletos. Camina rápido.": "The tomb. More skeletons. Walk fast.",
    "Torre arriba. No mires abajo.": "Up the tower. Don't look down.",
    "Una sala más. Y otra.": "One more room. And another.",
    "El visir Jaffar. La hora final.": "The vizier Jaffar. The final hour.",
    "Corre. Tu sombra ya no te imita.": "Run. Your shadow no longer mimics you.",
    "Ella te espera.": "She is waiting for you.",
    # --- temas (títulos de ambiente) --------------------------------
    "Mazmorra": "Dungeon",
    "Cuerpo de guardia": "Guardroom",
    "Osario": "Ossuary",
    "Galería del espejo": "Mirror gallery",
    "Salón del ladrón": "Thief's hall",
    "La escalinata": "The grand stair",
    "Entrañas de la montaña": "Heart of the mountain",
    "Cavernas": "Caverns",
    "La tumba": "The tomb",
    "La torre": "The tower",
    "Lo alto de la torre": "Top of the tower",
    "Dominios del visir": "The vizier's domain",
    "La huida final": "The final run",
    "Aposentos de la princesa": "The princess's chambers",
    # --- fin de nivel / muerte / final ------------------------------
    "NIVEL SUPERADO": "LEVEL COMPLETE",
    "Tiempo": "Time",
    "Muertes": "Deaths",
    "Enemigos derrotados": "Enemies defeated",
    "Pociones": "Potions",
    "Salas exploradas": "Rooms explored",
    "Tiempo rebobinado": "Time rewound",
    "¡nueva!": "new!",
    " para continuar": " to continue",
    "HAS MUERTO": "YOU DIED",
    "Muertes: {n} · el tiempo sigue corriendo": "Deaths: {n} · the clock keeps running",
    "Mantén LB": "Hold LB",
    "Mantén R": "Hold R",
    " para rebobinar el tiempo": " to rewind time",
    "{c} para reaparecer en esta sala": "{c} to respawn in this room",
    "{c} para reintentar el nivel": "{c} to retry the level",
    "VICTORIA": "VICTORY",
    "La princesa está a salvo.": "The princess is safe.",
    "Jaffar ha caído.": "Jaffar has fallen.",
    "Tiempo restante: {t}  ·  Muertes: {d}": "Time left: {t}  ·  Deaths: {d}",
    "Enter para volver al título": "Enter to return to the title",
    "TIEMPO AGOTADO": "TIME IS UP",
    "La princesa ha muerto.": "The princess is dead.",
    "El visir gana.": "The vizier wins.",
    # --- selección de nivel / medallas ------------------------------
    "NIVELES": "LEVELS",
    "Completado": "Completed",
    "Sin un rasguño": "Flawless",
    "Veloz": "Swift",
    "Explorador": "Explorer",
    "Medallas: ": "Medals: ",
    "Sin medallas todavía": "No medals yet",
    "Completa el nivel anterior para desbloquearlo": "Finish the previous level to unlock it",
    "{n} / {total} medallas": "{n} / {total} medals",
    "Enter / A: jugar · Esc / B: volver": "Enter / A: play · Esc / B: back",
    # --- pistas -----------------------------------------------------
    "↑ junto a una cornisa: salta y agárrate · ↑ otra vez para trepar": (
        "↑ by a ledge: jump and grab · ↑ again to climb"
    ),
    "A junto a una cornisa: salta y agárrate · A otra vez para trepar": (
        "A by a ledge: jump and grab · A again to climb"
    ),
    "Mantén SHIFT en el aire para agarrarte al borde": "Hold SHIFT in the air to grab the edge",
    "Mantén RB en el aire para agarrarte al borde": "Hold RB in the air to grab the edge",
    "SHIFT + dirección: paso corto sin caer · de espaldas al borde, ↓ para descolgarte": (
        "SHIFT + direction: careful step · back to the edge, ↓ to climb down"
    ),
    "RB + dirección: paso corto sin caer · de espaldas al borde, B para descolgarte": (
        "RB + direction: careful step · back to the edge, B to climb down"
    ),
    "Corriendo, ↑ hace un salto largo · ↑ + dirección parado salta 3 celdas": (
        "While running, ↑ makes a long jump · ↑ + direction standing jumps 3 tiles"
    ),
    "Corriendo, A hace un salto largo · A + dirección parado salta 3 celdas": (
        "While running, A makes a long jump · A + direction standing jumps 3 tiles"
    ),
    "ESPACIO ataca · ↑ para parar justo cuando él ataca · para y replica": (
        "SPACE attacks · ↑ parries right as he strikes · parry, then riposte"
    ),
    "X ataca · ↑ para parar justo cuando él ataca · para y replica": (
        "X attacks · A parries right as he strikes · parry, then riposte"
    ),
    "X ataca · A para parar justo cuando él ataca · para y replica": (
        "X attacks · A parries right as he strikes · parry, then riposte"
    ),
    "Sin espada, un guardia te mata de una estocada. Busca la espada": (
        "Unarmed, a guard kills you in one thrust. Find the sword"
    ),
    "¡Suelo suelto! No te pares encima": "Loose floor! Don't stand on it",
    "Las placas abren rejas durante un tiempo: ¡corre!": (
        "Pressure plates open gates for a while: run!"
    ),
    "Mantén R para rebobinar el tiempo": "Hold R to rewind time",
    "Mantén LB para rebobinar el tiempo": "Hold LB to rewind time",
    # --- cinemáticas ------------------------------------------------
    "Persia, hace mucho tiempo.": "Persia, a long time ago.",
    "Mientras el sultán guerrea en tierras lejanas,": (
        "While the sultan wages war in distant lands,"
    ),
    "su visir Jaffar se adueña del palacio.": "his vizier Jaffar seizes the palace.",
    "A la princesa le concede una hora para elegir:": "He grants the princess one hour to choose:",
    "casarse con él... o morir.": "marry him... or die.",
    "El joven que ella ama no tiene título ni nombre.": (
        "The young man she loves has neither title nor name."
    ),
    "Jaffar lo ha arrojado a las mazmorras.": "Jaffar has thrown him into the dungeons.",
    "Tiene sesenta minutos.": "He has sixty minutes.",
    "La arena se ha detenido.": "The sand has stopped running.",
    "Jaffar ha caído y el palacio despierta.": "Jaffar has fallen and the palace awakens.",
    "Ella nunca dudó.": "She never doubted.",
    "FIN": "THE END",
    "Enter para saltar": "Enter to skip",
}

_TABLES: dict[str, dict[str, str]] = {"es": {}, "en": EN}


def set_language(code: str) -> None:
    """Fija el idioma activo; un código desconocido vuelve al español."""
    _state["code"] = code if code in LANGUAGES else "es"


def language() -> str:
    return _state["code"]


def tr(text: str) -> str:
    """Traduce ``text`` (escrito en español) al idioma activo."""
    return _TABLES[_state["code"]].get(text, text)
