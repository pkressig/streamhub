import asyncio
import uuid
from datetime import datetime

from app.worker.celery_app import celery_app
from app.database import SessionLocal
from app.models.source import Source, SourceTest, SourceScore
from app.testers import get_tester
from app.scoring.engine import scoring_engine


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.worker.tasks.test_source")
def test_source(source_id: str):
    db = SessionLocal()
    try:
        source = db.query(Source).filter(Source.id == uuid.UUID(source_id)).first()
        if not source:
            return {"error": "source not found"}

        tester = get_tester(source.source_type)
        result = _run(tester.test(source.url, source.auth_key))

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
            .order_by(SourceTest.timestamp.desc())
            .limit(50)
            .all()
        )

        scores = scoring_engine.calculate(recent_tests)
        score_record = SourceScore(
            source_id=source.id, calculated_at=datetime.utcnow(), **scores
        )
        db.add(score_record)

        if scores["reliability_score"] >= 80:
            source.status = "active"
        elif scores["reliability_score"] >= 40:
            source.status = "degraded"
        elif len(recent_tests) >= 3:
            source.status = "dead"

        db.commit()
        return {"success": result.success, "response_time_ms": result.response_time_ms}
    finally:
        db.close()


@celery_app.task(name="app.worker.tasks.monitor_sources")
def monitor_sources():
    db = SessionLocal()
    try:
        sources = db.query(Source).all()
        for source in sources:
            test_source.delay(str(source.id))
        return {"dispatched": len(sources)}
    finally:
        db.close()
