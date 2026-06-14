"""Discovery pipeline Celery tasks — v0.4 with quality gate."""
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


# ── Main pipeline ─────────────────────────────────────────────────────────────

@celery_app.task(name="app.worker.tasks.run_discovery")
def run_discovery(run_id: str, deep: bool = False):
    """Crawl seeds → noise-filter → classify → store only passing candidates."""
    from app.models.discovery import DiscoveryRun, DiscoverySeed, DiscoveredSource, SourceFingerprint, DiscoveryRejected
    from app.discovery.classifier import classify
    from app.discovery.noise_filter import check as noise_check
    from app.discovery.fingerprinter import build_fingerprint

    url_limit = 500 if deep else 200

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
        rejected_count = 0
        bred_count = 0

        for seed in seeds:
            raw_urls = _run(_crawl_seed_async(seed, deep=deep))
            seed.last_crawled = datetime.utcnow()
            seeds_crawled += 1

            for url in raw_urls[:url_limit]:
                # 1 — noise filter (no network needed)
                passes, rejection_reason = noise_check(url, seed.url)
                if not passes:
                    _log_rejection(db, url, rejection_reason, seed.url)
                    rejected_count += 1
                    continue

                # 2 — already in candidates table?
                if db.query(DiscoveredSource).filter(DiscoveredSource.url == url).first():
                    continue

                # 3 — classify (network probe)
                clf = _run(classify(url))

                # 4 — quality gate: only store if we have a real type OR high-confidence generic
                if not _passes_quality_gate(clf):
                    _log_rejection(db, url, "low_confidence_generic", seed.url)
                    rejected_count += 1
                    continue

                # 5 — store passing candidate
                ds = DiscoveredSource(
                    run_id=uuid.UUID(run_id),
                    url=url,
                    name=clf.name or None,
                    detected_type=clf.detected_type,
                    detection_family=clf.detected_family,
                    confidence=clf.confidence,
                    detection_reason=clf.detection_reason,
                    detection_method=clf.detection_method,
                    status="candidate",
                    http_status=clf.http_status,
                    response_time_ms=clf.response_time_ms,
                    notes=clf.notes,
                )
                db.add(ds)
                db.flush()

                fp_data = build_fingerprint(url, clf.detected_type, clf.capabilities)
                db.add(SourceFingerprint(discovered_source_id=ds.id, **fp_data))
                bred_count += _breed_seeds(db, ds, seed)
                candidates_found += 1

            db.commit()

        run.status = "completed"
        run.finished_at = datetime.utcnow()
        run.seeds_crawled = seeds_crawled
        run.candidates_found = candidates_found
        run.notes = f"{rejected_count} URLs rejected by quality gate; {bred_count} seeds bred"
        db.commit()

        return {
            "status": "completed",
            "seeds_crawled": seeds_crawled,
            "candidates_found": candidates_found,
            "rejected": rejected_count,
            "bred": bred_count,
        }

    except Exception as e:
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


async def _crawl_seed_async(seed, deep: bool = False) -> list[str]:
    """Route a seed to the right crawler based on seed_type."""
    import re as _re
    from app.discovery.crawler import crawl_url, crawl_github_repo, crawl_reddit, crawl_github_search, crawl_github_user

    timeout = 30.0 if deep else 15.0

    if seed.seed_type in ("github_repo", "github"):
        m = _re.match(r"https?://github\.com/([^/]+)/([^/?#]+)", seed.url)
        if m:
            return await crawl_github_repo(m.group(1), m.group(2), timeout=timeout)
        return []
    if seed.seed_type == "github_search":
        from urllib.parse import urlparse, parse_qs, unquote_plus
        qs = parse_qs(urlparse(seed.url).query)
        query = unquote_plus(qs.get("q", [""])[0])
        if query:
            return await crawl_github_search(query, timeout=timeout)
        return []
    if seed.seed_type == "github_user":
        m = _re.match(r"https?://github\.com/([^/]+)/?", seed.url)
        if m:
            return await crawl_github_user(m.group(1))
        return []
    if seed.seed_type == "reddit":
        return await crawl_reddit(seed.url)
    return await crawl_url(seed.url, timeout=timeout)


