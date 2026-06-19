"""
Low-level CSV parsing helpers.

CSVImporter (app/data/importer.py) owns the full load -> clean -> validate
pipeline. This module holds small, pure parsing helpers that are easy to
unit test in isolation and are reused by the importer.
"""

from typing import Optional
import pandas as pd
from app.core.logger import get_logger

logger = get_logger(__name__)


def normalize_league(value: Optional[str]) -> Optional[str]:
    """Uppercase and strip a league code, e.g. ' epl ' -> 'EPL'."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return str(value).strip().upper()


def normalize_team_name(value: Optional[str]) -> Optional[str]:
    """Title-case and strip a team name, e.g. 'arsenal fc' -> 'Arsenal Fc'."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return str(value).strip().title()


def parse_probability(value) -> Optional[float]:
    """
    Parse a probability-like field into a 0-1 float.

    Accepts plain decimals (0.62), percentages (62 or '62%'), and
    returns None for anything that can't be coerced.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None

    if isinstance(value, str):
        value = value.strip().rstrip("%")

    try:
        num = float(value)
    except (TypeError, ValueError):
        return None

    if num > 1.0:
        num = num / 100.0

    if num < 0.0 or num > 1.0:
        return None

    return num


def parse_float(value) -> Optional[float]:
    """Parse a generic numeric field, returning None on failure."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_date(value):
    """Parse a date-like field into a pandas Timestamp, or NaT on failure."""
    return pd.to_datetime(value, errors="coerce")
