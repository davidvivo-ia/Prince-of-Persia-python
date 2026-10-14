"""Audio sintetizado — sin un solo fichero de sonido.

Todo se genera con numpy al arrancar:

- **SFX** por síntesis sustractiva y aditiva: ruido filtrado con
  envolventes (pasos, golpes, polvo), parciales inarmónicos que decaen
  (el choque metálico de dos espadas, rejas, cuchillas), barridos de
  ruido (el silbido de la hoja), arpegios de campana (espada, victoria).
- **Música procedural** en modo *hijaz* (el sabor "persa" de la banda
  sonora clásica): bordón grave, laúd pulsado (síntesis aditiva con
  ataque de púa) y, en combate, una capa de darbuka con el ritmo
  *maqsum* que entra y sale con fundido.
- **Estéreo**: cada SFX se panoramiza según la posición en pantalla.

Si el mezclador no arranca (sin tarjeta de sonido, CI) todo queda en
silencio sin errores.
"""

from __future__ import annotations

import contextlib
import functools
from typing import Any

import numpy as np
import pygame

SR = 22050
SAMPLE_RATE = SR

# IDs (compartidos con application.audio_bridge)
SND_FOOTSTEP = 1
SND_JUMP = 2
SND_LAND_SOFT = 3
SND_LAND_HARD = 4
SND_GRAB = 5
SND_CLIMB = 6
SND_STRIKE = 7
SND_DEATH = 8
SND_DRINK = 9
SND_SPIKE = 10
SND_CHOMP = 11
SND_LOOSE_CRACK = 12
SND_HURT = 20
SND_CLASH = 21
SND_PARRY = 22
SND_GATE_OPEN = 23
SND_GATE_CLOSE = 24
SND_PLATE = 25
SND_PICKUP_SWORD = 26
SND_VICTORY_LEVEL = 27
SND_VICTORY_FINAL = 28
SND_MIRROR_BREAK = 29
SND_SHADOW_APPEAR = 30
SND_TILE_CRASH = 31
SND_REWIND = 32
SND_UI_MOVE = 33
SND_UI_SELECT = 34
SND_HIT_FLESH = 35

# ---------------------------------------------------------------------------
# Bloques de síntesis (float32 en [-1, 1], mono)
# ---------------------------------------------------------------------------


def _n(dur: float) -> int:
    return max(1, int(SR * dur))


def _time(n: int) -> Any:
    return np.arange(n, dtype=np.float32) / SR


def _rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def noise(dur: float, seed: int = 0) -> Any:
    return _rng(seed).uniform(-1.0, 1.0, _n(dur)).astype(np.float32)


def lowpass(x: Any, width: int) -> Any:
    """Filtro de caja (dos pasadas ≈ triangular). ``width`` en muestras."""
    if width <= 1:
        return x
    k = np.ones(width, dtype=np.float32) / width
    y = np.convolve(x, k, mode="same")
    return np.convolve(y, k, mode="same").astype(np.float32)


def highpass(x: Any, width: int) -> Any:
    return (x - lowpass(x, width)).astype(np.float32)


def env_exp(n: int, decay: float, attack: float = 0.002) -> Any:
    t = _time(n)
    env = np.exp(-t / max(1e-4, decay))
    a = _n(attack)
    if a > 1:
        env[:a] *= np.linspace(0.0, 1.0, a, dtype=np.float32)
    return env.astype(np.float32)


def sine(freq: float | Any, dur: float) -> Any:
    n = _n(dur)
    if isinstance(freq, (int, float)):
        return np.sin(2 * np.pi * float(freq) * _time(n)).astype(np.float32)
    phase = 2 * np.pi * np.cumsum(np.asarray(freq, dtype=np.float64)) / SR
    return np.sin(phase).astype(np.float32)


def glide(f0: float, f1: float, dur: float) -> Any:
    return sine(np.geomspace(f0, f1, _n(dur)), dur)


def partials(freq: float, dur: float, spec: list[tuple[float, float, float]]) -> Any:
    """Suma de parciales ``(ratio, amplitud, decay_s)``."""
    n = _n(dur)
    out = np.zeros(n, dtype=np.float32)
    for ratio, amp, decay in spec:
        out += amp * sine(freq * ratio, dur) * env_exp(n, decay)
    return out


def mix(*parts: Any) -> Any:
    n = max(len(p) for p in parts)
    out = np.zeros(n, dtype=np.float32)
    for p in parts:
        out[: len(p)] += p
    return out


