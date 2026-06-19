"""Tests for app.engine.scorer."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.engine.scorer import Scorer


def test_score_over25_clamps_range():
    assert Scorer.score_over25(0.5) == 50.0
    assert Scorer.score_over25(1.5) == 100.0
    assert Scorer.score_over25(-0.5) == 0.0
    assert Scorer.score_over25(None) == 0.0


def test_score_btts_basic():
    assert Scorer.score_btts(0.8) == 80.0
    assert Scorer.score_btts(None) == 0.0


def test_score_xg_total():
    assert Scorer.score_xg(2.5, 2.5) == 100.0  # 5.0 total xG caps at 100
    assert Scorer.score_xg(1.0, 0.5) == 30.0
    assert Scorer.score_xg(None, 1.0) == 0.0


def test_score_odds_inverts_correctly():
    assert Scorer.score_odds(1.1) == 100.0
    assert Scorer.score_odds(2.3) == 0.0
    assert Scorer.score_odds(2.5) == 0.0  # above max
    assert Scorer.score_odds(None) == 0.0


def test_score_league_known_vs_unknown():
    assert Scorer.score_league("EPL") == 95.0
    assert Scorer.score_league("RANDOM_LEAGUE") == 60.0  # default


def test_calculate_composite_within_bounds():
    score = Scorer.calculate_composite(
        over25=0.7, btts=0.6, xg_home=1.8, xg_away=1.2, odds=1.8, league="EPL"
    )
    assert 0 <= score <= 100
    assert isinstance(score, int)


def test_categorize_pick():
    assert Scorer.categorize_pick(85) == "SAFE"
    assert Scorer.categorize_pick(77) == "VALUE"
    assert Scorer.categorize_pick(72) == "HIGH_RISK"
