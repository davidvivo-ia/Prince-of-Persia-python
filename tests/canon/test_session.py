"""Sesión de campaña: progresión de niveles, muerte→respawn, reloj global."""

from __future__ import annotations

from dataclasses import replace

from pop2026canon.application.session import Session, resolve_transition
from pop2026canon.domain.game import GameStatus, TimeRemaining


class TestSessionStart:
    def test_start_level_1(self) -> None:
        s = Session()
        g = s.start_game()
        assert g.level.number == 1
        assert g.kid.hp_max == 3

    def test_start_carries_hp_and_time(self) -> None:
        s = Session(level_number=5, hp_max=6, time=TimeRemaining(minutes=42, ticks=100))
        g = s.start_game()
        assert g.level.number == 5
        assert g.kid.hp_max == 6
        assert g.kid.hp_curr == 6, "Reapareces con la vida llena"
        assert g.time.minutes == 42


class TestLevelWon:
    def test_advances_to_next_level(self) -> None:
        s = Session(level_number=3)
        g = replace(s.start_game(), status=GameStatus.WON_LEVEL)
        s2, g2, outcome = resolve_transition(s, g)
        assert outcome == "card"
        assert s2.level_number == 4
        assert g2 is not None
        assert g2.level.number == 4

    def test_keeps_clock_across_levels(self) -> None:
        s = Session(level_number=1)
        g = s.start_game()
        g = replace(g, status=GameStatus.WON_LEVEL, time=TimeRemaining(minutes=50, ticks=3))
        _s2, g2, _ = resolve_transition(s, g)
        assert g2 is not None
        assert g2.time.minutes == 50, "El reloj NO se reinicia al pasar de nivel"

    def test_keeps_hp_max_gained(self) -> None:
        s = Session(level_number=1, hp_max=3)
        g = s.start_game()
        g = replace(g, kid=replace(g.kid, hp_max=5), status=GameStatus.WON_LEVEL)
        s2, g2, _ = resolve_transition(s, g)
        assert s2.hp_max == 5
        assert g2 is not None
        assert g2.kid.hp_max == 5


class TestDeath:
    def test_respawn_same_level_clock_running(self) -> None:
        s = Session(level_number=7, deaths=2)
        g = s.start_game()
        g = replace(g, status=GameStatus.LOST_DIED, time=TimeRemaining(minutes=30, ticks=0))
        s2, g2, outcome = resolve_transition(s, g)
        assert outcome == "respawn"
        assert s2.level_number == 7, "Morir NO retrocede de nivel"
        assert s2.deaths == 3
        assert g2 is not None
        assert g2.time.minutes == 30, "Morir no devuelve el tiempo perdido (canon)"
        assert g2.kid.hp_curr == g2.kid.hp_max

    def test_death_with_zero_clock_is_final(self) -> None:
        s = Session(level_number=7)
        g = s.start_game()
        g = replace(g, status=GameStatus.LOST_DIED, time=TimeRemaining(minutes=0, ticks=0))
        _, g2, outcome = resolve_transition(s, g)
        assert outcome == "timeout"
        assert g2 is None


class TestEndings:
    def test_won_game_is_victory(self) -> None:
        s = Session(level_number=14)
        g = replace(s.start_game(), status=GameStatus.WON_GAME)
        _, g2, outcome = resolve_transition(s, g)
        assert outcome == "victory"
        assert g2 is None

    def test_timeout_is_defeat(self) -> None:
        s = Session(level_number=2)
        g = replace(s.start_game(), status=GameStatus.LOST_TIMEOUT)
        _, _, outcome = resolve_transition(s, g)
        assert outcome == "timeout"


class TestFullCampaignPath:
    def test_thirteen_wins_reach_the_princess_level(self) -> None:
        """Ganar L1..L13 encadena hasta L14 con el mismo reloj."""
        s = Session()
        g = s.start_game()
        for _ in range(13):
            g = replace(g, status=GameStatus.WON_LEVEL)
            s, g2, outcome = resolve_transition(s, g)
            assert outcome == "card"
            assert g2 is not None
            g = g2
        assert g.level.number == 14
