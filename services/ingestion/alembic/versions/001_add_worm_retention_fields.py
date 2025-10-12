"""Add WORM and retention fields to document_metadata

Revision ID: 001
Revises: 
Create Date: 2025-10-12 20:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add WORM and retention fields."""
    
    # Add new columns
    op.add_column('document_metadata',
        sa.Column('state', sa.String(20), nullable=False, server_default='UNSIGNED'))
    
    op.add_column('document_metadata',
        sa.Column('worm_locked', sa.Boolean(), nullable=False, server_default='false'))
    
    op.add_column('document_metadata',
        sa.Column('signed_at', sa.DateTime(), nullable=True))
    
    op.add_column('document_metadata',
        sa.Column('retention_until', sa.Date(), nullable=True))
    
    op.add_column('document_metadata',
        sa.Column('hub_signature_ref', sa.String(255), nullable=True))
    
    op.add_column('document_metadata',
        sa.Column('legal_hold', sa.Boolean(), nullable=False, server_default='false'))
    
    op.add_column('document_metadata',
        sa.Column('lifecycle_tier', sa.String(20), nullable=False, server_default='Hot'))
    
    # Add indexes for common queries
    op.create_index('idx_document_state', 'document_metadata', ['state'])
    op.create_index('idx_document_worm', 'document_metadata', ['worm_locked'])
    op.create_index('idx_document_retention', 'document_metadata', ['retention_until'])
    op.create_index('idx_document_tier', 'document_metadata', ['lifecycle_tier'])
    
    # Create WORM enforcement function
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_worm_update()
        RETURNS TRIGGER AS $$
        BEGIN
            -- If document is WORM-locked, prevent modification of critical fields
            IF OLD.worm_locked = TRUE THEN
                -- Check if trying to modify WORM-protected fields
                IF (NEW.worm_locked = FALSE OR
                    NEW.state != OLD.state OR
                    NEW.retention_until != OLD.retention_until OR
                    NEW.hub_signature_ref IS DISTINCT FROM OLD.hub_signature_ref OR
                    NEW.signed_at IS DISTINCT FROM OLD.signed_at OR
                    NEW.sha256_hash != OLD.sha256_hash OR
                    NEW.blob_name != OLD.blob_name) THEN
                    
                    RAISE EXCEPTION 'Cannot modify WORM-locked document. Document ID: %. Protected fields are immutable.', OLD.id
                        USING HINT = 'WORM (Write Once Read Many) policy prevents modification of signed documents';
                END IF;
                
                -- Legal hold prevents deletion
                IF OLD.legal_hold = TRUE AND NEW.is_deleted = TRUE THEN
                    RAISE EXCEPTION 'Cannot delete document under legal hold. Document ID: %', OLD.id
                        USING HINT = 'Remove legal hold before attempting deletion';
                END IF;
            END IF;
            
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger
    op.execute("""
        CREATE TRIGGER enforce_worm_immutability
        BEFORE UPDATE ON document_metadata
        FOR EACH ROW
        EXECUTE FUNCTION prevent_worm_update();
    """)
    
    # Create function to auto-calculate retention for SIGNED documents (5 years)
    op.execute("""
        CREATE OR REPLACE FUNCTION set_retention_on_sign()
        RETURNS TRIGGER AS $$
        BEGIN
            -- When state changes to SIGNED, auto-set retention if not set
            IF NEW.state = 'SIGNED' AND OLD.state != 'SIGNED' THEN
                IF NEW.retention_until IS NULL THEN
                    NEW.retention_until := CURRENT_DATE + INTERVAL '5 years';
                END IF;
                
                -- Auto-set signed_at if not set
                IF NEW.signed_at IS NULL THEN
                    NEW.signed_at := NOW();
                END IF;
            END IF;
            
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger for auto-retention
    op.execute("""
        CREATE TRIGGER auto_set_retention
        BEFORE UPDATE ON document_metadata
        FOR EACH ROW
        EXECUTE FUNCTION set_retention_on_sign();
    """)


def downgrade() -> None:
    """Remove WORM and retention fields."""
    
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS enforce_worm_immutability ON document_metadata")
    op.execute("DROP TRIGGER IF EXISTS auto_set_retention ON document_metadata")
    
    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS prevent_worm_update()")
    op.execute("DROP FUNCTION IF EXISTS set_retention_on_sign()")
    
    # Drop indexes
    op.drop_index('idx_document_tier', 'document_metadata')
    op.drop_index('idx_document_retention', 'document_metadata')
    op.drop_index('idx_document_worm', 'document_metadata')
    op.drop_index('idx_document_state', 'document_metadata')
    
    # Drop columns
    op.drop_column('document_metadata', 'lifecycle_tier')
    op.drop_column('document_metadata', 'legal_hold')
    op.drop_column('document_metadata', 'hub_signature_ref')
    op.drop_column('document_metadata', 'retention_until')
    op.drop_column('document_metadata', 'signed_at')
    op.drop_column('document_metadata', 'worm_locked')
    op.drop_column('document_metadata', 'state')