def seq(*parts: tuple[float, Any]) -> Any:
    """Coloca fragmentos en instantes ``(t_segundos, señal)``."""
    n = max(_n(t) + len(p) for t, p in parts)
    out = np.zeros(n, dtype=np.float32)
    for t, p in parts:
        i = _n(t) if t > 0 else 0
        out[i : i + len(p)] += p
    return out


def normalize(x: Any, peak: float = 0.9) -> Any:
    m = float(np.max(np.abs(x))) if len(x) else 0.0
    if m < 1e-6:
        return x
    return (x * (peak / m)).astype(np.float32)


def fade_out(x: Any, dur: float = 0.01) -> Any:
    n = min(len(x), _n(dur))
    if n > 1:
        x = x.copy()
        x[-n:] *= np.linspace(1.0, 0.0, n, dtype=np.float32)
    return x


# ---------------------------------------------------------------------------
# Recetas de SFX
# ---------------------------------------------------------------------------


def _thump(dur: float, freq: float, seed: int, bright: int = 40) -> Any:
    n = _n(dur)
    body = sine(np.geomspace(freq * 1.6, freq, n), dur) * env_exp(n, dur * 0.35)
    grit = lowpass(noise(dur, seed), bright) * env_exp(n, dur * 0.2) * 2.5
    return mix(body, grit)


def _whoosh(dur: float, seed: int, width: int = 6, rise: float = 0.4) -> Any:
    n = _n(dur)
    t = np.linspace(0, 1, n, dtype=np.float32)
    shape = np.where(t < rise, t / rise, (1 - t) / (1 - rise)) ** 1.5
    return bandpass_noise(dur, seed, width, width * 6) * shape.astype(np.float32)


def bandpass_noise(dur: float, seed: int, lo_w: int, hi_w: int) -> Any:
    return highpass(lowpass(noise(dur, seed), lo_w), hi_w)


def _metal(freq: float, dur: float, seed: int) -> Any:
    ring = partials(
        freq,
        dur,
        [
            (1.0, 1.0, 0.35),
            (2.76, 0.6, 0.22),
            (5.40, 0.4, 0.12),
            (8.93, 0.25, 0.07),
            (13.3, 0.15, 0.04),
        ],
    )
    n = len(ring)
    hit = highpass(noise(0.03, seed), 3) * env_exp(_n(0.03), 0.008)
    return mix(ring * 0.6, hit * 0.8)[:n]


