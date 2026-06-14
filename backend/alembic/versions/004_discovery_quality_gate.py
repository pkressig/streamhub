"""Discovery quality gate — rejected table, new columns on discovered_sources

Revision ID: 004
Revises: 003
Create Date: 2026-06-14
"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade():
    # New columns on discovered_sources
    op.add_column("discovered_sources", sa.Column("confidence", sa.Float(), nullable=True))
    op.add_column("discovered_sources", sa.Column("detection_reason", sa.Text(), nullable=True))
    op.add_column("discovered_sources", sa.Column("detection_method", sa.String(50), nullable=True))
    op.add_column("discovered_sources", sa.Column("detection_family", sa.String(50), nullable=True))

    # New table for rejected candidates
    op.create_table(
        "discovery_rejected",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("rejection_reason", sa.String(100), nullable=False),
        sa.Column("source_seed", sa.Text(), nullable=True),
        sa.Column("discovered_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_discovery_rejected_reason", "discovery_rejected", ["rejection_reason"])


def downgrade():
    op.drop_index("ix_discovery_rejected_reason", table_name="discovery_rejected")
    op.drop_table("discovery_rejected")
    op.drop_column("discovered_sources", "detection_family")
    op.drop_column("discovered_sources", "detection_method")
    op.drop_column("discovered_sources", "detection_reason")
    op.drop_column("discovered_sources", "confidence")
