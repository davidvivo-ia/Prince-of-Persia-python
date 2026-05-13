# Postmortem — pop2026 (mayo 2026)

Reimplementar Prince of Persia treinta y siete años después es una
forma honesta de medir el progreso del oficio.

**Qué se ganó**. Empezamos sin un proyecto y terminamos con un juego
completo, jugable, empaquetado con `uv`, testado con cobertura ≥90 %
en el dominio, tipado estricto, formato y lint limpios, modo demo
determinista, CI multipython, ADRs y postmortem incluidos. En 1989
todo eso eran libros sin escribir; hoy son flags por defecto. La
arquitectura hexagonal separa físicas testeables del SDL real: lo que
Mechner depuraba ejecutando el Apple II y mirando, nosotros lo hacemos
con `pytest` corriendo en 0,5 s.

**Qué se perdió**. La textura del original. La rotoscopía nace de
filmar al hermano corriendo y calcar fotograma a fotograma; eso no se
sustituye con interpolación geométrica por mucho gusto que se le ponga
a la paleta. Tampoco el peso del momento: en POP cada salto era una
apuesta porque la consola podía reiniciar. Hoy un `Ctrl+R` y vuelta a
empezar. Hay algo *éticamente* distinto en jugar bajo riesgo de
pérdida real.

**Qué dice del oficio**. Que las herramientas se han abaratado tres
órdenes de magnitud (tiempo, dinero, fricción), pero el corazón del
ejercicio sigue siendo el mismo: decidir qué dejar fuera. Mechner
escribió un libro entero sobre las cinco veces que estuvo a punto de
abandonar; nosotros disponemos de generadores de plantillas y demos
deterministas, pero la decisión "tres niveles bien hechos antes que
doce a medias" es exactamente la suya. La caja de herramientas crece;
el juicio no.

Cuarenta años después, lo que envejece mejor no son los píxeles, son
las decisiones.
