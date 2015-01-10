"""add ride private col

Revision ID: 56a0f0a1f30d
Revises: 48e1dd00cbd8
Create Date: 2015-01-10 12:59:37.289534

"""

# revision identifiers, used by Alembic.
revision = '56a0f0a1f30d'
down_revision = '48e1dd00cbd8'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('rides', sa.Column('private', sa.Boolean, nullable=False, default=False))

def downgrade():
    op.drop_column('rides', 'private')

