from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.source import Source, SourceTest, SourceScore
from app.schemas.source import StatsResponse

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


@router.get("/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    total = db.query(Source).count()
    active = db.query(Source).filter(Source.status == "active").count()
    degraded = db.query(Source).filter(Source.status == "degraded").count()
    dead = db.query(Source).filter(Source.status == "dead").count()
    unknown = db.query(Source).filter(Source.status == "unknown").count()

    avg_result = db.query(func.avg(SourceScore.overall_score)).scalar()
    avg_overall_score = float(avg_result) if avg_result else 0.0

    recent_tests = (
        db.query(SourceTest)
        .order_by(SourceTest.timestamp.desc())
        .limit(10)
        .all()
    )

    return StatsResponse(
        total=total,
        active=active,
        degraded=degraded,
        dead=dead,
        unknown=unknown,
        avg_overall_score=round(avg_overall_score, 2),
        recent_tests=recent_tests,
    )
