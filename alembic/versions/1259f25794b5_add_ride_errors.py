"""add ride_errors

Revision ID: 1259f25794b5
Revises: 56a0f0a1f30d
Create Date: 2016-01-02 15:29:11.423185

"""

# revision identifiers, used by Alembic.
revision = '1259f25794b5'
down_revision = '56a0f0a1f30d'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'ride_errors',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=False),
        sa.Column('name', sa.String(1024), nullable=False),
        sa.Column('athlete_id',sa.Integer, sa.ForeignKey('athletes.id', ondelete="cascade"), nullable=False, index=True),
        sa.Column('start_date', sa.DateTime, nullable=False, index=True),
        sa.Column('last_seen', sa.DateTime, nullable=False, index=True),
        sa.Column('reason', sa.String(1024), nullable=False)
    )



def downgrade():
    op.drop_table('ride_errors')