def _sfx_recipes() -> dict[int, Any]:
    r: dict[int, Any] = {}
    r[SND_FOOTSTEP] = _thump(0.07, 90, 1, 30) * 0.6
    r[SND_JUMP] = mix(_whoosh(0.16, 2, 5, 0.3) * 0.7, _thump(0.05, 140, 3, 20) * 0.4)
    r[SND_LAND_SOFT] = _thump(0.14, 70, 4, 40)
    r[SND_LAND_HARD] = mix(
        _thump(0.3, 55, 5, 60), lowpass(noise(0.25, 6), 8) * env_exp(_n(0.25), 0.06)
    )
    r[SND_GRAB] = highpass(noise(0.05, 7), 6) * env_exp(_n(0.05), 0.012)
    r[SND_CLIMB] = seq(
        (0.0, highpass(noise(0.04, 8), 6) * env_exp(_n(0.04), 0.01)),
        (0.18, _thump(0.08, 120, 9, 20) * 0.6),
        (0.34, highpass(noise(0.04, 10), 6) * env_exp(_n(0.04), 0.01)),
    )
    r[SND_STRIKE] = _whoosh(0.2, 11, 3, 0.35)
    r[SND_DEATH] = mix(glide(180, 60, 0.7) * env_exp(_n(0.7), 0.3) * 0.6, _thump(0.4, 50, 12, 70))
    r[SND_DRINK] = seq(
        *[
            (0.12 * i, glide(300 + 60 * i, 700 + 80 * i, 0.08) * env_exp(_n(0.08), 0.03) * 0.5)
            for i in range(4)
        ]
    )
    r[SND_SPIKE] = mix(
        _metal(1900, 0.25, 13) * 0.6, highpass(noise(0.12, 14), 4) * env_exp(_n(0.12), 0.03)
    )
    r[SND_CHOMP] = seq((0.0, _metal(900, 0.18, 15)), (0.07, _metal(760, 0.2, 16)))
    r[SND_LOOSE_CRACK] = mix(
        highpass(noise(0.08, 17), 5) * env_exp(_n(0.08), 0.015),
        lowpass(noise(0.35, 18), 30) * env_exp(_n(0.35), 0.12) * 1.6,
    )
    r[SND_TILE_CRASH] = mix(
        _thump(0.45, 45, 19, 80) * 1.2,
        lowpass(noise(0.5, 20), 6) * env_exp(_n(0.5), 0.15),
        seq(
            *[
                (0.05 + 0.04 * i, highpass(noise(0.03, 21 + i), 4) * env_exp(_n(0.03), 0.008) * 0.4)
                for i in range(6)
            ]
        ),
    )
    r[SND_HURT] = mix(
        glide(260, 150, 0.22) * env_exp(_n(0.22), 0.09) * 0.5,
        lowpass(noise(0.18, 30), 12) * env_exp(_n(0.18), 0.05),
    )
    r[SND_HIT_FLESH] = mix(
        _thump(0.12, 110, 31, 18), highpass(noise(0.06, 32), 8) * env_exp(_n(0.06), 0.015) * 0.6
    )
    r[SND_CLASH] = _metal(1450, 0.6, 33)
    r[SND_PARRY] = mix(_metal(1720, 0.5, 34), _metal(2310, 0.35, 35) * 0.5)
    r[SND_GATE_OPEN] = seq(
        *[(0.07 * i, _metal(520 + (i % 2) * 40, 0.06, 40 + i) * 0.35) for i in range(10)]
    )
    r[SND_GATE_CLOSE] = mix(
        seq(*[(0.025 * i, _metal(480, 0.04, 60 + i) * 0.3) for i in range(8)]),
        seq((0.22, mix(_metal(300, 0.5, 70), _thump(0.3, 60, 71, 50)))),
    )
    r[SND_PLATE] = mix(
        _thump(0.12, 160, 72, 15) * 0.8, highpass(noise(0.03, 73), 5) * env_exp(_n(0.03), 0.006)
    )
    r[SND_PICKUP_SWORD] = _arpeggio([0, 3, 4, 7, 12], 0.09, 440, 0.6, 80)
    r[SND_VICTORY_LEVEL] = _arpeggio([0, 1, 4, 5, 7, 12, 7, 12], 0.12, 293.66, 0.9, 90)
    r[SND_VICTORY_FINAL] = _arpeggio([0, 4, 7, 12, 16, 19, 24, 19, 24], 0.18, 293.66, 1.6, 100)
    r[SND_MIRROR_BREAK] = mix(
        *[_metal(2000 + 700 * k, 0.5, 110 + k) * 0.3 for k in range(6)],
        highpass(noise(0.4, 120), 3) * env_exp(_n(0.4), 0.1) * 0.5,
    )
    swell_n = _n(0.6)
    r[SND_SHADOW_APPEAR] = (
        glide(110, 220, 0.6) * np.linspace(0, 1, swell_n, dtype=np.float32) ** 2 * 0.6
        + lowpass(noise(0.6, 121), 20) * np.linspace(0, 1, swell_n, dtype=np.float32) ** 3
    )
    rew_n = _n(0.5)
    r[SND_REWIND] = (
        sine(np.full(rew_n, 220.0) + 60 * np.sin(np.linspace(0, 12 * np.pi, rew_n)), 0.5) * 0.25
        + bandpass_noise(0.5, 122, 4, 30) * 0.5
    ).astype(np.float32)
    r[SND_UI_MOVE] = partials(1400, 0.05, [(1, 1.0, 0.012)]) * 0.3
    r[SND_UI_SELECT] = seq(
        (0, partials(880, 0.08, [(1, 1, 0.03), (2, 0.4, 0.02)]) * 0.4),
        (0.06, partials(1320, 0.1, [(1, 1, 0.04), (2, 0.4, 0.02)]) * 0.4),
    )
    out = {}
    for k, v in r.items():
        peak = 0.95 if k in (SND_TILE_CRASH, SND_LAND_HARD, SND_DEATH) else 0.8
        if k == SND_REWIND:
            out[k] = normalize(v, 0.7)  # bucle: sin fundido
        else:
            out[k] = fade_out(normalize(v, peak))
    return out


HIJAZ = (0, 1, 4, 5, 7, 8, 10)
"""Semitonos del modo hijaz (frigio dominante) sobre la tónica."""


