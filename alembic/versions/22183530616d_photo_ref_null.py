"""photo ref null

Revision ID: 22183530616d
Revises: ca3d5036d720
Create Date: 2016-01-30 14:48:33.771451

"""

# revision identifiers, used by Alembic.
revision = '22183530616d'
down_revision = 'ca3d5036d720'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column('ride_photos', 'ref', nullable=True, server_default=None, existing_type=sa.String(255))


def downgrade():
    op.alter_column('ride_photos', 'ref', nullable=False, server_default=False, existing_type=sa.String(255))

