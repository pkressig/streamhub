import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, Float, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.database import Base


class DiscoverySeed(Base):
    __tablename__ = "discovery_seeds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url = Column(String, nullable=False, unique=True)
    label = Column(String, nullable=True)
    seed_type = Column(String, nullable=False, default="url")
    enabled = Column(Boolean, nullable=False, default=True)
    last_crawled = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class DiscoveryRun(Base):
    __tablename__ = "discovery_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String, nullable=False, default="pending")
    seeds_crawled = Column(Integer, default=0)
    candidates_found = Column(Integer, default=0)
    notes = Column(Text, nullable=True)

    discovered_sources = relationship("DiscoveredSource", back_populates="run")


class DiscoveredSource(Base):
    __tablename__ = "discovered_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    run_id = Column(UUID(as_uuid=True), ForeignKey("discovery_runs.id", ondelete="SET NULL"), nullable=True)
    url = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=True)
    detected_type = Column(String, nullable=False, default="unknown")
    status = Column(String, nullable=False, default="candidate")
    italian_score = Column(Float, nullable=True)
    german_score = Column(Float, nullable=True)
    overall_score = Column(Float, nullable=True)
    response_time_ms = Column(Float, nullable=True)
    http_status = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id", ondelete="SET NULL"), nullable=True)
    discovered_at = Column(DateTime, default=datetime.utcnow)
    tested_at = Column(DateTime, nullable=True)
    benchmarked_at = Column(DateTime, nullable=True)

    run = relationship("DiscoveryRun", back_populates="discovered_sources")
    fingerprint = relationship("SourceFingerprint", back_populates="discovered_source", uselist=False)


class SourceFingerprint(Base):
    __tablename__ = "source_fingerprints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    discovered_source_id = Column(UUID(as_uuid=True), ForeignKey("discovered_sources.id", ondelete="CASCADE"), nullable=False)
    fingerprint_hash = Column(String, nullable=False)
    base_url = Column(String, nullable=True)
    api_path = Column(String, nullable=True)
    capabilities = Column(JSONB, nullable=True)
    software_family = Column(String, nullable=True)
    version_hint = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    discovered_source = relationship("DiscoveredSource", back_populates="fingerprint")


class SourceRelationship(Base):
    __tablename__ = "source_relationships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_a_id = Column(UUID(as_uuid=True), ForeignKey("discovered_sources.id", ondelete="CASCADE"), nullable=False)
    source_b_id = Column(UUID(as_uuid=True), ForeignKey("discovered_sources.id", ondelete="CASCADE"), nullable=False)
    relationship_type = Column(String, nullable=False)
    confidence = Column(Float, default=1.0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
