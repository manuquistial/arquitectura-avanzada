"""Create users table for Azure AD B2C integration

Revision ID: 002_create_users
Revises: 001_create_citizens
Create Date: 2025-10-12 23:30:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY

# revision identifiers, used by Alembic
revision = '002_create_users'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(255), primary_key=True, comment='Azure AD B2C user ID (sub claim)'),
        sa.Column('email', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('given_name', sa.String(255), nullable=True),
        sa.Column('family_name', sa.String(255), nullable=True),
        
        # Azure AD B2C specific fields
        sa.Column('azure_b2c_object_id', sa.String(255), nullable=True, unique=True, index=True),
        sa.Column('idp', sa.String(100), nullable=True, comment='Identity Provider (Azure AD, Google, etc.)'),
        
        # Roles and permissions (ABAC)
        sa.Column('roles', ARRAY(sa.String), nullable=False, default=[], server_default='{}'),
        sa.Column('permissions', ARRAY(sa.String), nullable=False, default=[], server_default='{}'),
        
        # Status
        sa.Column('is_active', sa.Boolean, nullable=False, default=True, server_default='true'),
        sa.Column('is_verified', sa.Boolean, nullable=False, default=False, server_default='false'),
        sa.Column('email_verified', sa.Boolean, nullable=False, default=False, server_default='false'),
        
        # Metadata
        sa.Column('operator_id', sa.String(255), nullable=True, comment='Operator ID for multi-tenant'),
        sa.Column('preferred_language', sa.String(10), nullable=True, default='es'),
        sa.Column('timezone', sa.String(50), nullable=True, default='America/Bogota'),
        
        # Audit fields
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_login_at', sa.DateTime, nullable=True),
        sa.Column('deleted_at', sa.DateTime, nullable=True, comment='Soft delete'),
    )

    # Create indexes
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_azure_b2c_object_id', 'users', ['azure_b2c_object_id'])
    op.create_index('idx_users_operator_id', 'users', ['operator_id'])
    op.create_index('idx_users_is_active', 'users', ['is_active'])
    op.create_index('idx_users_roles', 'users', ['roles'], postgresql_using='gin')
    
    # Create trigger for updated_at
    op.execute("""
        CREATE OR REPLACE FUNCTION update_users_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    op.execute("""
        CREATE TRIGGER trigger_update_users_updated_at
        BEFORE UPDATE ON users
        FOR EACH ROW
        EXECUTE FUNCTION update_users_updated_at();
    """)


def downgrade() -> None:
    # Drop trigger first
    op.execute('DROP TRIGGER IF EXISTS trigger_update_users_updated_at ON users')
    op.execute('DROP FUNCTION IF EXISTS update_users_updated_at()')
    
    # Drop indexes
    op.drop_index('idx_users_roles', table_name='users')
    op.drop_index('idx_users_is_active', table_name='users')
    op.drop_index('idx_users_operator_id', table_name='users')
    op.drop_index('idx_users_azure_b2c_object_id', table_name='users')
    op.drop_index('idx_users_email', table_name='users')
    
    # Drop table
    op.drop_table('users')