def _bell(freq: float, dur: float) -> Any:
    return partials(freq, dur, [(1, 1.0, 0.5), (2.0, 0.5, 0.3), (3.01, 0.3, 0.2), (4.2, 0.15, 0.1)])


def _arpeggio(steps: list[int], step: float, base: float, tail: float, seed: int) -> Any:
    _ = seed
    return seq(*[(i * step, _bell(base * 2 ** (s / 12), tail) * 0.5) for i, s in enumerate(steps)])


# ---------------------------------------------------------------------------
# Música procedural
# ---------------------------------------------------------------------------


def _pluck(freq: float, dur: float, seed: int) -> Any:
    """Laúd (oud) por síntesis aditiva: parciales con caída rápida +
    púa de ruido."""
    n = _n(dur)
    body = partials(
        freq,
        dur,
        [(1, 1.0, 0.45), (2, 0.55, 0.28), (3, 0.35, 0.18), (4, 0.22, 0.1), (5, 0.12, 0.06)],
    )
    pick = highpass(noise(0.01, seed), 3) * env_exp(_n(0.01), 0.002) * 0.4
    return mix(body, pick)[:n]


def _dum(seed: int) -> Any:
    n = _n(0.3)
    return sine(np.geomspace(120, 62, n), 0.3) * env_exp(n, 0.11) + lowpass(
        noise(0.3, seed), 40
    ) * env_exp(n, 0.03)


def _tek(seed: int) -> Any:
    n = _n(0.08)
    return highpass(noise(0.08, seed), 3) * env_exp(n, 0.018) * 0.7 + partials(
        1900, 0.08, [(1, 0.3, 0.02)]
    )


@functools.lru_cache(maxsize=4)
def music_layers(theme: str) -> tuple[Any, Any]:
    """``(base, combate)`` en bucle perfecto para el tema."""
    palace = theme == "palace"
    bpm = 92 if palace else 76
    beat = 60.0 / bpm
    bars = 8
    total = bars * 4 * beat
    n_total = _n(total)
    tonic = 220.0 if palace else 146.83  # A3 / D3
    rng = _rng(7 if palace else 3)

    # Bordón: tónica y quinta graves con respiración lenta.
    t = _time(n_total)
    lfo = 0.6 + 0.4 * np.sin(2 * np.pi * t / total * 2)
    drone = (
        np.sin(2 * np.pi * tonic / 2 * t) * 0.5
        + np.sin(2 * np.pi * tonic * 0.75 * t) * 0.25
        + np.sin(2 * np.pi * tonic / 4 * t) * 0.35
    ) * lfo
    drone += lowpass(noise(total, 11), 60) * 0.6 * lfo
    base = drone.astype(np.float32) * 0.35

    # Melodía: paseo aleatorio por el modo, con silencios.
    degree = 0
    pos = 0.0
    melody = np.zeros(n_total + _n(2.0), dtype=np.float32)
    while pos < total - beat * 0.5:
        dur_beats = rng.choice([0.5, 0.5, 1.0, 1.0, 1.5, 2.0])
        if rng.random() < (0.35 if palace else 0.5):
            pos += dur_beats * beat
            continue
        degree = int(np.clip(degree + rng.choice([-2, -1, -1, 0, 1, 1, 2]), -3, 9))
        octave, idx = divmod(degree, len(HIJAZ))
        semis = HIJAZ[idx] + 12 * octave
        freq = tonic * 2 ** (semis / 12)
        note = _pluck(freq, 1.6, int(pos * 1000)) * (0.5 if palace else 0.45)
        i = _n(pos)
        melody[i : i + len(note)] += note
        # Ornamento: nota de paso rápida antes de algunas notas
        if rng.random() < 0.25 and i > _n(0.08):
            grace = _pluck(freq * 2 ** (1 / 12), 0.3, int(pos * 997)) * 0.25
            j = i - _n(0.08)
            melody[j : j + len(grace)] += grace
        pos += dur_beats * beat
    # Cola que se sale del bucle: vuelve al principio (bucle sin costura)
    tail = melody[n_total:]
    melody = melody[:n_total]
    melody[: len(tail)] += tail
    base = base + melody

    # Capa de combate: darbuka maqsum (D T - T D - T -) + bordón tenso.
    combat = np.zeros(n_total + _n(0.5), dtype=np.float32)
    pattern = [("D", 0.0), ("T", 0.5), ("T", 1.5), ("D", 2.0), ("T", 3.0)]
    for bar in range(bars):
        for kind, b in pattern:
            i = _n((bar * 4 + b) * beat)
            hit = _dum(bar * 10 + int(b * 2)) if kind == "D" else _tek(bar * 10 + int(b * 2))
            combat[i : i + len(hit)] += hit * (0.9 if kind == "D" else 0.5)
        if rng.random() < 0.6:
            for b in (2.5, 3.5):
                i = _n((bar * 4 + b) * beat)
                hit = _tek(bar * 31 + int(b * 3)) * 0.3
                combat[i : i + len(hit)] += hit
    ctail = combat[n_total:]
    combat = combat[:n_total]
    combat[: len(ctail)] += ctail
    tremolo = 0.5 + 0.5 * np.sin(2 * np.pi * 6 * t)
    combat += (np.sin(2 * np.pi * tonic * 2 ** (1 / 12) * t) * 0.12 * tremolo).astype(np.float32)
    return normalize(base, 0.55), normalize(combat, 0.6)


