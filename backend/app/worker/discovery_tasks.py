"""Discovery pipeline Celery tasks."""
from __future__ import annotations
import asyncio
import uuid
from datetime import datetime

from app.worker.celery_app import celery_app
from app.database import SessionLocal


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.worker.tasks.run_discovery")
def run_discovery(run_id: str):
    """Main discovery pipeline: crawl seeds, detect types, fingerprint, store candidates."""
    from app.models.discovery import DiscoveryRun, DiscoverySeed, DiscoveredSource, SourceFingerprint
    from app.discovery.crawler import crawl_url
    from app.discovery.detector import detect_source_type
    from app.discovery.fingerprinter import build_fingerprint

    db = SessionLocal()
    try:
        run = db.query(DiscoveryRun).filter(DiscoveryRun.id == uuid.UUID(run_id)).first()
        if not run:
            return {"error": "run not found"}

        run.status = "running"
        db.commit()

        seeds = db.query(DiscoverySeed).filter(DiscoverySeed.enabled == True).all()
        seeds_crawled = 0
        candidates_found = 0

        for seed in seeds:
            candidate_urls = _run(crawl_url(seed.url))
            seed.last_crawled = datetime.utcnow()
            seeds_crawled += 1

            for url in candidate_urls[:100]:
                # Skip if already known
                existing = db.query(DiscoveredSource).filter(DiscoveredSource.url == url).first()
                if existing:
                    continue

                detection = _run(detect_source_type(url))
                if detection["detected_type"] == "unknown" and not detection["http_status"]:
                    continue

                ds = DiscoveredSource(
                    run_id=uuid.UUID(run_id),
                    url=url,
                    name=detection.get("name"),
                    detected_type=detection["detected_type"],
                    status="candidate",
                    http_status=detection.get("http_status"),
                    response_time_ms=detection.get("response_time_ms"),
                    notes=detection.get("notes"),
                )
                db.add(ds)
                db.flush()

                fp_data = build_fingerprint(url, detection["detected_type"], detection.get("capabilities"))
                fp = SourceFingerprint(
                    discovered_source_id=ds.id,
                    **fp_data,
                )
                db.add(fp)
                candidates_found += 1

            db.commit()

        run.status = "completed"
        run.finished_at = datetime.utcnow()
        run.seeds_crawled = seeds_crawled
        run.candidates_found = candidates_found
        db.commit()

        return {"status": "completed", "seeds_crawled": seeds_crawled, "candidates_found": candidates_found}

    except Exception as e:
        if db:
            try:
                run = db.query(DiscoveryRun).filter(DiscoveryRun.id == uuid.UUID(run_id)).first()
                if run:
                    run.status = "failed"
                    run.notes = str(e)[:500]
                    db.commit()
            except Exception:
                pass
        raise
    finally:
        db.close()


@celery_app.task(name="app.worker.tasks.test_discovered_source")
def test_discovered_source(source_id: str):
    """Run type detection + connectivity test on a single discovered source."""
    from app.models.discovery import DiscoveredSource
    from app.discovery.detector import detect_source_type

    db = SessionLocal()
    try:
        ds = db.query(DiscoveredSource).filter(DiscoveredSource.id == uuid.UUID(source_id)).first()
        if not ds:
            return {"error": "not found"}

        detection = _run(detect_source_type(ds.url))
        ds.http_status = detection.get("http_status")
        ds.response_time_ms = detection.get("response_time_ms")
        ds.notes = detection.get("notes")
        ds.tested_at = datetime.utcnow()

        if detection.get("http_status") and detection["http_status"] < 400:
            ds.detected_type = detection["detected_type"]
            ds.status = "tested"
        else:
            ds.status = "dead"

        db.commit()
        return {"status": ds.status, "detected_type": ds.detected_type}
    finally:
        db.close()


@celery_app.task(name="app.worker.tasks.benchmark_discovered_source")
def benchmark_discovered_source(source_id: str):
    """Run a mini benchmark (5 ITA + 5 GER titles) against a discovered source."""
    from app.models.discovery import DiscoveredSource
    from app.models.benchmark import BenchmarkTitle
    from app.benchmarking.searcher import search_source

    db = SessionLocal()
    try:
        ds = db.query(DiscoveredSource).filter(DiscoveredSource.id == uuid.UUID(source_id)).first()
        if not ds:
            return {"error": "not found"}

        # Get 5 ITA + 5 GER benchmark titles
        ita_titles = db.query(BenchmarkTitle).filter(BenchmarkTitle.language_target == "ita").limit(5).all()
        ger_titles = db.query(BenchmarkTitle).filter(BenchmarkTitle.language_target == "ger").limit(5).all()
        titles = ita_titles + ger_titles

        if not titles:
            ds.notes = "No benchmark titles available"
            db.commit()
            return {"error": "no benchmark titles"}

        ita_hits = 0
        ger_hits = 0

        for title in ita_titles:
            result = _run(search_source(ds.detected_type, ds.url, title.title, None))
            if result.success and result.result_count > 0:
                ita_hits += 1

        for title in ger_titles:
            result = _run(search_source(ds.detected_type, ds.url, title.title, None))
            if result.success and result.result_count > 0:
                ger_hits += 1

        total = len(ita_titles) + len(ger_titles)
        ita_score = (ita_hits / len(ita_titles) * 100) if ita_titles else 0.0
        ger_score = (ger_hits / len(ger_titles) * 100) if ger_titles else 0.0
        overall = (ita_score + ger_score) / 2 if (ita_titles and ger_titles) else max(ita_score, ger_score)

        ds.italian_score = round(ita_score, 1)
        ds.german_score = round(ger_score, 1)
        ds.overall_score = round(overall, 1)
        ds.status = "benchmarked"
        ds.benchmarked_at = datetime.utcnow()
        db.commit()

        return {"ita_score": ds.italian_score, "ger_score": ds.german_score, "overall_score": ds.overall_score}
    finally:
        db.close()


@celery_app.task(name="app.worker.tasks.scheduled_discovery")
def scheduled_discovery():
    """Periodic task: create and run a discovery run if seeds exist."""
    from app.models.discovery import DiscoveryRun, DiscoverySeed
    db = SessionLocal()
    try:
        if db.query(DiscoverySeed).filter(DiscoverySeed.enabled == True).count() == 0:
            return {"skipped": "no enabled seeds"}
        run = DiscoveryRun(status="pending")
        db.add(run)
        db.commit()
        db.refresh(run)
        run_discovery.delay(str(run.id))
        return {"run_id": str(run.id)}
    finally:
        db.close()


@celery_app.task(name="app.worker.tasks.retest_discovered_sources")
def retest_discovered_sources():
    """Periodic task: retest candidate/tested sources that haven't been checked in 24h."""
    from app.models.discovery import DiscoveredSource
    from datetime import timedelta
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(hours=24)
        stale = db.query(DiscoveredSource).filter(
            DiscoveredSource.status.in_(["candidate", "tested"]),
            (DiscoveredSource.tested_at == None) | (DiscoveredSource.tested_at < cutoff),
        ).limit(50).all()
        for ds in stale:
            test_discovered_source.delay(str(ds.id))
        return {"dispatched": len(stale)}
    finally:
        db.close()
