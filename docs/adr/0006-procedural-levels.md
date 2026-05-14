# ADR 0006 — Niveles procedurales para escalar a 100

## Contexto

La v2.0 entregaba 12 niveles hand-crafted. El usuario pide una
campaña de 100. Tres caminos viables:

1. Diseñar 88 ``.poplv`` adicionales a mano.
2. Sustituir todo por un generador.
3. Híbrido: mantener los 12 narrativos como Acto I-parcial y generar
   los 88 restantes con semilla determinista.

## Decisión

**Opción 3 (híbrido)**.

- 12 niveles hand-crafted (`01_cell` … `12_jaffar`) — lo narrativo.
- 88 niveles procedurales generados por
  :mod:`pop2026.application.level_generator`.
- 4 actos de 25 niveles cada uno (Mazmorra, Prisión, Palacio, Torre).
- Curva de dificultad declarativa en
  :mod:`pop2026.application.difficulty`.
- Validación con BFS de :mod:`pop2026.domain.reachability` antes de
  servir el nivel; reintentos con perturbaciones; fallback a corredor
  desnudo si todo falla.
- Determinismo total por ``(level_index, seed)``.

## Consecuencias

- **+** El proyecto escala a 100 niveles sin trabajo de contenido
  manual proporcional.
- **+** Cada playthrough con la misma `--seed` es exactamente
  reproducible (importante para demo, tests, speedrun verification).
- **+** Los 12 narrativos preservan el "alma" del original; los 88
  procedurales aportan variedad y rejugabilidad.
- **−** Los procedurales pueden sentirse menos memorables que los
  narrativos. Mitigación: cinemáticas por acto, títulos temáticos,
  curva de dificultad cuidada.
- **−** Bug en el generador → todos los niveles afectados. Mitigación:
  reachability BFS + property tests con hypothesis (≥80 muestras).

## Alternativas consideradas y descartadas

- **Generación 100 % manual**: ~88 horas estimadas de diseño cuidado.
  No cabe en una iteración razonable y no aporta sobre el procedural
  validado.
- **Sustituir los 12 narrativos**: pierde la curva pedagógica
  cuidadosamente diseñada (sable → guardia → trampas → jefe).

## Implementación clave

- ``application/difficulty.py``: parámetros por
  ``(act, local_index)``; monótono por acto, escalón al cambiar.
- ``application/level_generator.py``: 4 fases (esqueleto, suelos,
  trampas, actores), validación, hasta 12 reintentos.
- ``application/level_source.py``: 1..12 → built-in; 13..100 → genera.
- ``application/campaign.py``: ``CAMPAIGN`` ahora 100 entradas con
  títulos derivados del acto.

## Métricas observadas tras la entrega

- 290+ tests verdes en menos de 2 s.
- Cobertura de dominio ≥ 90 %.
- Property test (hypothesis) confirma que ≥ 80 combinaciones
  ``(level_index, seed)`` aleatorias generan niveles reachable.
