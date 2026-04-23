"""auto: 2026-03-13T06:54:54Z

Revision ID: 1f7497ecc657
Revises: d8af10c5657d
Create Date: 2026-03-13 09:54:55.269312

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '1f7497ecc657'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Drop known unique artifacts if they exist
    try:
        op.drop_constraint("uq_portfolios_category", "portfolios", type_="unique")
    except Exception:
        pass

    for idx in ("uq_portfolios_category", "uq_portfolios_category_active", "uq_portfolios_category_ci"):
        op.execute(f'DROP INDEX IF EXISTS "{idx}"')

    # Optional: non-unique index for lookups
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_portfolios_category
        ON portfolios (category)
        WHERE category IS NOT NULL
    """)


def downgrade():
    op.execute('DROP INDEX IF EXISTS "ix_portfolios_category"')
    # (Intentional: we do NOT restore uniqueness on downgrade)
