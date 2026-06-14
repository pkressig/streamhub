"""Add category column to discovery_seeds

Revision ID: 005
Revises: 004
Create Date: 2026-06-14
"""
from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("discovery_seeds", sa.Column("category", sa.String(50), nullable=True))


def downgrade():
    op.drop_column("discovery_seeds", "category")
