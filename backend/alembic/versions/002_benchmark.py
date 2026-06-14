"""Benchmark tables

Revision ID: 002
Revises: 001
Create Date: 2026-06-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "benchmark_titles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("imdb_id", sa.String(), nullable=True),
        sa.Column("tmdb_id", sa.String(), nullable=True),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("language_target", sa.String(), nullable=False, server_default="multi"),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_benchmark_titles_category", "benchmark_titles", ["category"])
    op.create_index("ix_benchmark_titles_language", "benchmark_titles", ["language_target"])

    op.create_table(
        "benchmark_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("started_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("sources_tested", sa.Integer(), default=0),
        sa.Column("titles_tested", sa.Integer(), default=0),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "benchmark_results",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("benchmark_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("result_count", sa.Integer(), default=0),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("duplicate_count", sa.Integer(), default=0),
        sa.Column("tested_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["benchmark_id"], ["benchmark_titles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_benchmark_results_source_id", "benchmark_results", ["source_id"])
    op.create_index("ix_benchmark_results_benchmark_id", "benchmark_results", ["benchmark_id"])
    op.create_index("ix_benchmark_results_run_id", "benchmark_results", ["run_id"])
    op.create_index("ix_benchmark_results_tested_at", "benchmark_results", ["tested_at"])

    op.create_table(
        "source_profiles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("movie_score", sa.Float(), default=0.0),
        sa.Column("series_score", sa.Float(), default=0.0),
        sa.Column("anime_score", sa.Float(), default=0.0),
        sa.Column("italian_score", sa.Float(), default=0.0),
        sa.Column("german_score", sa.Float(), default=0.0),
        sa.Column("avg_result_count", sa.Float(), default=0.0),
        sa.Column("avg_response_ms", sa.Float(), nullable=True),
        sa.Column("reliability_pct", sa.Float(), default=0.0),
        sa.Column("duplicate_rate", sa.Float(), default=0.0),
        sa.Column("benchmark_runs", sa.Integer(), default=0),
        sa.Column("last_profiled", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id"),
    )
    op.create_index("ix_source_profiles_source_id", "source_profiles", ["source_id"])


def downgrade():
    op.drop_table("source_profiles")
    op.drop_table("benchmark_results")
    op.drop_table("benchmark_runs")
    op.drop_table("benchmark_titles")
