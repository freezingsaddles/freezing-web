"""drop global_privacy col

Revision ID: 8925b9da7d7
Revises: 180c13f61b54
Create Date: 2015-01-04 13:07:33.140627

"""

# revision identifiers, used by Alembic.
revision = '8925b9da7d7'
down_revision = '180c13f61b54'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_column('athletes', 'global_privacy')
    

def downgrade():
    op.add_column('athletes', sa.Column('global_privacy', sa.Boolean, default=False, nullable=False))