# ---------------------------------------------------------------------------
# Motor
# ---------------------------------------------------------------------------


def _to_stereo_bytes(x: Any, width_ms: float = 0.0) -> bytes:
    pcm = np.clip(x, -1.0, 1.0)
    left = pcm
    right = pcm
    if width_ms > 0:
        d = _n(width_ms / 1000)
        right = np.concatenate([pcm[-d:], pcm[:-d]])
    st = np.empty(len(pcm) * 2, dtype=np.int16)
    st[0::2] = (left * 32767).astype(np.int16)
    st[1::2] = (right * 32767).astype(np.int16)
    return st.tobytes()


MUSIC_CHANNELS = (0, 1)
LOOP_CHANNEL = 2
AMBIENCE_CHANNEL = 3
AMBIENCE_GAIN = 0.45


# ---------------------------------------------------------------------------
# Ambiente por tema (bucles largos, muy por debajo de la música)
# ---------------------------------------------------------------------------

AMBIENCE_SECONDS = 9.0


def _lfo(n: int, hz: float, lo: float, hi: float, phase: float = 0.0) -> Any:
    t = _time(n)
    return (lo + (hi - lo) * (0.5 + 0.5 * np.sin(2 * np.pi * hz * t + phase))).astype(np.float32)


def _wind(n: int, seed: int, *, width: int, lo: float, hi: float, hz: float) -> Any:
    w = lowpass(noise(n / SR, seed), width) * _lfo(n, hz, lo, hi) * _lfo(n, hz * 2.7, 0.6, 1.0, 1.3)
    return w.astype(np.float32)


