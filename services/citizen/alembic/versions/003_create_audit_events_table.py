"""Create audit_events table

Revision ID: 003
Revises: 002
Create Date: 2025-10-13 08:15:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create audit_events table for compliance logging."""
    
    # Create audit_events table
    op.create_table(
        'audit_events',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('event_type', sa.String(100), nullable=False, index=True),
        sa.Column('user_id', sa.String(100), nullable=True, index=True),
        sa.Column('user_email', sa.String(255), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('service_name', sa.String(50), nullable=False, index=True),
        sa.Column('resource_type', sa.String(50), nullable=True, index=True),
        sa.Column('resource_id', sa.String(100), nullable=True, index=True),
        sa.Column('action', sa.String(50), nullable=False, index=True),
        sa.Column('status', sa.String(20), nullable=False, index=True),
        sa.Column('details', JSONB, nullable=True),
        sa.Column('request_id', sa.String(100), nullable=True, index=True),
        sa.Column('trace_id', sa.String(100), nullable=True, index=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('changes', JSONB, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
    )
    
    # Create indexes for common queries
    op.create_index('idx_audit_timestamp', 'audit_events', ['timestamp'])
    op.create_index('idx_audit_user_timestamp', 'audit_events', ['user_id', 'timestamp'])
    op.create_index('idx_audit_resource', 'audit_events', ['resource_type', 'resource_id'])
    op.create_index('idx_audit_action_status', 'audit_events', ['action', 'status'])
    
    # Create partial index for failures
    op.execute("""
        CREATE INDEX idx_audit_failures 
        ON audit_events (timestamp DESC) 
        WHERE status = 'failure'
    """)
    
    # Create GIN index for JSONB columns
    op.execute("CREATE INDEX idx_audit_details_gin ON audit_events USING GIN (details)")
    op.execute("CREATE INDEX idx_audit_changes_gin ON audit_events USING GIN (changes)")


def downgrade() -> None:
    """Drop audit_events table."""
    op.drop_table('audit_events')

