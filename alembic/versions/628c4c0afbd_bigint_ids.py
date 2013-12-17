"""bigint ids

Revision ID: 628c4c0afbd
Revises: a3aee1eb0fb
Create Date: 2013-12-16 20:33:56.247834

"""

# revision identifiers, used by Alembic.
revision = '628c4c0afbd'
down_revision = 'a3aee1eb0fb'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # We are actually skipping the ones that shouldn't matter ...
    #op.alter_column('teams', 'id', type_=sa.BigInteger, existing_nullable=False)
    #op.alter_column('athletes', 'id', existing_type=sa.Integer, type_=sa.BigInteger, existing_nullable=False)
    #op.alter_column('athletes', 'team_id', existing_type=sa.Integer, type_=sa.BigInteger, existing_nullable=False)
    op.alter_column('rides', 'id', existing_type=sa.Integer, type_=sa.BigInteger, existing_nullable=False)
    #op.alter_column('rides', 'athlete_id', existing_type=sa.Integer, type_=sa.BigInteger, existing_nullable=False)
    op.alter_column('ride_efforts', 'id', existing_type=sa.Integer, type_=sa.BigInteger, existing_nullable=False)
    op.alter_column('ride_efforts', 'ride_id', existing_type=sa.Integer, type_=sa.BigInteger, existing_nullable=False)
    op.alter_column('ride_efforts', 'segment_id', existing_type=sa.Integer, type_=sa.BigInteger, existing_nullable=False)
    op.alter_column('ride_weather', 'ride_id', existing_type=sa.Integer, type_=sa.BigInteger, existing_nullable=False)
    op.alter_column('ride_geo', 'ride_id', existing_type=sa.Integer, type_=sa.BigInteger, existing_nullable=False)

def downgrade():
    raise NotImplementedError('data loss would ensue.  gotta love mysql.')