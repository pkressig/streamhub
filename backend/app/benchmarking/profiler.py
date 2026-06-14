"""
Computes SourceProfile from BenchmarkResults.
Called after each benchmark run.
"""
from datetime import datetime
from typing import List
from sqlalchemy.orm import Session

from app.models.benchmark import BenchmarkResult, BenchmarkTitle, SourceProfile
from app.models.source import Source, SourceScore


def _score_from_results(results: List[BenchmarkResult]) -> float:
    """0-100 score: fraction successful weighted by result_count richness."""
    if not results:
        return 0.0
    total = len(results)
    hits = sum(1 for r in results if r.success and r.result_count > 0)
    hit_rate = hits / total

    avg_count = sum(r.result_count for r in results if r.success) / max(hits, 1)
    richness = min(avg_count / 20.0, 1.0)  # 20+ results = full richness

    dup_rate = sum(r.duplicate_count for r in results) / max(
        sum(r.result_count for r in results if r.success), 1
    )
    dup_penalty = min(dup_rate * 0.3, 0.3)  # max 30 point penalty

    return round((hit_rate * 0.6 + richness * 0.4 - dup_penalty) * 100, 2)


def build_profile(source_id, db: Session) -> SourceProfile:
    results = (
        db.query(BenchmarkResult)
        .filter(BenchmarkResult.source_id == source_id)
        .all()
    )

    def _filter(results, **kwargs):
        out = []
        for r in results:
            bm = r.benchmark
            match = all(getattr(bm, k) == v for k, v in kwargs.items())
            if match:
                out.append(r)
        return out

    movie_results = _filter(results, category="movie")
    series_results = _filter(results, category="series")
    anime_results = _filter(results, category="anime")
    ita_results = _filter(results, language_target="ita")
    ger_results = _filter(results, language_target="ger")

    total = len(results)
    successful = [r for r in results if r.success]
    reliability = (len(successful) / total * 100) if total else 0.0
    response_times = [r.response_time_ms for r in results if r.response_time_ms]
    avg_ms = sum(response_times) / len(response_times) if response_times else None
    avg_count = sum(r.result_count for r in successful) / max(len(successful), 1)
    total_results = max(sum(r.result_count for r in results), 1)
    dup_rate = sum(r.duplicate_count for r in results) / total_results

    profile = db.query(SourceProfile).filter(SourceProfile.source_id == source_id).first()
    if not profile:
        profile = SourceProfile(source_id=source_id)
        db.add(profile)

    profile.movie_score = _score_from_results(movie_results)
    profile.series_score = _score_from_results(series_results)
    profile.anime_score = _score_from_results(anime_results)
    profile.italian_score = _score_from_results(ita_results)
    profile.german_score = _score_from_results(ger_results)
    profile.avg_result_count = round(avg_count, 2)
    profile.avg_response_ms = round(avg_ms, 0) if avg_ms else None
    profile.reliability_pct = round(reliability, 2)
    profile.duplicate_rate = round(dup_rate * 100, 2)
    profile.benchmark_runs = (profile.benchmark_runs or 0) + 1
    profile.last_profiled = datetime.utcnow()

    # Push scores back into SourceScore so dashboard picks them up
    from app.models.source import SourceScore, SourceTest
    from app.scoring.engine import scoring_engine

    recent_tests = (
        db.query(SourceTest)
        .filter(SourceTest.source_id == source_id)
        .order_by(SourceTest.timestamp.desc())
        .limit(50)
        .all()
    )
    base_scores = scoring_engine.calculate(recent_tests)
    base_scores["italian_score"] = profile.italian_score
    base_scores["german_score"] = profile.german_score
    # Recalculate overall with real language scores
    base_scores["overall_score"] = round(
        base_scores["reliability_score"] * 0.30
        + base_scores["speed_score"] * 0.20
        + base_scores["trust_score"] * 0.15
        + profile.italian_score * 0.15
        + profile.german_score * 0.10
        + profile.movie_score * 0.05
        + profile.series_score * 0.05,
        2,
    )
    score_record = SourceScore(
        source_id=source_id,
        calculated_at=datetime.utcnow(),
        **base_scores,
    )
    db.add(score_record)

    return profile
