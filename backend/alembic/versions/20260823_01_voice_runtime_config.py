"""Add voice runtime provider configuration to agents table

Revision ID: 20260823_01
Revises: 20260619_01
Create Date: 2026-08-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260823_01"
down_revision = "20260619_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add streaming provider fields
    op.add_column('agents', sa.Column('stt_provider', sa.String(40), nullable=False, server_default='openai'))
    op.add_column('agents', sa.Column('llm_provider', sa.String(40), nullable=False, server_default='openai'))
    op.add_column('agents', sa.Column('tts_provider', sa.String(40), nullable=False, server_default='openai'))
    
    # Add language support
    op.add_column('agents', sa.Column('supported_languages', postgresql.ARRAY(sa.String(32)), nullable=False, server_default=sa.text("ARRAY['en-IN']::text[]")))
    
    # Add model configuration
    op.add_column('agents', sa.Column('llm_model', sa.String(80), nullable=True))
    op.add_column('agents', sa.Column('stt_model', sa.String(80), nullable=True))
    op.add_column('agents', sa.Column('tts_model', sa.String(80), nullable=True))
    
    # Add tools configuration
    op.add_column('agents', sa.Column('enabled_tools', postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")))
    
    # Add business configuration (from hospital_settings)
    op.add_column('agents', sa.Column('business_config', postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")))


def downgrade() -> None:
    op.drop_column('agents', 'business_config')
    op.drop_column('agents', 'enabled_tools')
    op.drop_column('agents', 'tts_model')
    op.drop_column('agents', 'stt_model')
    op.drop_column('agents', 'llm_model')
    op.drop_column('agents', 'supported_languages')
    op.drop_column('agents', 'tts_provider')
    op.drop_column('agents', 'llm_provider')
    op.drop_column('agents', 'stt_provider')
