"""nullable ride_photos ref

Revision ID: c5bfe51cfec3
Revises: 74b6566816aa
Create Date: 2018-01-02 21:32:46.526984

"""

# revision identifiers, used by Alembic.
revision = 'c5bfe51cfec3'
down_revision = '74b6566816aa'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column('ride_photos', 'ref', existing_type=sa.String(255), nullable=True)


def downgrade():
    op.alter_column('ride_photos', 'ref', existing_type=sa.String(255), nullable=False)
