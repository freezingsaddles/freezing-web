"""ride tracks

Revision ID: 17b73a90925d
Revises: 54627e8199c9
Create Date: 2016-01-28 21:23:28.391271

"""

# revision identifiers, used by Alembic.
revision = '17b73a90925d'
down_revision = '54627e8199c9'

from alembic import op
import sqlalchemy as sa
import geoalchemy as ga


def upgrade():

    t = op.create_table(
        'ride_tracks',
        sa.Column('ride_id',sa.BigInteger, sa.ForeignKey('rides.id', ondelete="cascade"), primary_key=True, autoincrement=False),
        ga.GeometryExtensionColumn('gps_track', ga.LineString(2), nullable=False)
    )
    ga.GeometryDDL(t)

    op.add_column('rides', sa.Column('track_fetched', sa.Boolean, default=None, nullable=True))
    op.execute('update rides set track_fetched = false where manual = false')


def downgrade():
    op.drop_column('rides', 'track_fetched')
    op.drop_table('ride_tracks')
