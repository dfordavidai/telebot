"""FastAPI route definitions."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.logger import get_logger
from app.storage.database import get_db
from app.data.importer import CSVImporter
from app.models.match import Prediction
from app.services.roi import ROITracker

logger = get_logger(__name__)
router = APIRouter()


@router.get("/health")
def health():
    """Health check endpoint for Railway."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@router.post("/import")
def trigger_import(db_session: Session = Depends(get_db)):
    """Manually trigger a CSV import from data/latest.csv."""
    try:
        importer = CSVImporter()
        count = importer.import_matches(db_session)
        return {"imported": count}
    except Exception as e:
        logger.error(f"Manual import failed: {e}")
        raise HTTPException(status_code=500, detail="Import failed")


@router.get("/today")
def get_today(db_session: Session = Depends(get_db)):
    """Get today's generated picks."""
    today_start = datetime.combine(datetime.utcnow().date(), datetime.min.time())
    today_end = datetime.combine(datetime.utcnow().date(), datetime.max.time())

    predictions = (
        db_session.query(Prediction)
        .join(Prediction.match)
        .filter(Prediction.posted_at >= today_start, Prediction.posted_at <= today_end)
        .all()
    )

    return {
        "count": len(predictions),
        "picks": [
            {
                "match": f"{p.match.home} vs {p.match.away}",
                "league": p.match.league,
                "pick": p.pick,
                "confidence": p.confidence,
                "category": p.category,
            }
            for p in predictions
        ],
    }


@router.get("/stats")
def get_stats(days: int = 30, db_session: Session = Depends(get_db)):
    """Get ROI / performance stats over the given window (default 30 days)."""
    return ROITracker.calculate_roi(db_session, days=days)
