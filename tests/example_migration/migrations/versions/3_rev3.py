"""rev3

Create Date: 2026-03-03 10:00:00.000000
"""

revision = "rev3"
down_revision = "rev2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from alembic import op

    op.execute("CREATE INDEX idx_users_email ON users (email)")


def downgrade() -> None:
    from alembic import op

    op.execute("DROP INDEX idx_users_email")
