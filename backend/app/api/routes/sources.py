import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.source import Source, SourceScore, SourceTest
from app.schemas.source import (
    SourceCreate,
    SourceResponse,
    SourceDetailResponse,
    SourceTestResponse,
)
from app.testers import get_tester
from app.scoring.engine import scoring_engine

router = APIRouter()


def _latest_score(source_id, db: Session):
    return (
        db.query(SourceScore)
        .filter(SourceScore.source_id == source_id)
        .order_by(desc(SourceScore.calculated_at))
        .first()
    )


def _build_response(source: Source, db: Session) -> SourceResponse:
    resp = SourceResponse.model_validate(source)
    resp.latest_score = _latest_score(source.id, db)
    return resp


@router.get("", response_model=List[SourceResponse])
def list_sources(
    status: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Source)
    if status:
        q = q.filter(Source.status == status)
    if source_type:
        q = q.filter(Source.source_type == source_type)
    sources = q.order_by(desc(Source.created_at)).all()
    return [_build_response(s, db) for s in sources]


@router.post("", response_model=SourceResponse, status_code=201)
def create_source(payload: SourceCreate, db: Session = Depends(get_db)):
    source = Source(**payload.model_dump())
    db.add(source)
    db.commit()
    db.refresh(source)

    from app.worker.tasks import test_source
    test_source.delay(str(source.id))

    return _build_response(source, db)


@router.get("/{source_id}", response_model=SourceDetailResponse)
def get_source(source_id: str, db: Session = Depends(get_db)):
    try:
        sid = uuid.UUID(source_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid UUID")

    source = db.query(Source).filter(Source.id == sid).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    recent_tests = (
        db.query(SourceTest)
        .filter(SourceTest.source_id == source.id)
        .order_by(desc(SourceTest.timestamp))
        .limit(50)
        .all()
    )

    resp = SourceDetailResponse.model_validate(source)
    resp.latest_score = _latest_score(source.id, db)
    resp.recent_tests = recent_tests
    return resp


@router.delete("/{source_id}", status_code=204)
def delete_source(source_id: str, db: Session = Depends(get_db)):
    try:
        sid = uuid.UUID(source_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid UUID")

    source = db.query(Source).filter(Source.id == sid).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    db.delete(source)
    db.commit()


@router.post("/{source_id}/test", response_model=SourceTestResponse)
async def run_test(source_id: str, db: Session = Depends(get_db)):
    try:
        sid = uuid.UUID(source_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid UUID")

    source = db.query(Source).filter(Source.id == sid).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    tester = get_tester(source.source_type)
    result = await tester.test(source.url, source.auth_key)

    test_record = SourceTest(
        source_id=source.id,
        timestamp=datetime.utcnow(),
        success=result.success,
        response_time_ms=result.response_time_ms,
        http_status=result.http_status,
        notes=result.notes,
        tester_type=result.tester_type,
    )
    db.add(test_record)
    source.last_checked = datetime.utcnow()

    recent_tests = (
        db.query(SourceTest)
        .filter(SourceTest.source_id == source.id)
        .order_by(desc(SourceTest.timestamp))
        .limit(50)
        .all()
    )
    scores = scoring_engine.calculate(recent_tests)
    db.add(SourceScore(source_id=source.id, calculated_at=datetime.utcnow(), **scores))

    if scores["reliability_score"] >= 80:
        source.status = "active"
    elif scores["reliability_score"] >= 40:
        source.status = "degraded"
    elif len(recent_tests) >= 3:
        source.status = "dead"

    db.commit()
    db.refresh(test_record)
    return test_record
