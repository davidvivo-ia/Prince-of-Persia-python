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

---

## Adenda v3.0 — De 12 niveles a 100

Lo más difícil de pasar de 12 a 100 niveles no fue el generador
procedural. Fue **renunciar a que cada nivel tenga título narrativo
propio**. Los 12 narrativos hand-crafted siguen ahí porque son el
"alma": tutorial, sable, primer guardia, primera trampa, primer jefe.
Los 88 restantes son repetición temática con dificultad creciente:
cuatro actos, cuatro músicas, cuatro cinemáticas. La curva la dicta
una tabla declarativa, no la imaginación.

Lo que se ganó: rejugabilidad determinista (`--seed N` reproduce
exactamente la misma campaña), escalabilidad (subir a 200 niveles es
cambiar una constante), mantenibilidad (un bug en el generador se
arregla una vez, no 88 veces).

Lo que se perdió: el cariño por nivel. El nivel 67 no es memorable
como el "Nivel 8 con el espejo" del original. Pero no pretende serlo:
es una repetición rítmica del Acto III. La memorabilidad vive en los
actos y en sus cinemáticas, no en cada pasillo individual.

Si tuviera que elegir entre 12 niveles cuidados y 100 generados, me
quedo con los 12. Aquí están los dos: la primera capa narrativa más
una segunda capa repetitiva-pero-rigurosa para quien quiera correr 100
pasillos sin parar.
