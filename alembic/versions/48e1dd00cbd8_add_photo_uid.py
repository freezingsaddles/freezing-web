"""add photo uid

Revision ID: 48e1dd00cbd8
Revises: 8925b9da7d7
Create Date: 2015-01-04 22:36:15.020260

"""

# revision identifiers, used by Alembic.
revision = '48e1dd00cbd8'
down_revision = '8925b9da7d7'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('ride_photos', sa.Column('uid', sa.String(255), nullable=True))


def downgrade():
    op.drop_column('ride_photos', 'uid')
