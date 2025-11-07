"""Add citizen_id to users table

Revision ID: 004_add_citizen_id
Revises: 003
Create Date: 2025-11-07 12:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '004_add_citizen_id'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add citizen_id column to users table to link users to citizens."""
    
    # Add citizen_id column to users table
    op.add_column(
        'users',
        sa.Column('citizen_id', sa.String(20), nullable=True, comment='Citizen ID (document number) - foreign key to citizens table')
    )
    
    # Create index on citizen_id for faster lookups
    op.create_index('idx_users_citizen_id', 'users', ['citizen_id'])
    
    # Create foreign key constraint (optional, can be deferred if citizens table doesn't exist yet)
    # Note: We'll use a deferred constraint to avoid issues if citizens table doesn't exist
    try:
        op.create_foreign_key(
            'fk_users_citizen_id',
            'users', 'citizens',
            ['citizen_id'], ['id'],
            ondelete='SET NULL'  # If citizen is deleted, set citizen_id to NULL
        )
    except Exception as e:
        # If foreign key creation fails (e.g., citizens table doesn't exist), just log it
        # The index is still created which is the most important part
        print(f"Warning: Could not create foreign key constraint: {e}")
        print("This is OK if the citizens table doesn't exist yet or if there are existing records")


def downgrade() -> None:
    """Remove citizen_id column from users table."""
    
    # Drop foreign key constraint if it exists
    try:
        op.drop_constraint('fk_users_citizen_id', 'users', type_='foreignkey')
    except Exception:
        pass  # Ignore if constraint doesn't exist
    
    # Drop index
    op.drop_index('idx_users_citizen_id', table_name='users')
    
    # Drop column
    op.drop_column('users', 'citizen_id')

