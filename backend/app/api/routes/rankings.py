from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.source import Source
from app.models.benchmark import SourceProfile
from app.schemas.benchmark import RankedSourceResponse

router = APIRouter()

LIMIT = 20


def _build_ranked(sources_profiles, score_attr: str) -> List[RankedSourceResponse]:
    results = []
    for source, profile in sources_profiles:
        score = getattr(profile, score_attr, 0.0) if profile else 0.0
        results.append(
            RankedSourceResponse(
                id=source.id,
                name=source.name,
                url=source.url,
                source_type=source.source_type,
                status=source.status,
                score=score,
                profile=profile,
            )
        )
    results.sort(key=lambda x: x.score, reverse=True)
    return results


def _query(db: Session, score_col, limit: int):
    return (
        db.query(Source, SourceProfile)
        .outerjoin(SourceProfile, Source.id == SourceProfile.source_id)
        .filter(Source.status.in_(["active", "degraded"]))
        .order_by(desc(score_col))
        .limit(limit)
        .all()
    )


@router.get("", response_model=List[RankedSourceResponse])
def get_all_rankings(limit: int = Query(LIMIT, le=100), db: Session = Depends(get_db)):
    from app.models.benchmark import SourceProfile
    rows = (
        db.query(Source, SourceProfile)
        .outerjoin(SourceProfile, Source.id == SourceProfile.source_id)
        .filter(Source.status.in_(["active", "degraded"]))
        .limit(limit)
        .all()
    )
    return _build_ranked(rows, "reliability_pct")


@router.get("/italian", response_model=List[RankedSourceResponse])
def get_italian_rankings(limit: int = Query(LIMIT, le=100), db: Session = Depends(get_db)):
    rows = _query(db, SourceProfile.italian_score, limit)
    return _build_ranked(rows, "italian_score")


@router.get("/german", response_model=List[RankedSourceResponse])
def get_german_rankings(limit: int = Query(LIMIT, le=100), db: Session = Depends(get_db)):
    rows = _query(db, SourceProfile.german_score, limit)
    return _build_ranked(rows, "german_score")


@router.get("/movies", response_model=List[RankedSourceResponse])
def get_movie_rankings(limit: int = Query(LIMIT, le=100), db: Session = Depends(get_db)):
    rows = _query(db, SourceProfile.movie_score, limit)
    return _build_ranked(rows, "movie_score")


@router.get("/series", response_model=List[RankedSourceResponse])
def get_series_rankings(limit: int = Query(LIMIT, le=100), db: Session = Depends(get_db)):
    rows = _query(db, SourceProfile.series_score, limit)
    return _build_ranked(rows, "series_score")


@router.get("/anime", response_model=List[RankedSourceResponse])
def get_anime_rankings(limit: int = Query(LIMIT, le=100), db: Session = Depends(get_db)):
    rows = _query(db, SourceProfile.anime_score, limit)
    return _build_ranked(rows, "anime_score")
