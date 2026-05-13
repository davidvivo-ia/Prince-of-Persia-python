# Legacy — Prince of Persia (1989) — referencia histórica

Este directorio actúa como **archivo histórico de solo lectura**. No contiene
el código fuente original de Jordan Mechner — ese código es propiedad
intelectual de su autor y Ubisoft, y se conserva en su repositorio público:

  https://github.com/jmechner/Prince-of-Persia-Apple-II

El presente proyecto **NO redistribuye** ese código. Lo que sí toma del
original es:

- La estructura **conceptual** del juego (mecánicas, ritmo, géneros de obstáculos).
- El **espíritu**: rotoscopía, físicas crueles, tiempo límite, sword fighting.
- Las **decisiones de diseño** documentadas por Mechner en sus diarios públicos
  (`The Making of Prince of Persia`, Stripe Press, 2020) y en el repositorio
  histórico antes citado.

## Inventario del original (resumen de su repositorio)

| Carpeta             | Contenido                                              |
|---------------------|--------------------------------------------------------|
| `01 POP Source`     | Núcleo del motor: lógica, animación, IA, combate       |
| `02 POP Disk`       | Rutinas de carga de niveles desde disquete             |
| `03 Disk Protection`| Protección anti-copia (irrelevante para nuestra v1.0)  |
| `04 Support`        | Editores y utilidades de Mechner                       |

- Lenguaje: ensamblador **6502** (Apple II), ~83% del repositorio.
- Año: 1985–1989. Liberado en 2012.
- Plataforma original: Apple II 128K, dos disquetes 5.25".

Para todo análisis funcional, ver
[`../docs/original_program_analysis.md`](../docs/original_program_analysis.md).
