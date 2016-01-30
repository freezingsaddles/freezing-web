"""bookkeeping

Revision ID: 41c3e58a61aa
Revises: 17b73a90925d
Create Date: 2016-01-29 21:58:13.978603

"""

# revision identifiers, used by Alembic.
revision = '41c3e58a61aa'
down_revision = '17b73a90925d'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('rides', sa.Column('detail_fetched', sa.Boolean, nullable=False, default=False))


def downgrade():
    op.drop_column('rides', 'detail_fetched')
