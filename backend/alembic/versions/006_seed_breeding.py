"""Seed breeding — parent_seed_id, is_bred, breed_depth on discovery_seeds; app_settings table

Revision ID: 006
Revises: 005
Create Date: 2026-06-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("discovery_seeds", sa.Column("parent_seed_id", UUID(as_uuid=True), sa.ForeignKey("discovery_seeds.id", ondelete="SET NULL"), nullable=True))
    op.add_column("discovery_seeds", sa.Column("is_bred", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("discovery_seeds", sa.Column("breed_depth", sa.Integer(), nullable=False, server_default="0"))

    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(100), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True, server_default=sa.text("now()")),
    )

    op.execute("INSERT INTO app_settings (key, value) VALUES ('auto_discovery_enabled', 'true')")


def downgrade():
    op.drop_table("app_settings")
    op.drop_column("discovery_seeds", "breed_depth")
    op.drop_column("discovery_seeds", "is_bred")
    op.drop_column("discovery_seeds", "parent_seed_id")