def _breed_seeds(db, ds, seed) -> int:
    """Derive new seeds from a quality-gate-passing candidate. Returns # added."""
    from app.models.discovery import DiscoverySeed
    import re as _re
    from urllib.parse import urlparse

    if seed.breed_depth >= 3:
        return 0

    new_seeds = []
    next_depth = seed.breed_depth + 1

    if seed.seed_type == "github_repo":
        m = _re.match(r"https?://github\.com/([^/]+)/", seed.url)
        if m:
            owner = m.group(1)
            new_seeds.append({
                "url": f"https://github.com/{owner}",
                "label": f"GitHub user: {owner}",
                "seed_type": "github_user",
                "category": seed.category,
                "parent_seed_id": seed.id,
                "is_bred": True,
                "breed_depth": next_depth,
            })

    if ds.detected_type == "stremio_manifest":
        parsed = urlparse(ds.url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        if base.rstrip("/") != ds.url.rstrip("/"):
            new_seeds.append({
                "url": base,
                "label": f"Stremio host: {parsed.netloc}",
                "seed_type": "url",
                "category": "stremio_ecosystem",
                "parent_seed_id": seed.id,
                "is_bred": True,
                "breed_depth": next_depth,
            })

    if ds.detected_type in ("torznab", "newznab", "jackett", "prowlarr", "nzbhydra", "bitmagnet"):
        parsed = urlparse(ds.url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        new_seeds.append({
            "url": base,
            "label": f"Indexer host: {parsed.netloc}",
            "seed_type": "url",
            "category": seed.category or "usenet",
            "parent_seed_id": seed.id,
            "is_bred": True,
            "breed_depth": next_depth,
        })

    added = 0
    for sd_data in new_seeds:
        if not db.query(DiscoverySeed).filter(DiscoverySeed.url == sd_data["url"]).first():
            db.add(DiscoverySeed(**sd_data))
            added += 1
    return added


def _passes_quality_gate(clf) -> bool:
    """Return True if classification is good enough to store."""
    if clf.detected_type in (
        "torznab", "newznab", "rss", "stremio_manifest",
        "torrentio_family", "comet_family", "mediafusion_family",
        "stremthru_family", "aiostreams_family",
        "jackett", "prowlarr", "nzbhydra", "bitmagnet",
    ):
        return True
    if clf.detected_type == "generic_http" and clf.confidence >= 75:
        return True
    return False


def _log_rejection(db, url: str, reason: str, seed: str | None) -> None:
    from app.models.discovery import DiscoveryRejected
    from sqlalchemy.exc import IntegrityError
    try:
        entry = DiscoveryRejected(url=url, rejection_reason=reason, source_seed=seed)
        db.add(entry)
        db.flush()
    except Exception:
        db.rollback()


# ── Per-source actions ────────────────────────────────────────────────────────

@celery_app.task(name="app.worker.tasks.test_discovered_source")
def test_discovered_source(source_id: str):
    """Re-run classifier on a single discovered source."""
    from app.models.discovery import DiscoveredSource
    from app.discovery.classifier import classify

    db = SessionLocal()
    try:
        ds = db.query(DiscoveredSource).filter(DiscoveredSource.id == uuid.UUID(source_id)).first()
        if not ds:
            return {"error": "not found"}

        clf = _run(classify(ds.url))
        ds.http_status = clf.http_status
        ds.response_time_ms = clf.response_time_ms
        ds.notes = clf.notes
        ds.confidence = clf.confidence
        ds.detection_reason = clf.detection_reason
        ds.detection_method = clf.detection_method
        ds.detection_family = clf.detected_family
        ds.tested_at = datetime.utcnow()

        if clf.http_status and clf.http_status < 400:
            ds.detected_type = clf.detected_type
            ds.status = "tested"
        else:
            ds.status = "dead"

        db.commit()
        return {"status": ds.status, "detected_type": ds.detected_type, "confidence": ds.confidence}
    finally:
        db.close()


@celery_app.task(name="app.worker.tasks.benchmark_discovered_source")
def benchmark_discovered_source(source_id: str):
    """Mini benchmark (5 ITA + 5 GER) — skips generic_http and low-confidence sources."""
    from app.models.discovery import DiscoveredSource
    from app.models.benchmark import BenchmarkTitle
    from app.benchmarking.searcher import search_source

    db = SessionLocal()
    try:
        ds = db.query(DiscoveredSource).filter(DiscoveredSource.id == uuid.UUID(source_id)).first()
        if not ds:
            return {"error": "not found"}

        # Skip generic_http or low-confidence — they won't produce meaningful results
        if ds.detected_type == "generic_http" or (ds.confidence is not None and ds.confidence < 60):
            ds.notes = (ds.notes or "") + " [skipped benchmark: generic_http or low confidence]"
            db.commit()
            return {"skipped": True, "reason": "generic_http_or_low_confidence"}

        ita_titles = db.query(BenchmarkTitle).filter(BenchmarkTitle.language_target == "ita").limit(5).all()
        ger_titles = db.query(BenchmarkTitle).filter(BenchmarkTitle.language_target == "ger").limit(5).all()

        if not ita_titles and not ger_titles:
            ds.notes = "No benchmark titles available"
            db.commit()
            return {"error": "no benchmark titles"}

        ita_hits = sum(
            1 for t in ita_titles
            if (r := _run(search_source(ds.detected_type, ds.url, t.title, None))).success and r.result_count > 0
        )
        ger_hits = sum(
            1 for t in ger_titles
            if (r := _run(search_source(ds.detected_type, ds.url, t.title, None))).success and r.result_count > 0
        )

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


# ── Cleanup ──────────────────────────────────────────────────────────────────

@celery_app.task(name="app.worker.tasks.cleanup_garbage_candidates")
def cleanup_garbage_candidates():
    """
    Delete obvious garbage: generic_http with zero scores AND
    any discovered_source whose URL matches github.com patterns.
    """
    from app.models.discovery import DiscoveredSource
    import re

    db = SessionLocal()
    try:
        deleted = 0

        # Delete worthless generic_http (no scores at all)
        generic_garbage = db.query(DiscoveredSource).filter(
            DiscoveredSource.detected_type == "generic_http",
            DiscoveredSource.italian_score == None,
            DiscoveredSource.german_score == None,
            DiscoveredSource.overall_score == None,
        ).all()
        for ds in generic_garbage:
            db.delete(ds)
            deleted += 1

        # Delete anything with a github.com URL that slipped through
        github_re = re.compile(r"github\.com", re.IGNORECASE)
        github_rows = db.query(DiscoveredSource).filter(
            DiscoveredSource.url.op("~*")("github\\.com")
        ).all()
        for ds in github_rows:
            db.delete(ds)
            deleted += 1

        db.commit()
        return {"deleted": deleted}
    finally:
        db.close()


# ── Periodic tasks ────────────────────────────────────────────────────────────

@celery_app.task(name="app.worker.tasks.scheduled_discovery")
def scheduled_discovery():
    from app.models.discovery import DiscoveryRun, DiscoverySeed
    from app.models.settings import AppSetting
    db = SessionLocal()
    try:
        auto_setting = db.query(AppSetting).filter(AppSetting.key == "auto_discovery_enabled").first()
        if auto_setting and auto_setting.value.lower() != "true":
            return {"skipped": "auto_discovery_disabled"}

        if db.query(DiscoverySeed).filter(DiscoverySeed.enabled == True).count() == 0:
            return {"skipped": "no enabled seeds"}

        active = db.query(DiscoveryRun).filter(DiscoveryRun.status.in_(["pending", "running"])).first()
        if active:
            return {"skipped": "run already active", "run_id": str(active.id)}

        run = DiscoveryRun(status="pending")
        db.add(run)
        db.commit()
        db.refresh(run)
        run_discovery.delay(str(run.id))
        return {"run_id": str(run.id)}
    finally:
        db.close()


@celery_app.task(name="app.worker.tasks.deep_discovery")
def deep_discovery():
    from app.models.discovery import DiscoveryRun, DiscoverySeed
    from app.models.settings import AppSetting
    db = SessionLocal()
    try:
        auto_setting = db.query(AppSetting).filter(AppSetting.key == "auto_discovery_enabled").first()
        if auto_setting and auto_setting.value.lower() != "true":
            return {"skipped": "auto_discovery_disabled"}

        if db.query(DiscoverySeed).filter(DiscoverySeed.enabled == True).count() == 0:
            return {"skipped": "no enabled seeds"}

        active = db.query(DiscoveryRun).filter(DiscoveryRun.status.in_(["pending", "running"])).first()
        if active:
            return {"skipped": "run already active", "run_id": str(active.id)}

        run = DiscoveryRun(status="pending")
        db.add(run)
        db.commit()
        db.refresh(run)
        run_discovery.delay(str(run.id), deep=True)
        return {"run_id": str(run.id), "deep": True}
    finally:
        db.close()


@celery_app.task(name="app.worker.tasks.retest_discovered_sources")
def retest_discovered_sources():
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
