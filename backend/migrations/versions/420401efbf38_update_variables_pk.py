# Copyright 2024 Google Inc
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""ML models variables update to allow for variable reuse with different comparison values.

Revision ID: 420401efbf38
Revises: 8b95ad532329
Create Date: 2024-05-29 19:44:46.732614

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '420401efbf38'
down_revision = '8b95ad532329'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint('ml_model_variables_ibfk_1', 'ml_model_variables', type_='foreignkey')
    op.drop_constraint('PRIMARY', 'ml_model_variables', type_='primary')
    with op.batch_alter_table('ml_model_variables', schema=None) as batch_op:
        batch_op.add_column(sa.Column('id', sa.Integer()))
    op.create_primary_key('PRIMARY', 'ml_model_variables', ['id'])
    op.execute('ALTER TABLE ml_model_variables MODIFY id INTEGER NOT NULL AUTO_INCREMENT;')
    op.create_foreign_key(
        'ml_model_variables_ibfk_1', 'ml_model_variables', 'ml_models',
        ['ml_model_id'], ['id'])


def downgrade():
    op.drop_constraint('ml_model_variables_ibfk_1', 'ml_model_variables', type_='foreignkey')
    op.drop_constraint('PRIMARY', 'ml_model_variables', type_='primary')
    with op.batch_alter_table('ml_model_variables', schema=None) as batch_op:
        batch_op.drop_column('id')
    op.create_primary_key(
        'PRIMARY', 'ml_model_variables',
        ['ml_model_id', 'name'])
    op.create_foreign_key(
        'ml_model_variables_ibfk_1', 'ml_model_variables', 'ml_models',
        ['ml_model_id'], ['id'])
