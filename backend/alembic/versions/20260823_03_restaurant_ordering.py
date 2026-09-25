"""Add restaurant menu and order tables

Revision ID: 20260823_03
Revises: 20260823_02
Create Date: 2026-08-23
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260823_03"
down_revision = "20260823_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create menu_items table
    op.create_table(
        'menu_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hospitals.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('price', sa.Numeric(10, 2), nullable=False),
        sa.Column('is_available', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('preparation_time_minutes', sa.Integer(), nullable=False, server_default=15),
        sa.Column('metadata', postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    
    # Create indexes for menu_items
    op.create_index('ix_menu_items_hospital_id', 'menu_items', ['hospital_id'])
    op.create_index('ix_menu_items_category', 'menu_items', ['category'])
    op.create_index('ix_menu_items_is_available', 'menu_items', ['is_available'])
    
    # Create orders table
    op.create_table(
        'orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('hospital_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('hospitals.id', ondelete='CASCADE'), nullable=False),
        sa.Column('call_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('calls.id', ondelete='SET NULL'), nullable=True),
        sa.Column('customer_phone', sa.String(32), nullable=False),
        sa.Column('customer_name', sa.String(200), nullable=True),
        sa.Column('delivery_address', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('total_amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='INR'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    # Create indexes for orders
    op.create_index('ix_orders_hospital_id', 'orders', ['hospital_id'])
    op.create_index('ix_orders_call_id', 'orders', ['call_id'])
    op.create_index('ix_orders_customer_phone', 'orders', ['customer_phone'])
    op.create_index('ix_orders_status', 'orders', ['status'])
    op.create_index('ix_orders_created_at', 'orders', ['created_at'])
    
    # Create order_items table
    op.create_table(
        'order_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('menu_item_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('menu_items.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('unit_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('subtotal', sa.Numeric(10, 2), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    
    # Create indexes for order_items
    op.create_index('ix_order_items_order_id', 'order_items', ['order_id'])
    op.create_index('ix_order_items_menu_item_id', 'order_items', ['menu_item_id'])


def downgrade() -> None:
    op.drop_index('ix_order_items_menu_item_id', table_name='order_items')
    op.drop_index('ix_order_items_order_id', table_name='order_items')
    op.drop_table('order_items')
    
    op.drop_index('ix_orders_created_at', table_name='orders')
    op.drop_index('ix_orders_status', table_name='orders')
    op.drop_index('ix_orders_customer_phone', table_name='orders')
    op.drop_index('ix_orders_call_id', table_name='orders')
    op.drop_index('ix_orders_hospital_id', table_name='orders')
    op.drop_table('orders')
    
    op.drop_index('ix_menu_items_is_available', table_name='menu_items')
    op.drop_index('ix_menu_items_category', table_name='menu_items')
    op.drop_index('ix_menu_items_hospital_id', table_name='menu_items')
    op.drop_table('menu_items')
