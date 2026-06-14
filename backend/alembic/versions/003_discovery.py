"""Discovery tables

Revision ID: 003
Revises: 002
Create Date: 2026-06-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "discovery_seeds",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=True),
        sa.Column("seed_type", sa.String(), nullable=False, server_default="url"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_crawled", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url"),
    )

    op.create_table(
        "discovery_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("started_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("seeds_crawled", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("candidates_found", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "discovered_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("detected_type", sa.String(), nullable=False, server_default="unknown"),
        sa.Column("status", sa.String(), nullable=False, server_default="candidate"),
        sa.Column("italian_score", sa.Float(), nullable=True),
        sa.Column("german_score", sa.Float(), nullable=True),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("response_time_ms", sa.Float(), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("discovered_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
        sa.Column("tested_at", sa.DateTime(), nullable=True),
        sa.Column("benchmarked_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["discovery_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("url"),
    )
    op.create_index("ix_discovered_sources_status", "discovered_sources", ["status"])
    op.create_index("ix_discovered_sources_detected_type", "discovered_sources", ["detected_type"])

    op.create_table(
        "source_fingerprints",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("discovered_source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fingerprint_hash", sa.String(), nullable=False),
        sa.Column("base_url", sa.String(), nullable=True),
        sa.Column("api_path", sa.String(), nullable=True),
        sa.Column("capabilities", postgresql.JSONB(), nullable=True),
        sa.Column("software_family", sa.String(), nullable=True),
        sa.Column("version_hint", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["discovered_source_id"], ["discovered_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_source_fingerprints_hash", "source_fingerprints", ["fingerprint_hash"])

    op.create_table(
        "source_relationships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_a_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_b_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relationship_type", sa.String(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True, server_default="1.0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["source_a_id"], ["discovered_sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_b_id"], ["discovered_sources.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("source_relationships")
    op.drop_table("source_fingerprints")
    op.drop_table("discovered_sources")
    op.drop_table("discovery_runs")
    op.drop_table("discovery_seeds")
