"""Add image_data column to analysis table

Revision ID: 2f7ffe9d7094
Revises: eec5331a1c96
Create Date: 2024-09-20 10:34:08.364859

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2f7ffe9d7094'
down_revision = 'eec5331a1c96'
branch_labels = None
depends_on = None


def upgrade():
    # Add image_data column without NOT NULL constraint
    op.add_column('analysis', sa.Column('image_data', sa.LargeBinary()))
    
    # Update existing records with empty binary data
    op.execute("UPDATE analysis SET image_data = decode('', 'hex') WHERE image_data IS NULL")
    
    # Add NOT NULL constraint
    op.alter_column('analysis', 'image_data', nullable=False)


def downgrade():
    op.drop_column('analysis', 'image_data')
