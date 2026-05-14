"""rev1

Create Date: 2026-03-01 10:00:00.000000
"""
# -- squawk-ignore-file ban-drop-column

revision = "rev1"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    import sqlalchemy as sa
    from alembic import op

    op.create_table("users", sa.Column("id", sa.Integer(), primary_key=True))


def downgrade() -> None:
    from alembic import op

    op.drop_table("users")