def _loopable(x: Any) -> Any:
    """Cruce suave entre el final y el principio para que el bucle no
    haga clic."""
    n = min(len(x) // 8, _n(0.4))
    if n < 2:
        return x
    x = x.copy()
    fade = np.linspace(0.0, 1.0, n, dtype=np.float32)
    x[:n] = x[:n] * fade + x[-n:] * (1.0 - fade)
    return x[:-n]


def _drops(n: int, seed: int, rate: float, *, bright: bool, echo: float) -> Any:
    """Goteras: pings sinusoidales esparcidos con un eco corto."""
    rng = _rng(seed)
    out = np.zeros(n, dtype=np.float32)
    count = max(1, int(rate * n / SR))
    for _ in range(count):
        i = int(rng.uniform(0, n - SR // 4))
        f = rng.uniform(1400.0, 2600.0) if bright else rng.uniform(700.0, 1500.0)
        d = rng.uniform(0.05, 0.14)
        ping = sine(f, 0.25) * env_exp(_n(0.25), d) * rng.uniform(0.25, 0.6)
        out[i : i + len(ping)] += ping[: max(0, n - i)]
    if echo > 0:
        delay = _n(0.19)
        echoed = np.zeros_like(out)
        echoed[delay:] = out[:-delay] * echo
        delay2 = _n(0.41)
        echoed[delay2:] += out[:-delay2] * echo * 0.5
        out = out + echoed
    return out


def ambience_layer(kind: str) -> Any:
    """Bucle de ambiente mono de ~9 s para un tema de nivel."""
    n = _n(AMBIENCE_SECONDS)
    seed = sum(ord(c) for c in kind)
    if kind == "drips":
        rumble = _wind(n, seed, width=400, lo=0.05, hi=0.12, hz=0.09)
        x = mix(rumble, _drops(n, seed, 1.6, bright=True, echo=0.35))
    elif kind == "cave":
        rumble = _wind(n, seed, width=600, lo=0.08, hi=0.16, hz=0.07)
        x = mix(rumble, _drops(n, seed, 1.1, bright=False, echo=0.55))
    elif kind == "wind":
        x = _wind(n, seed, width=90, lo=0.06, hi=0.2, hz=0.13)
    elif kind == "gale":
        x = mix(
            _wind(n, seed, width=40, lo=0.1, hi=0.32, hz=0.17),
            _wind(n, seed + 1, width=12, lo=0.0, hi=0.12, hz=0.31),
        )
    elif kind == "tomb":
        whisper = highpass(lowpass(noise(n / SR, seed + 2), 6), 40) * _lfo(n, 0.05, 0.0, 0.09, 2.0)
        x = mix(_wind(n, seed, width=700, lo=0.1, hi=0.18, hz=0.05), whisper)
    elif kind == "fire":
        rng = _rng(seed)
        crackle = np.zeros(n, dtype=np.float32)
        for _ in range(int(n / SR * 14)):
            i = int(rng.uniform(0, n - 400))
            pop = (
                noise(0.012, int(rng.uniform(0, 9999)))
                * env_exp(_n(0.012), 0.004)
                * rng.uniform(0.2, 0.7)
            )
            crackle[i : i + len(pop)] += pop
        hiss = lowpass(noise(n / SR, seed + 3), 5) * _lfo(n, 0.4, 0.05, 0.1)
        x = mix(crackle, hiss)
    elif kind == "rumble":
        x = mix(
            _wind(n, seed, width=900, lo=0.12, hi=0.26, hz=0.06),
            _drops(n, seed, 0.3, bright=False, echo=0.4) * 0.5,
        )
    elif kind == "garden":
        rng = _rng(seed)
        chimes = np.zeros(n, dtype=np.float32)
        for _ in range(5):
            i = int(rng.uniform(0, n - SR))
            f = float(rng.choice([1318.0, 1568.0, 1760.0, 2093.0]))
            c = partials(f, 0.9, [(1.0, 0.25, 0.5), (2.76, 0.08, 0.25)])
            chimes[i : i + len(c)] += c[: max(0, n - i)]
        x = mix(_wind(n, seed, width=150, lo=0.04, hi=0.14, hz=0.11), chimes)
    else:
        x = _wind(n, seed, width=90, lo=0.06, hi=0.2, hz=0.13)
    return _loopable(normalize(x, 0.5))


class AudioEngine:
    """SFX panoramizados + música en capas con fundidos."""

    def __init__(
        self, *, mute: bool = False, sfx_volume: float = 1.0, music_volume: float = 0.6
    ) -> None:
        self.mute = mute
        self.sfx_volume = sfx_volume
        self.music_volume = music_volume
        self._sounds: dict[int, pygame.mixer.Sound] = {}
        self._music: dict[str, tuple[pygame.mixer.Sound, pygame.mixer.Sound]] = {}
        self._theme: str | None = None
        self._combat = 0.0
        self._combat_target = 0.0
        self._fade = 1.0
        self._loop_id: int | None = None
        self._ambience: dict[str, pygame.mixer.Sound] = {}
        self._ambience_kind: str | None = None
        self.ok = False
        if mute:
            return
        with contextlib.suppress(pygame.error):
            current = pygame.mixer.get_init()
            if current and (current[0], current[2]) != (SR, 2):
                # pygame.init() abre el mezclador a 44.1 kHz: reabrirlo con
                # el formato de los buffers sintetizados.
                pygame.mixer.quit()
                current = None
            if not current:
                pygame.mixer.init(frequency=SR, size=-16, channels=2, buffer=512)
            init = pygame.mixer.get_init()
            if init and init[2] == 2 and init[0] == SR:
                pygame.mixer.set_num_channels(24)
                pygame.mixer.set_reserved(4)
                for sid, buf in _sfx_recipes().items():
                    self._sounds[sid] = pygame.mixer.Sound(buffer=_to_stereo_bytes(buf))
                self.ok = True

    # --- SFX -----------------------------------------------------------

    def play(self, sfx_id: int, pan: float = 0.0, volume: float = 1.0) -> None:
        if not self.ok or self.mute:
            return
        snd = self._sounds.get(sfx_id)
        if snd is None:
            return
        with contextlib.suppress(pygame.error):
            ch = snd.play()
            if ch is not None:
                v = max(0.0, min(1.0, volume * self.sfx_volume))
                p = max(-1.0, min(1.0, pan))
                ch.set_volume(v * min(1.0, 1.0 - p), v * min(1.0, 1.0 + p))

    def loop(self, sfx_id: int | None) -> None:
        """Sonido en bucle (rebobinado). ``None`` lo para."""
        if not self.ok or self._loop_id == sfx_id:
            return
        self._loop_id = sfx_id
        with contextlib.suppress(pygame.error):
            ch = pygame.mixer.Channel(LOOP_CHANNEL)
            if sfx_id is None:
                ch.fadeout(120)
            else:
                snd = self._sounds.get(sfx_id)
                if snd is not None:
                    ch.play(snd, loops=-1, fade_ms=60)
                    ch.set_volume(0.6 * self.sfx_volume)

    # --- ambiente --------------------------------------------------------

    def ambience(self, kind: str | None) -> None:
        """Fondo sonoro del nivel (goteras, viento, fuego...). ``None`` lo para."""
        if not self.ok or kind == self._ambience_kind:
            return
        self._ambience_kind = kind
        with contextlib.suppress(pygame.error):
            ch = pygame.mixer.Channel(AMBIENCE_CHANNEL)
            if kind is None:
                ch.fadeout(800)
                return
            if kind not in self._ambience:
                self._ambience[kind] = pygame.mixer.Sound(
                    buffer=_to_stereo_bytes(ambience_layer(kind), 9)
                )
            ch.play(self._ambience[kind], loops=-1, fade_ms=1200)
            ch.set_volume(AMBIENCE_GAIN * self.sfx_volume)

    # --- música --------------------------------------------------------

    def music(self, theme: str | None) -> None:
        """Arranca (o cambia) el tema: ``dungeon`` / ``palace`` / ``None``."""
        if not self.ok or theme == self._theme:
            return
        self._theme = theme
        with contextlib.suppress(pygame.error):
            base_ch = pygame.mixer.Channel(MUSIC_CHANNELS[0])
            combat_ch = pygame.mixer.Channel(MUSIC_CHANNELS[1])
            if theme is None:
                base_ch.fadeout(600)
                combat_ch.fadeout(600)
                return
            if theme not in self._music:
                base, combat = music_layers(theme)
                self._music[theme] = (
                    pygame.mixer.Sound(buffer=_to_stereo_bytes(base, 12)),
                    pygame.mixer.Sound(buffer=_to_stereo_bytes(combat, 7)),
                )
            b, c = self._music[theme]
            base_ch.play(b, loops=-1, fade_ms=900)
            combat_ch.play(c, loops=-1)
            combat_ch.set_volume(0.0)
            self._apply_music_volume()

    def combat(self, active: bool) -> None:
        self._combat_target = 1.0 if active else 0.0

    def duck(self, amount: float) -> None:
        """Baja la música (0..1) — p.ej. en pausa."""
        self._fade = max(0.0, min(1.0, 1.0 - amount))
        self._apply_music_volume()

    def set_volumes(self, sfx: float, music: float) -> None:
        self.sfx_volume = sfx
        self.music_volume = music
        self._apply_music_volume()
        if self.ok and self._ambience_kind is not None:
            with contextlib.suppress(pygame.error):
                pygame.mixer.Channel(AMBIENCE_CHANNEL).set_volume(AMBIENCE_GAIN * sfx)

    def update(self, dt: float) -> None:
        if not self.ok:
            return
        step = dt * (1.5 if self._combat_target > self._combat else 0.5)
        if self._combat < self._combat_target:
            self._combat = min(self._combat_target, self._combat + step)
        else:
            self._combat = max(self._combat_target, self._combat - step)
        self._apply_music_volume()

    def _apply_music_volume(self) -> None:
        if not self.ok:
            return
        with contextlib.suppress(pygame.error):
            v = self.music_volume * self._fade
            pygame.mixer.Channel(MUSIC_CHANNELS[0]).set_volume(v * (1.0 - 0.35 * self._combat))
            pygame.mixer.Channel(MUSIC_CHANNELS[1]).set_volume(v * self._combat)


class Beeper(AudioEngine):
    """Compatibilidad con el nombre antiguo."""


def is_audio_available() -> bool:
    return pygame.mixer.get_init() is not None
