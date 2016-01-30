"""photo fields

Revision ID: ca3d5036d720
Revises: 41c3e58a61aa
Create Date: 2016-01-29 23:37:06.942789

"""

# revision identifiers, used by Alembic.
revision = 'ca3d5036d720'
down_revision = '41c3e58a61aa'

from alembic import op
import sqlalchemy as sa


def upgrade():

    op.add_column('ride_photos', sa.Column('source', sa.Integer, nullable=False, default=2))
    op.execute('update ride_photos set source=2')

    op.alter_column('ride_photos', 'id', type_=sa.String(255), existing_nullable=False)
    op.execute('update ride_photos set id=uid')

    op.drop_column('ride_photos', 'uid')
    op.add_column('ride_photos', sa.Column('img_t', sa.String(255), nullable=True))
    op.add_column('ride_photos', sa.Column('img_l', sa.String(255), nullable=True))

    op.add_column('ride_photos', sa.Column('primary', sa.Boolean, nullable=False, default=False))


def downgrade():
    op.drop_column('ride_photos', 'img_t')
    op.drop_column('ride_photos', 'img_l')
    op.drop_column('ride_photos', 'source')
    op.alter_column('ride_photos', 'id', type_=sa.BigInteger, existing_nullable=False)
    op.add_column('ride_photos', sa.Column('uid', sa.String(255), nullable=False))
    op.execute('update ride_photos set uid=id')

    op.drop_column('ride_photos', 'primary')