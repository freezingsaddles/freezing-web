"""real utf8

Revision ID: a77103b34b0b
Revises: 22183530616d
Create Date: 2016-01-30 20:23:46.846779

"""

# revision identifiers, used by Alembic.
revision = 'a77103b34b0b'
down_revision = '22183530616d'

from alembic import op
import sqlalchemy as sa


def upgrade():

    # NOTE: Max varchar size is 191 for indexing
    op.alter_column('ride_photos', 'id', type_=sa.String(191), existing_nullable=False)

    op.execute('ALTER TABLE ride_photos CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_bin')
    op.execute('ALTER TABLE rides CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_bin')
    op.execute('ALTER TABLE ride_errors CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_bin')
    op.execute('ALTER TABLE teams CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_bin')


def downgrade():
    pass
