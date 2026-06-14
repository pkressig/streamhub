from __future__ import annotations
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.discovery import DiscoverySeed, DiscoveryRun, DiscoveredSource, SourceRelationship, DiscoveryRejected
from app.schemas.discovery import (
    DiscoverySeedCreate, DiscoverySeedOut,
    DiscoveryRunOut, DiscoveredSourceOut,
    SourceRelationshipOut, DiscoveryStatsOut, DiscoveryRejectedOut,
)

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Stats ────────────────────────────────────────────────────────────────────

@router.get("/stats", response_model=DiscoveryStatsOut)
def get_stats(db: Session = Depends(get_db)):
    from sqlalchemy import func
    status_counts = dict(
        db.query(DiscoveredSource.status, func.count(DiscoveredSource.id))
        .group_by(DiscoveredSource.status)
        .all()
    )
    return DiscoveryStatsOut(
        total_candidates=db.query(DiscoveredSource).count(),
        tested=(
            status_counts.get("tested", 0)
            + status_counts.get("benchmarked", 0)
            + status_counts.get("approved", 0)
            + status_counts.get("imported", 0)
        ),
        benchmarked=status_counts.get("benchmarked", 0) + status_counts.get("approved", 0) + status_counts.get("imported", 0),
        approved=status_counts.get("approved", 0),
        imported=status_counts.get("imported", 0),
        ignored=status_counts.get("ignored", 0),
        dead=status_counts.get("dead", 0),
        total_seeds=db.query(DiscoverySeed).count(),
        active_seeds=db.query(DiscoverySeed).filter(DiscoverySeed.enabled == True).count(),
        total_runs=db.query(DiscoveryRun).count(),
        total_rejected=db.query(DiscoveryRejected).count(),
    )


# ── Seeds ────────────────────────────────────────────────────────────────────

@router.get("/seeds", response_model=list[DiscoverySeedOut])
def list_seeds(db: Session = Depends(get_db)):
    return db.query(DiscoverySeed).order_by(DiscoverySeed.created_at.desc()).all()


@router.post("/seeds", response_model=DiscoverySeedOut, status_code=201)
def create_seed(body: DiscoverySeedCreate, db: Session = Depends(get_db)):
    existing = db.query(DiscoverySeed).filter(DiscoverySeed.url == body.url).first()
    if existing:
        raise HTTPException(status_code=409, detail="Seed URL already exists")
    seed = DiscoverySeed(**body.model_dump())
    db.add(seed)
    db.commit()
    db.refresh(seed)
    return seed


@router.delete("/seeds/{seed_id}", status_code=204)
def delete_seed(seed_id: str, db: Session = Depends(get_db)):
    seed = db.query(DiscoverySeed).filter(DiscoverySeed.id == uuid.UUID(seed_id)).first()
    if not seed:
        raise HTTPException(status_code=404, detail="Seed not found")
    db.delete(seed)
    db.commit()


# ── Runs ─────────────────────────────────────────────────────────────────────

@router.get("/runs", response_model=list[DiscoveryRunOut])
def list_runs(db: Session = Depends(get_db)):
    return db.query(DiscoveryRun).order_by(DiscoveryRun.started_at.desc()).limit(50).all()


@router.post("/runs", response_model=DiscoveryRunOut, status_code=201)
def trigger_run(db: Session = Depends(get_db)):
    from app.worker.discovery_tasks import run_discovery
    run = DiscoveryRun(status="pending")
    db.add(run)
    db.commit()
    db.refresh(run)
    try:
        run_discovery.delay(str(run.id))
    except Exception as e:
        run.status = "failed"
        run.notes = f"Failed to dispatch task: {e}"
        db.commit()
    return run


# ── Cleanup ───────────────────────────────────────────────────────────────────

