"""Merge add_rag_models and 1a31ce608336

Revision ID: 68b0f4e63010
Revises: 1a31ce608336, add_rag_models
Create Date: 2025-04-10 13:22:04.059968

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = '68b0f4e63010'
down_revision = ('1a31ce608336', 'add_rag_models')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
