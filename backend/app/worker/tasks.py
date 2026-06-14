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


@celery_app.task(name="app.worker.tasks.run_benchmark")
def run_benchmark(run_id: str):
    """Run all benchmark titles against all active sources, then update profiles."""
    from app.models.benchmark import BenchmarkTitle, BenchmarkResult, BenchmarkRun
    from app.benchmarking.searcher import search_source
    from app.benchmarking.profiler import build_profile

    db = SessionLocal()
    try:
        run = db.query(BenchmarkRun).filter(BenchmarkRun.id == uuid.UUID(run_id)).first()
        if not run:
            return {"error": "run not found"}

        run.status = "running"
        db.commit()

        sources = db.query(Source).filter(Source.status.in_(["active", "degraded"])).all()
        titles = db.query(BenchmarkTitle).all()

        if not sources or not titles:
            run.status = "completed"
            run.finished_at = datetime.utcnow()
            run.notes = "No active sources or no benchmark titles"
            db.commit()
            return {"status": "completed", "sources": 0, "titles": 0}

        results_added = 0
        for source in sources:
            for title in titles:
                result = _run(
                    search_source(
                        source.source_type, source.url, title.title, source.auth_key
                    )
                )
                br = BenchmarkResult(
                    source_id=source.id,
                    benchmark_id=title.id,
                    run_id=uuid.UUID(run_id),
                    success=result.success,
                    result_count=result.result_count,
                    response_time_ms=result.response_time_ms,
                    duplicate_count=result.duplicate_count,
                    tested_at=datetime.utcnow(),
                )
                db.add(br)
                results_added += 1

        db.flush()

        # Rebuild profiles for all tested sources
        for source in sources:
            build_profile(source.id, db)

        run.status = "completed"
        run.finished_at = datetime.utcnow()
        run.sources_tested = len(sources)
        run.titles_tested = len(titles)
        run.notes = f"{results_added} results recorded"
        db.commit()

        return {
            "status": "completed",
            "sources": len(sources),
            "titles": len(titles),
            "results": results_added,
        }
    except Exception as e:
        if db:
            try:
                run = db.query(BenchmarkRun).filter(BenchmarkRun.id == uuid.UUID(run_id)).first()
                if run:
                    run.status = "failed"
                    run.notes = str(e)[:500]
                    db.commit()
            except Exception:
                pass
        raise
    finally:
        db.close()


@celery_app.task(name="app.worker.tasks.nightly_benchmark")
def nightly_benchmark():
    """Nightly task: create and run a full benchmark."""
    from app.models.benchmark import BenchmarkRun, BenchmarkTitle
    db = SessionLocal()
    try:
        if db.query(BenchmarkTitle).count() == 0:
            return {"skipped": "no benchmark titles"}
        run = BenchmarkRun(status="pending")
        db.add(run)
        db.commit()
        db.refresh(run)
        run_benchmark.delay(str(run.id))
        return {"run_id": str(run.id)}
    finally:
        db.close()
