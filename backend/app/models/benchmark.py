import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Float, Integer, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class BenchmarkTitle(Base):
    __tablename__ = "benchmark_titles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    imdb_id = Column(String, nullable=True)
    tmdb_id = Column(String, nullable=True)
    # movie | series | anime
    category = Column(String, nullable=False)
    # ita | ger | multi
    language_target = Column(String, nullable=False, default="multi")
    year = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    results = relationship(
        "BenchmarkResult", back_populates="benchmark", cascade="all, delete-orphan"
    )


class BenchmarkResult(Base):
    __tablename__ = "benchmark_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False
    )
    benchmark_id = Column(
        UUID(as_uuid=True),
        ForeignKey("benchmark_titles.id", ondelete="CASCADE"),
        nullable=False,
    )
    success = Column(Boolean, nullable=False)
    result_count = Column(Integer, default=0)
    response_time_ms = Column(Integer, nullable=True)
    duplicate_count = Column(Integer, default=0)
    tested_at = Column(DateTime, default=datetime.utcnow)
    run_id = Column(UUID(as_uuid=True), nullable=True)  # groups results per run

    source = relationship("Source")
    benchmark = relationship("BenchmarkTitle", back_populates="results")


class BenchmarkRun(Base):
    """A single benchmark run that tested all active sources against all benchmark titles."""

    __tablename__ = "benchmark_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    # pending | running | completed | failed
    status = Column(String, nullable=False, default="pending")
    sources_tested = Column(Integer, default=0)
    titles_tested = Column(Integer, default=0)
    notes = Column(Text, nullable=True)


class SourceProfile(Base):
    """Computed intelligence profile for a source based on benchmark results."""

    __tablename__ = "source_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(
        UUID(as_uuid=True), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    movie_score = Column(Float, default=0.0)
    series_score = Column(Float, default=0.0)
    anime_score = Column(Float, default=0.0)
    italian_score = Column(Float, default=0.0)
    german_score = Column(Float, default=0.0)
    avg_result_count = Column(Float, default=0.0)
    avg_response_ms = Column(Float, nullable=True)
    reliability_pct = Column(Float, default=0.0)
    duplicate_rate = Column(Float, default=0.0)
    benchmark_runs = Column(Integer, default=0)
    last_profiled = Column(DateTime, nullable=True)

    source = relationship("Source")
