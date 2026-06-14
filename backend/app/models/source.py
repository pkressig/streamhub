import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Float, Integer, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base

class Source(Base):
    __tablename__ = "sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    source_type = Column(String, nullable=False)  # torznab, newznab, rss, manifest, generic_http
    status = Column(String, nullable=False, default="unknown")  # unknown, active, degraded, dead
    requires_auth = Column(Boolean, default=False)
    auth_key = Column(String, nullable=True)
    last_checked = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    scores = relationship("SourceScore", back_populates="source", cascade="all, delete-orphan", order_by="SourceScore.calculated_at.desc()")
    tests = relationship("SourceTest", back_populates="source", cascade="all, delete-orphan", order_by="SourceTest.timestamp.desc()")


class SourceScore(Base):
    __tablename__ = "source_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    overall_score = Column(Float, default=0.0)
    italian_score = Column(Float, default=0.0)
    german_score = Column(Float, default=0.0)
    speed_score = Column(Float, default=0.0)
    reliability_score = Column(Float, default=0.0)
    trust_score = Column(Float, default=0.0)
    calculated_at = Column(DateTime, default=datetime.utcnow)

    source = relationship("Source", back_populates="scores")


class SourceTest(Base):
    __tablename__ = "source_tests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    success = Column(Boolean, nullable=False)
    response_time_ms = Column(Integer, nullable=True)
    http_status = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    tester_type = Column(String, nullable=True)

    source = relationship("Source", back_populates="tests")
