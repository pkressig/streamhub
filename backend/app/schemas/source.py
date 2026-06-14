from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class SourceCreate(BaseModel):
    name: str
    url: str
    source_type: str  # torznab, newznab, rss, manifest, generic_http
    requires_auth: bool = False
    auth_key: Optional[str] = None

class SourceScoreResponse(BaseModel):
    id: UUID
    source_id: UUID
    overall_score: float
    italian_score: float
    german_score: float
    speed_score: float
    reliability_score: float
    trust_score: float
    calculated_at: datetime

    class Config:
        from_attributes = True

class SourceTestResponse(BaseModel):
    id: UUID
    source_id: UUID
    timestamp: datetime
    success: bool
    response_time_ms: Optional[int]
    http_status: Optional[int]
    notes: Optional[str]
    tester_type: Optional[str]

    class Config:
        from_attributes = True

class SourceResponse(BaseModel):
    id: UUID
    name: str
    url: str
    source_type: str
    status: str
    requires_auth: bool
    last_checked: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    latest_score: Optional[SourceScoreResponse] = None

    class Config:
        from_attributes = True

class SourceDetailResponse(SourceResponse):
    recent_tests: List[SourceTestResponse] = []

class StatsResponse(BaseModel):
    total: int
    active: int
    degraded: int
    dead: int
    unknown: int
    avg_overall_score: float
    recent_tests: List[SourceTestResponse] = []
