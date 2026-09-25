"""Add voice call events and session tracking

Revision ID: 20260823_02
Revises: 20260823_01
Create Date: 2026-08-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260823_02"
down_revision = "20260823_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add fields to conversation_turns for voice runtime
    op.add_column('conversation_turns', sa.Column('timestamp_start', sa.DateTime(timezone=True), nullable=True))
    op.add_column('conversation_turns', sa.Column('timestamp_end', sa.DateTime(timezone=True), nullable=True))
    op.add_column('conversation_turns', sa.Column('language', sa.String(16), nullable=True))
    op.add_column('conversation_turns', sa.Column('interrupted', sa.Boolean, nullable=False, server_default='false'))
    op.add_column('conversation_turns', sa.Column('provider', sa.String(40), nullable=True))
    op.add_column('conversation_turns', sa.Column('metadata', postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")))
    
    # Add fields to calls for voice runtime
    op.add_column('calls', sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('calls', sa.Column('session_id', sa.String(64), nullable=True))
    op.add_column('calls', sa.Column('stream_sid', sa.String(64), nullable=True))
    op.add_column('calls', sa.Column('caller_phone', sa.String(32), nullable=True))
    op.add_column('calls', sa.Column('response_latency_ms', sa.Integer, nullable=True))
    
    # Create voice_call_events table for detailed event logging
    op.create_table(
        'voice_call_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hospitals.id', ondelete='CASCADE'), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agents.id', ondelete='SET NULL'), nullable=True),
        sa.Column('call_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('calls.id', ondelete='CASCADE'), nullable=True),
        sa.Column('session_id', sa.String(64), nullable=False),
        sa.Column('stream_sid', sa.String(64), nullable=True),
        sa.Column('event_type', sa.String(64), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column('metadata', postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('latency_ms', sa.Integer, nullable=True),
        sa.Column('provider', sa.String(40), nullable=True),
        sa.Column('status', sa.String(32), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    
    # Create indexes for voice_call_events
    op.create_index('ix_voice_call_events_call_id', 'voice_call_events', ['call_id'])
    op.create_index('ix_voice_call_events_session_id', 'voice_call_events', ['session_id'])
    op.create_index('ix_voice_call_events_event_type', 'voice_call_events', ['event_type'])
    op.create_index('ix_voice_call_events_hospital_id', 'voice_call_events', ['hospital_id'])
    op.create_index('ix_voice_call_events_timestamp', 'voice_call_events', ['timestamp'])
    
    # Create voice_call_sessions table for session lifecycle
    op.create_table(
        'voice_call_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hospitals.id', ondelete='CASCADE'), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agents.id', ondelete='SET NULL'), nullable=True),
        sa.Column('call_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('calls.id', ondelete='CASCADE'), nullable=True),
        sa.Column('session_id', sa.String(64), nullable=False, unique=True),
        sa.Column('stream_sid', sa.String(64), nullable=True),
        sa.Column('from_number', sa.String(32), nullable=True),
        sa.Column('to_number', sa.String(32), nullable=True),
        sa.Column('lifecycle_state', sa.String(32), nullable=False, server_default='created'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column('connected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer, nullable=True),
        sa.Column('metadata', postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    
    # Create indexes for voice_call_sessions
    op.create_index('ix_voice_call_sessions_session_id', 'voice_call_sessions', ['session_id'])
    op.create_index('ix_voice_call_sessions_call_id', 'voice_call_sessions', ['call_id'])
    op.create_index('ix_voice_call_sessions_hospital_id', 'voice_call_sessions', ['hospital_id'])
    op.create_index('ix_voice_call_sessions_lifecycle_state', 'voice_call_sessions', ['lifecycle_state'])


def downgrade() -> None:
    op.drop_index('ix_voice_call_sessions_lifecycle_state', table_name='voice_call_sessions')
    op.drop_index('ix_voice_call_sessions_hospital_id', table_name='voice_call_sessions')
    op.drop_index('ix_voice_call_sessions_call_id', table_name='voice_call_sessions')
    op.drop_index('ix_voice_call_sessions_session_id', table_name='voice_call_sessions')
    op.drop_table('voice_call_sessions')
    
    op.drop_index('ix_voice_call_events_timestamp', table_name='voice_call_events')
    op.drop_index('ix_voice_call_events_hospital_id', table_name='voice_call_events')
    op.drop_index('ix_voice_call_events_event_type', table_name='voice_call_events')
    op.drop_index('ix_voice_call_events_session_id', table_name='voice_call_events')
    op.drop_index('ix_voice_call_events_call_id', table_name='voice_call_events')
    op.drop_table('voice_call_events')
    
    op.drop_column('calls', 'response_latency_ms')
    op.drop_column('calls', 'caller_phone')
    op.drop_column('calls', 'stream_sid')
    op.drop_column('calls', 'session_id')
    op.drop_column('calls', 'agent_id')
    
    op.drop_column('conversation_turns', 'metadata')
    op.drop_column('conversation_turns', 'provider')
    op.drop_column('conversation_turns', 'interrupted')
    op.drop_column('conversation_turns', 'language')
    op.drop_column('conversation_turns', 'timestamp_end')
    op.drop_column('conversation_turns', 'timestamp_start')
