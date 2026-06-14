from __future__ import annotations
from datetime import datetime
from typing import Optional, Any
from uuid import UUID
from pydantic import BaseModel


class DiscoverySeedCreate(BaseModel):
    url: str
    label: Optional[str] = None
    seed_type: str = "url"
    category: Optional[str] = None
    enabled: bool = True
    parent_seed_id: Optional[UUID] = None
    is_bred: bool = False
    breed_depth: int = 0


class DiscoverySeedOut(BaseModel):
    id: UUID
    url: str
    label: Optional[str]
    seed_type: str
    category: Optional[str]
    enabled: bool
    last_crawled: Optional[datetime]
    created_at: Optional[datetime]
    parent_seed_id: Optional[UUID]
    is_bred: bool
    breed_depth: int

    model_config = {"from_attributes": True}


class DiscoveryRunOut(BaseModel):
    id: UUID
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    status: str
    seeds_crawled: int
    candidates_found: int
    notes: Optional[str]

    model_config = {"from_attributes": True}


class DiscoveredSourceOut(BaseModel):
    id: UUID
    run_id: Optional[UUID]
    url: str
    name: Optional[str]
    detected_type: str
    detection_family: Optional[str]
    confidence: Optional[float]
    detection_reason: Optional[str]
    detection_method: Optional[str]
    status: str
    italian_score: Optional[float]
    german_score: Optional[float]
    overall_score: Optional[float]
    response_time_ms: Optional[float]
    http_status: Optional[int]
    notes: Optional[str]
    source_id: Optional[UUID]
    discovered_at: Optional[datetime]
    tested_at: Optional[datetime]
    benchmarked_at: Optional[datetime]

    model_config = {"from_attributes": True}


class DiscoveryRejectedOut(BaseModel):
    id: int
    url: str
    rejection_reason: str
    source_seed: Optional[str]
    discovered_at: Optional[datetime]

    model_config = {"from_attributes": True}


class SourceRelationshipOut(BaseModel):
    id: UUID
    source_a_id: UUID
    source_b_id: UUID
    relationship_type: str
    confidence: float
    notes: Optional[str]
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


class DiscoveryStatsOut(BaseModel):
    total_candidates: int
    tested: int
    benchmarked: int
    approved: int
    imported: int
    ignored: int
    dead: int
    total_seeds: int
    active_seeds: int
    total_runs: int
    total_rejected: int
    auto_discovery_enabled: bool
    discovery_interval_hours: int
    next_scheduled_at: Optional[datetime]
    total_bred_seeds: int
