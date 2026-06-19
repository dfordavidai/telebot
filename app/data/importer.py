"""CSV data import and validation pipeline."""

from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd
from sqlalchemy.orm import Session
from app.core.logger import get_logger
from app.models.match import Match

logger = get_logger(__name__)

# Expected CSV columns
REQUIRED_COLUMNS = {
    "date", "league", "home", "away", "xg_home", "xg_away", "btts", "over25", "odds"
}

# Trusted leagues
TRUSTED_LEAGUES = {
    "PL", "EPL", "PREMIER_LEAGUE",
    "LA_LIGA", "LALIGA", "LIGA_EA_SPORTS",
    "SERIE_A", "SERIEA",
    "LIGUE_1", "LIGUE1",
    "BUNDESLIGA",
    "EREDIVISIE",
    "SUPER_LEAGUE", "SUPERLIG"
}


class CSVImporter:
    """Import and validate football matches from CSV."""
    
    def __init__(self, csv_path: str = "data/latest.csv"):
        self.csv_path = Path(csv_path)
    
    def load_csv(self) -> Optional[pd.DataFrame]:
        """Load CSV file with error handling."""
        try:
            if not self.csv_path.exists():
                logger.error(f"CSV file not found: {self.csv_path}")
                return None
            
            df = pd.read_csv(self.csv_path)
            logger.info(f"Loaded CSV with {len(df)} rows")
            return df
        except Exception as e:
            logger.error(f"Failed to load CSV: {e}")
            return None
    
    def clean_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names and types."""
        # Lowercase all columns
        df.columns = df.columns.str.lower().str.strip()
        
        # Type conversions
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["league"] = df["league"].str.upper().str.strip()
        df["home"] = df["home"].str.strip().str.title()
        df["away"] = df["away"].str.strip().str.title()
        df["xg_home"] = pd.to_numeric(df["xg_home"], errors="coerce")
        df["xg_away"] = pd.to_numeric(df["xg_away"], errors="coerce")
        df["btts"] = pd.to_numeric(df["btts"], errors="coerce")  # 0-1 probability
        df["over25"] = pd.to_numeric(df["over25"], errors="coerce")  # 0-1 probability
        df["odds"] = pd.to_numeric(df["odds"], errors="coerce")
        
        return df
    
    def validate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Filter rows for quality and completeness."""
        initial_count = len(df)
        
        # Check required columns
        missing_cols = REQUIRED_COLUMNS - set(df.columns)
        if missing_cols:
            logger.error(f"Missing columns: {missing_cols}")
            return df.iloc[0:0]  # Return empty dataframe
        
        # Remove NaN rows in critical columns
        critical_cols = ["date", "league", "home", "away", "xg_home", "xg_away", "odds"]
        df = df.dropna(subset=critical_cols)
        
        # Filter: odds <= 2.3
        df = df[df["odds"] <= 2.3]
        
        # Filter: trusted leagues only
        df = df[df["league"].isin(TRUSTED_LEAGUES)]
        
        # Filter: valid probabilities
        df = df[(df["btts"] >= 0) & (df["btts"] <= 1)]
        df = df[(df["over25"] >= 0) & (df["over25"] <= 1)]
        
        # Filter: future or today (don't import past matches)
        now = datetime.utcnow()
        df = df[df["date"] >= now]
        
        removed = initial_count - len(df)
        logger.info(f"Validation: removed {removed} rows, kept {len(df)}")
        
        return df
    
    def import_matches(self, db_session: Session) -> int:
        """Complete import pipeline: load → clean → validate → save."""
        
        df = self.load_csv()
        if df is None or len(df) == 0:
            return 0
        
        df = self.clean_columns(df)
        df = self.validate(df)
        
        if len(df) == 0:
            logger.warning("No valid matches after validation")
            return 0
        
        saved = 0
        for _, row in df.iterrows():
            try:
                # Check for duplicate (same league, home, away, date)
                existing = db_session.query(Match).filter(
                    Match.league == row["league"],
                    Match.home == row["home"],
                    Match.away == row["away"],
                    Match.date == row["date"]
                ).first()
                
                if existing:
                    logger.debug(f"Duplicate match skipped: {row['home']} vs {row['away']}")
                    continue
                
                match = Match(
                    date=row["date"],
                    league=row["league"],
                    home=row["home"],
                    away=row["away"],
                    xg_home=float(row["xg_home"]),
                    xg_away=float(row["xg_away"]),
                    btts=float(row["btts"]),
                    over25=float(row["over25"]),
                    odds=float(row["odds"]),
                    status="pending"
                )
                db_session.add(match)
                saved += 1
            except Exception as e:
                logger.error(f"Failed to save match: {e}")
                continue
        
        try:
            db_session.commit()
            logger.info(f"Imported {saved} new matches")
        except Exception as e:
            logger.error(f"Commit failed: {e}")
            db_session.rollback()
            return 0
        
        return saved
