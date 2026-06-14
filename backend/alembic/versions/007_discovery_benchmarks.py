"""discovery_benchmark_results table + benchmarking columns on discovered_sources

Revision ID: 007
Revises: 006
Create Date: 2026-06-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("discovered_sources", sa.Column("last_benchmark_at", sa.DateTime(), nullable=True))
    op.add_column("discovered_sources", sa.Column("best_italian_score", sa.Float(), nullable=True))
    op.add_column("discovered_sources", sa.Column("best_german_score", sa.Float(), nullable=True))
    op.add_column("discovered_sources", sa.Column("best_overall_score", sa.Float(), nullable=True))
    op.add_column("discovered_sources", sa.Column("anime_score", sa.Float(), nullable=True))
    op.add_column("discovered_sources", sa.Column("reject_reason", sa.Text(), nullable=True))

    op.create_table(
        "discovery_benchmark_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_id", UUID(as_uuid=True), sa.ForeignKey("discovered_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
        sa.Column("is_online", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("response_ms", sa.Integer(), nullable=True),
        sa.Column("total_results", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("italian_results", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("german_results", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("english_results", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("anime_results", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("dubbed_results", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("results_4k", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("results_1080p", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("results_720p", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("has_debrid_links", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("italian_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("german_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("anime_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("overall_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("test_queries_run", JSONB(), nullable=True),
        sa.Column("raw_sample", JSONB(), nullable=True),
    )
    op.create_index("idx_dbm_source_id", "discovery_benchmark_results", ["source_id"])


def downgrade():
    op.drop_index("idx_dbm_source_id", table_name="discovery_benchmark_results")
    op.drop_table("discovery_benchmark_results")
    for col in ("reject_reason", "anime_score", "best_overall_score", "best_german_score",
                "best_italian_score", "last_benchmark_at"):
        op.drop_column("discovered_sources", col)
