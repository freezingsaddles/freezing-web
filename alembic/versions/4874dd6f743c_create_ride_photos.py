"""create ride_photos

Revision ID: 4874dd6f743c
Revises: 54675468b7bb
Create Date: 2015-01-03 21:57:17.263117

"""

# revision identifiers, used by Alembic.
revision = '4874dd6f743c'
down_revision = '54675468b7bb'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('rides', sa.Column('photos_fetched', sa.Boolean, default=False, nullable=False))
    op.create_table(
        'ride_photos',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=False),
        sa.Column('ride_id',sa.BigInteger, sa.ForeignKey('rides.id', ondelete="cascade"), index=True),
        sa.Column('ref', sa.String(255), nullable=False),
        sa.Column('caption', sa.Text, nullable=True)
    )

def downgrade():
    op.drop_column('rides', 'photos_fetched')
    op.drop_table('ride_photos')
