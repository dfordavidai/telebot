"""
Prediction model.

Note: Match and Prediction are defined together in app/models/match.py
because they're tightly coupled via a SQLAlchemy relationship and
splitting them risks circular-import issues with declarative Base.
This module re-exports Prediction so imports matching the spec's
folder structure (`from app.models.prediction import Prediction`)
continue to work.
"""

from app.models.match import Prediction

__all__ = ["Prediction"]
