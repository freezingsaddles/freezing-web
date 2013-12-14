"""add athlete display name

Revision ID: a3aee1eb0fb
Revises: 3361172cfdc9
Create Date: 2013-12-13 21:07:17.918398

"""

# revision identifiers, used by Alembic.
revision = 'a3aee1eb0fb'
down_revision = '3361172cfdc9'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('athletes', sa.Column('display_name', sa.String(255)))


def downgrade():
    op.drop_column('athletes', 'display_name')
