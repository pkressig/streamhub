from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class BenchmarkTitleCreate(BaseModel):
    title: str
    imdb_id: Optional[str] = None
    tmdb_id: Optional[str] = None
    category: str  # movie | series | anime
    language_target: str = "multi"  # ita | ger | multi
    year: Optional[int] = None


class BenchmarkTitleResponse(BenchmarkTitleCreate):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class BenchmarkResultResponse(BaseModel):
    id: UUID
    source_id: UUID
    benchmark_id: UUID
    run_id: Optional[UUID]
    success: bool
    result_count: int
    response_time_ms: Optional[int]
    duplicate_count: int
    tested_at: datetime

    class Config:
        from_attributes = True


class BenchmarkRunResponse(BaseModel):
    id: UUID
    started_at: datetime
    finished_at: Optional[datetime]
    status: str
    sources_tested: int
    titles_tested: int
    notes: Optional[str]

    class Config:
        from_attributes = True


class SourceProfileResponse(BaseModel):
    source_id: UUID
    movie_score: float
    series_score: float
    anime_score: float
    italian_score: float
    german_score: float
    avg_result_count: float
    avg_response_ms: Optional[float]
    reliability_pct: float
    duplicate_rate: float
    benchmark_runs: int
    last_profiled: Optional[datetime]

    class Config:
        from_attributes = True


class RankedSourceResponse(BaseModel):
    id: UUID
    name: str
    url: str
    source_type: str
    status: str
    score: float
    profile: Optional[SourceProfileResponse] = None

    class Config:
        from_attributes = True


class ImportResponse(BaseModel):
    imported: int
    skipped: int
    errors: List[str] = []
