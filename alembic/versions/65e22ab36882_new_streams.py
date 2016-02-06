"""new streams

Revision ID: 65e22ab36882
Revises: 6cca33764ed5
Create Date: 2016-02-06 09:19:10.385309

"""

# revision identifiers, used by Alembic.
revision = '65e22ab36882'
down_revision = '6cca33764ed5'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('ride_tracks', sa.Column('elevation_stream', sa.Text, nullable=True))
    op.add_column('ride_tracks', sa.Column('time_stream', sa.Text, nullable=True))

def downgrade():
    op.drop_column('ride_tracks', 'elevation_stream')
    op.drop_column('ride_tracks', 'time_stream')
