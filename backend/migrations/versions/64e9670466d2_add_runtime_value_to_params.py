"""add runtime value to params

Revision ID: 64e9670466d2
Revises: e34417c82307
Create Date: 2018-11-27 10:48:19.305460

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '64e9670466d2'
down_revision = 'e34417c82307'
branch_labels = None
depends_on = None


def upgrade():
  op.add_column('params', sa.Column('runtime_value', sa.Text(), nullable=True))

def downgrade():
  op.drop_column('params', 'runtime_value')
