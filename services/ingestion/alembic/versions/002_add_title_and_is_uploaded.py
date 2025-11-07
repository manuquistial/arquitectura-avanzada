"""Add title and is_uploaded columns to document_metadata

Revision ID: 002
Revises: 001
Create Date: 2025-11-06 19:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add title and is_uploaded columns."""
    
    # Add title column (nullable, can use filename as fallback)
    op.add_column('document_metadata',
        sa.Column('title', sa.String(500), nullable=True))
    
    # Add is_uploaded column (boolean flag to track if file was uploaded)
    op.add_column('document_metadata',
        sa.Column('is_uploaded', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    """Remove title and is_uploaded columns."""
    
    op.drop_column('document_metadata', 'is_uploaded')
    op.drop_column('document_metadata', 'title')

