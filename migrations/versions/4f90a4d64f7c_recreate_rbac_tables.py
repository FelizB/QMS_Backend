"""recreate rbac tables

Revision ID: 4f90a4d64f7c
Revises: a6551285427a
Create Date: 2026-04-05 02:54:00.206464

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '4f90a4d64f7c'
down_revision: Union[str, Sequence[str], None] = 'a6551285427a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # roles
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(length=64), nullable=False, unique=True, index=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index("ix_roles_name", "roles", ["name"])

    # role_actions
    op.create_table(
        "role_actions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(length=32), nullable=False, unique=True, index=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index("ix_role_actions_name", "role_actions", ["name"])

    # user_roles
    op.create_table(
        "user_roles",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role_id", sa.Integer, sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("user_id", "role_id", name="uq_user_role"),
    )
    op.create_index("ix_user_roles_user_id", "user_roles", ["user_id"])
    op.create_index("ix_user_roles_role_id", "user_roles", ["role_id"])

    # role_action_grants
    op.create_table(
        "role_action_grants",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("role_id", sa.Integer, sa.ForeignKey("roles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action_id", sa.Integer, sa.ForeignKey("role_actions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=True),
        sa.Column("allow", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("role_id", "action_id", "entity_type", name="uq_role_action_scope"),
    )
    op.create_index("ix_role_action_grants_role_id", "role_action_grants", ["role_id"])
    op.create_index("ix_role_action_grants_action_id", "role_action_grants", ["action_id"])
    op.create_index("ix_role_action_grants_entity_type", "role_action_grants", ["entity_type"])

    # Seed base roles/actions
    op.execute("""
        INSERT INTO roles (name, is_default, is_system)
        VALUES
          ('SUPERADMIN', false, true),
          ('ADMIN',      false, true),
          ('USER',       true,  true)
        ON CONFLICT (name) DO NOTHING;
    """)
    op.execute("""
        INSERT INTO role_actions (name, is_default)
        VALUES
          ('INITIATE', true),
          ('VIEW',     true),
          ('REVIEW',   true),
          ('APPROVE',  true)
        ON CONFLICT (name) DO NOTHING;
    """)


def downgrade():
    op.drop_index("ix_role_action_grants_entity_type", table_name="role_action_grants")
    op.drop_index("ix_role_action_grants_action_id", table_name="role_action_grants")
    op.drop_index("ix_role_action_grants_role_id", table_name="role_action_grants")
    op.drop_table("role_action_grants")

    op.drop_index("ix_user_roles_role_id", table_name="user_roles")
    op.drop_index("ix_user_roles_user_id", table_name="user_roles")
    op.drop_table("user_roles")

    op.drop_index("ix_role_actions_name", table_name="role_actions")
    op.drop_table("role_actions")

    op.drop_index("ix_roles_name", table_name="roles")
    op.drop_table("roles")
