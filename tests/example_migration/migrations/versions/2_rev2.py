"""rev2

Create Date: 2026-03-02 10:00:00.000000
"""
# squawk-disable require-concurrent-index-creation
# -- squawk-ignore-file ban-add-column-default

revision = "rev2"
down_revision = "rev1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    import sqlalchemy as sa
    from alembic import op

    op.add_column("users", sa.Column("email", sa.String(255)))


def downgrade() -> None:
    from alembic import op

    op.drop_column("users", "email")