@router.post("/cleanup", status_code=202)
def trigger_cleanup():
    """Dispatch the cleanup_garbage_candidates Celery task."""
    from app.worker.discovery_tasks import cleanup_garbage_candidates
    try:
        cleanup_garbage_candidates.delay()
        return {"dispatched": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to dispatch cleanup: {e}")


# ── Discovered Sources ────────────────────────────────────────────────────────

@router.get("/sources", response_model=list[DiscoveredSourceOut])
def list_discovered(
    status: Optional[str] = Query(None),
    detected_type: Optional[str] = Query(None),
    min_confidence: Optional[float] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(DiscoveredSource)
    if status:
        q = q.filter(DiscoveredSource.status == status)
    if detected_type:
        q = q.filter(DiscoveredSource.detected_type == detected_type)
    if min_confidence is not None:
        q = q.filter(DiscoveredSource.confidence >= min_confidence)
    return q.order_by(DiscoveredSource.discovered_at.desc()).limit(500).all()


@router.get("/sources/{source_id}", response_model=DiscoveredSourceOut)
def get_discovered(source_id: str, db: Session = Depends(get_db)):
    s = db.query(DiscoveredSource).filter(DiscoveredSource.id == uuid.UUID(source_id)).first()
    if not s:
        raise HTTPException(status_code=404, detail="Discovered source not found")
    return s


@router.post("/sources/{source_id}/test", response_model=DiscoveredSourceOut)
def test_discovered(source_id: str, db: Session = Depends(get_db)):
    s = db.query(DiscoveredSource).filter(DiscoveredSource.id == uuid.UUID(source_id)).first()
    if not s:
        raise HTTPException(status_code=404, detail="Not found")
    from app.worker.discovery_tasks import test_discovered_source
    test_discovered_source.delay(source_id)
    return s


@router.post("/sources/{source_id}/benchmark", response_model=DiscoveredSourceOut)
def benchmark_discovered(source_id: str, db: Session = Depends(get_db)):
    s = db.query(DiscoveredSource).filter(DiscoveredSource.id == uuid.UUID(source_id)).first()
    if not s:
        raise HTTPException(status_code=404, detail="Not found")
    from app.worker.discovery_tasks import benchmark_discovered_source
    benchmark_discovered_source.delay(source_id)
    return s


@router.post("/sources/{source_id}/approve", response_model=DiscoveredSourceOut)
def approve_discovered(source_id: str, db: Session = Depends(get_db)):
    s = db.query(DiscoveredSource).filter(DiscoveredSource.id == uuid.UUID(source_id)).first()
    if not s:
        raise HTTPException(status_code=404, detail="Not found")
    s.status = "approved"
    db.commit()
    db.refresh(s)
    return s


@router.post("/sources/{source_id}/import", response_model=DiscoveredSourceOut)
def import_discovered(source_id: str, db: Session = Depends(get_db)):
    from app.models.source import Source
    s = db.query(DiscoveredSource).filter(DiscoveredSource.id == uuid.UUID(source_id)).first()
    if not s:
        raise HTTPException(status_code=404, detail="Not found")
    if s.status == "imported" and s.source_id:
        raise HTTPException(status_code=409, detail="Already imported")

    type_map = {
        "torznab": "torznab", "newznab": "newznab", "rss": "rss",
        "stremio_manifest": "manifest", "generic_http": "generic_http",
        "jackett": "torznab", "prowlarr": "torznab", "nzbhydra": "newznab",
        "bitmagnet": "generic_http",
    }
    source_type = type_map.get(s.detected_type, "generic_http")

    source = Source(name=s.name or s.url, url=s.url, source_type=source_type, status="unknown")
    db.add(source)
    db.flush()
    s.status = "imported"
    s.source_id = source.id
    db.commit()
    db.refresh(s)
    return s


@router.post("/sources/{source_id}/ignore", response_model=DiscoveredSourceOut)
def ignore_discovered(source_id: str, db: Session = Depends(get_db)):
    s = db.query(DiscoveredSource).filter(DiscoveredSource.id == uuid.UUID(source_id)).first()
    if not s:
        raise HTTPException(status_code=404, detail="Not found")
    s.status = "ignored"
    db.commit()
    db.refresh(s)
    return s


# ── Rejected ──────────────────────────────────────────────────────────────────

@router.get("/rejected", response_model=list[DiscoveryRejectedOut])
def list_rejected(
    limit: int = Query(200, le=1000),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    return (
        db.query(DiscoveryRejected)
        .order_by(DiscoveryRejected.discovered_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.delete("/rejected", status_code=204)
def clear_rejected(db: Session = Depends(get_db)):
    """Bulk-delete all rejection log entries."""
    db.query(DiscoveryRejected).delete()
    db.commit()


# ── Relationships ─────────────────────────────────────────────────────────────

@router.get("/relationships", response_model=list[SourceRelationshipOut])
def list_relationships(db: Session = Depends(get_db)):
    return db.query(SourceRelationship).order_by(SourceRelationship.created_at.desc()).limit(200).all()
