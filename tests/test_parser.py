"""Tests for app.data.parser."""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.data.parser import normalize_league, normalize_team_name, parse_probability, parse_float


def test_normalize_league():
    assert normalize_league(" epl ") == "EPL"
    assert normalize_league(None) is None


def test_normalize_team_name():
    assert normalize_team_name(" arsenal fc ") == "Arsenal Fc"
    assert normalize_team_name(None) is None


def test_parse_probability_handles_decimals_and_percentages():
    assert parse_probability(0.65) == 0.65
    assert parse_probability(65) == 0.65
    assert parse_probability("65%") == 0.65
    assert parse_probability("not a number") is None


def test_parse_float():
    assert parse_float("1.85") == 1.85
    assert parse_float(None) is None
    assert parse_float("nope") is None
