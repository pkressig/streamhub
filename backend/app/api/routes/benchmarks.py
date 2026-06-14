import csv
import io
import json
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.models.benchmark import BenchmarkTitle, BenchmarkResult, BenchmarkRun
from app.schemas.benchmark import (
    BenchmarkTitleResponse,
    BenchmarkResultResponse,
    BenchmarkRunResponse,
    ImportResponse,
)

router = APIRouter()


# ── Titles ───────────────────────────────────────────────────────────────────

@router.get("/titles", response_model=List[BenchmarkTitleResponse])
def list_titles(
    category: Optional[str] = Query(None),
    language_target: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(BenchmarkTitle)
    if category:
        q = q.filter(BenchmarkTitle.category == category)
    if language_target:
        q = q.filter(BenchmarkTitle.language_target == language_target)
    return q.order_by(BenchmarkTitle.title).all()


@router.post("/titles", response_model=BenchmarkTitleResponse, status_code=201)
def create_title(payload: dict = Body(...), db: Session = Depends(get_db)):
    from app.schemas.benchmark import BenchmarkTitleCreate
    data = BenchmarkTitleCreate(**payload)
    title = BenchmarkTitle(**data.model_dump())
    db.add(title)
    db.commit()
    db.refresh(title)
    return title


@router.delete("/titles/{title_id}", status_code=204)
def delete_title(title_id: str, db: Session = Depends(get_db)):
    t = db.query(BenchmarkTitle).filter(BenchmarkTitle.id == uuid.UUID(title_id)).first()
    if not t:
        raise HTTPException(status_code=404, detail="Title not found")
    db.delete(t)
    db.commit()


# ── Import ────────────────────────────────────────────────────────────────────

@router.post("/import", response_model=ImportResponse)
async def import_titles(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    content = await file.read()
    filename = file.filename or ""
    errors: List[str] = []
    imported = 0
    skipped = 0

    rows: List[dict] = []
    if filename.endswith(".json"):
        try:
            data = json.loads(content)
            rows = data if isinstance(data, list) else [data]
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
    elif filename.endswith(".csv"):
        try:
            reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
            rows = list(reader)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid CSV: {e}")
    else:
        raise HTTPException(status_code=400, detail="Only .csv and .json files supported")

    for i, row in enumerate(rows):
        try:
            title_val = str(row.get("title", "")).strip()
            if not title_val:
                skipped += 1
                continue
            category = str(row.get("category", "movie")).strip().lower()
            if category not in ("movie", "series", "anime"):
                errors.append(f"Row {i+1}: invalid category '{category}', skipping")
                skipped += 1
                continue
            lang = str(row.get("language_target", "multi")).strip().lower()
            if lang not in ("ita", "ger", "multi"):
                lang = "multi"
            year = None
            if row.get("year"):
                try:
                    year = int(row["year"])
                except ValueError:
                    pass
            bt = BenchmarkTitle(
                title=title_val,
                imdb_id=row.get("imdb_id") or None,
                tmdb_id=row.get("tmdb_id") or None,
                category=category,
                language_target=lang,
                year=year,
            )
            db.add(bt)
            imported += 1
        except Exception as e:
            errors.append(f"Row {i+1}: {e}")
            skipped += 1

    db.commit()
    return ImportResponse(imported=imported, skipped=skipped, errors=errors)


# ── Runs ──────────────────────────────────────────────────────────────────────

@router.get("/runs", response_model=List[BenchmarkRunResponse])
def list_runs(db: Session = Depends(get_db)):
    return db.query(BenchmarkRun).order_by(desc(BenchmarkRun.started_at)).limit(50).all()


@router.post("/run", response_model=BenchmarkRunResponse, status_code=202)
def trigger_run(db: Session = Depends(get_db)):
    """Create a benchmark run record and dispatch to worker."""
    titles_count = db.query(BenchmarkTitle).count()
    if titles_count == 0:
        raise HTTPException(status_code=400, detail="No benchmark titles defined. Import titles first.")

    run = BenchmarkRun(status="pending")
    db.add(run)
    db.commit()
    db.refresh(run)

    from app.worker.tasks import run_benchmark
    run_benchmark.delay(str(run.id))

    return run


@router.get("/runs/{run_id}", response_model=BenchmarkRunResponse)
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = db.query(BenchmarkRun).filter(BenchmarkRun.id == uuid.UUID(run_id)).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


# ── Results ───────────────────────────────────────────────────────────────────

@router.get("/results", response_model=List[BenchmarkResultResponse])
def list_results(
    source_id: Optional[str] = Query(None),
    run_id: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
):
    q = db.query(BenchmarkResult)
    if source_id:
        q = q.filter(BenchmarkResult.source_id == uuid.UUID(source_id))
    if run_id:
        q = q.filter(BenchmarkResult.run_id == uuid.UUID(run_id))
    return q.order_by(desc(BenchmarkResult.tested_at)).limit(limit).all()
