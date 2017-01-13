"""observer teams

Revision ID: 74b6566816aa
Revises: 65e22ab36882
Create Date: 2017-01-13 07:53:55.581320

"""

# revision identifiers, used by Alembic.
revision = '74b6566816aa'
down_revision = '65e22ab36882'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('teams', sa.Column('leaderboard_exclude', sa.Boolean, nullable=False, default=False))

def downgrade():
    op.drop_column('teams', 'leaderboard_exclude')
