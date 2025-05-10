"""add_server_defaults

Revision ID: a4376e125863
Revises: 85c7d6b52429
Create Date: 2025-05-10 20:59:17.762083

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a4376e125863'
down_revision: Union[str, None] = '85c7d6b52429'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'users',
        'tariff',
        existing_type=sa.String(),
        nullable=False,
        server_default=''
    )
    op.alter_column(
        'users',
        'tariff_paid',
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.text('FALSE')
    )
    op.alter_column(
        'users',
        'advisors',
        existing_type=sa.JSON(),
        nullable=False,
        server_default=sa.text("'[]'")
    )

def downgrade() -> None:
    # при необходимости — снять server_default
    op.alter_column(
        'users',
        'advisors',
        existing_type=sa.JSON(),
        nullable=False,
        server_default=None
    )
    op.alter_column(
        'users',
        'tariff_paid',
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=None
    )
    op.alter_column(
        'users',
        'tariff',
        existing_type=sa.String(),
        nullable=False,
        server_default=None
    )
