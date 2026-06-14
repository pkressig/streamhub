"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-14
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('source_type', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='unknown'),
        sa.Column('requires_auth', sa.Boolean(), nullable=True, server_default='false'),
        sa.Column('auth_key', sa.String(), nullable=True),
        sa.Column('last_checked', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_sources_status', 'sources', ['status'])

    op.create_table(
        'source_scores',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('overall_score', sa.Float(), nullable=True),
        sa.Column('italian_score', sa.Float(), nullable=True),
        sa.Column('german_score', sa.Float(), nullable=True),
        sa.Column('speed_score', sa.Float(), nullable=True),
        sa.Column('reliability_score', sa.Float(), nullable=True),
        sa.Column('trust_score', sa.Float(), nullable=True),
        sa.Column('calculated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_source_scores_source_id', 'source_scores', ['source_id'])

    op.create_table(
        'source_tests',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('http_status', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('tester_type', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['source_id'], ['sources.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_source_tests_source_id', 'source_tests', ['source_id'])
    op.create_index('ix_source_tests_timestamp', 'source_tests', ['timestamp'])

def downgrade():
    op.drop_table('source_tests')
    op.drop_table('source_scores')
    op.drop_table('sources')
