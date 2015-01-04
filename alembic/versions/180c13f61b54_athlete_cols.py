"""additional athlete columns

Revision ID: 180c13f61b54
Revises: 4874dd6f743c
Create Date: 2015-01-04 12:42:26.951868

"""

# revision identifiers, used by Alembic.
revision = '180c13f61b54'
down_revision = '4874dd6f743c'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('athletes', sa.Column('global_privacy', sa.Boolean, default=False, nullable=False))
    op.add_column('athletes', sa.Column('profile_photo', sa.String(255), nullable=True))


def downgrade():
    op.drop_column('athletes', 'global_privacy')
    op.drop_column('athletes', 'profile_photo')

