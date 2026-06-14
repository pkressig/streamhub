from typing import List
from app.models.source import SourceTest


class ScoringEngine:
    def calculate(self, tests: List[SourceTest]) -> dict:
        if not tests:
            return {
                "overall_score": 0.0,
                "italian_score": 0.0,
                "german_score": 0.0,
                "speed_score": 0.0,
                "reliability_score": 0.0,
                "trust_score": 0.0,
            }

        total = len(tests)
        successful = sum(1 for t in tests if t.success)
        reliability_score = (successful / total) * 100.0

        response_times = [
            t.response_time_ms
            for t in tests
            if t.success and t.response_time_ms is not None
        ]
        if response_times:
            avg_ms = sum(response_times) / len(response_times)
            if avg_ms <= 500:
                speed_score = 100.0
            elif avg_ms >= 5000:
                speed_score = 0.0
            else:
                speed_score = 100.0 - ((avg_ms - 500) / 4500) * 100.0
        else:
            speed_score = 0.0

        # Placeholders — AI-based language detection in future phases
        italian_score = 0.0
        german_score = 0.0

        trust_score = (reliability_score + speed_score) / 2.0

        overall_score = (
            reliability_score * 0.35
            + speed_score * 0.25
            + trust_score * 0.20
            + italian_score * 0.10
            + german_score * 0.10
        )

        return {
            "overall_score": round(overall_score, 2),
            "italian_score": round(italian_score, 2),
            "german_score": round(german_score, 2),
            "speed_score": round(speed_score, 2),
            "reliability_score": round(reliability_score, 2),
            "trust_score": round(trust_score, 2),
        }


scoring_engine = ScoringEngine()
