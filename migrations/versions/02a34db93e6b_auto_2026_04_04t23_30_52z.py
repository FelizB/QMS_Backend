"""auto: 2026-04-04T23:30:52Z

Revision ID: 02a34db93e6b
Revises: f5432ee51d5f
Create Date: 2026-04-05 02:30:53.179698

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '02a34db93e6b'
down_revision: Union[str, Sequence[str], None] = 'f5432ee51d5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # 1) Add nullable first
    op.add_column(
        "roles",
        sa.Column("is_system", sa.Boolean(), nullable=True),
    )

    # 2) Backfill existing rows (choose your policy)
    # Most conservative: existing roles are not system unless they match known names
    op.execute("""
        UPDATE roles
        SET is_system = CASE
            WHEN UPPER(name) IN ('SUPERADMIN', 'ADMIN', 'USER') THEN TRUE
            ELSE FALSE
        END
        WHERE is_system IS NULL;
    """)

    # 3) Set NOT NULL after backfill
    op.alter_column("roles", "is_system", nullable=False)

    # 4) Optional: set server default so future inserts never create NULL
    op.alter_column("roles", "is_system", server_default=sa.text("false"))

    # 5) Ensure base roles exist (by name, not fixed IDs)
    op.execute("""
        INSERT INTO roles (name, is_default, is_system)
        VALUES
            ('SUPERADMIN', false, true),
            ('ADMIN',      false, true),
            ('USER',       true,  true)
        ON CONFLICT (name) DO NOTHING;
    """)

    # Optional: enforce only one default role
    # (Do this only if you want strict single-default)
    # op.execute("""
    #     UPDATE roles SET is_default = false WHERE UPPER(name) <> 'USER';
    # """)


def downgrade():
    # Remove is_system column
    op.drop_column("roles", "is_system")
