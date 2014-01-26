"""manual column

Revision ID: 54675468b7bb
Revises: 628c4c0afbd
Create Date: 2014-01-26 16:00:30.188553

"""

# revision identifiers, used by Alembic.
revision = '54675468b7bb'
down_revision = '628c4c0afbd'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('rides', sa.Column('manual', sa.Boolean, nullable=True))

def downgrade():
    op.drop_column('rides', 'manual')

