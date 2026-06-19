"""Tests for app.engine.filters."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.engine.filters import MatchFilter


def test_rejects_missing_xg():
    assert MatchFilter.has_required_xg(None, 1.0) is False
    assert MatchFilter.has_required_xg(1.0, None) is False
    assert MatchFilter.has_required_xg(1.0, 1.0) is True


def test_rejects_odds_above_ceiling():
    assert MatchFilter.odds_in_range(2.3) is True
    assert MatchFilter.odds_in_range(2.31) is False
    assert MatchFilter.odds_in_range(None) is False


def test_rejects_unknown_league():
    assert MatchFilter.is_known_league("EPL") is True
    assert MatchFilter.is_known_league("MADE_UP_LEAGUE") is False
    assert MatchFilter.is_known_league(None) is False


def test_is_eligible_combines_all_checks():
    assert MatchFilter.is_eligible(
        xg_home=1.5, xg_away=1.2, odds=1.9, league="EPL"
    ) is True
    assert MatchFilter.is_eligible(
        xg_home=None, xg_away=1.2, odds=1.9, league="EPL"
    ) is False
    assert MatchFilter.is_eligible(
        xg_home=1.5, xg_away=1.2, odds=2.5, league="EPL"
    ) is False
    assert MatchFilter.is_eligible(
        xg_home=1.5, xg_away=1.2, odds=1.9, league="MADE_UP"
    ) is False
