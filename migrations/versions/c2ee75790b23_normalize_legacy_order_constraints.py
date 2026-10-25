
"""Normalize legacy order constraints."""

from alembic import op
import sqlalchemy as sa

revision = "c2ee75790b23"
down_revision = "0dcdba84e47f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Backfill missing timestamps before enforcing NOT NULL.
    op.execute("""
        UPDATE orders
        SET created_at = NOW()
        WHERE created_at IS NULL
    """)

    # Preserve existing statuses; use 'unknown' only for NULL values.
    op.execute("""
        UPDATE orders
        SET status = 'unknown'
        WHERE status IS NULL
    """)

    # Normalize status to match the current ORM.
    op.alter_column(
        "orders",
        "status",
        existing_type=sa.Text(),
        type_=sa.String(length=30),
        postgresql_using="status::varchar(30)",
        nullable=False,
    )

    op.alter_column(
        "orders",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("NOW()"),
    )


def downgrade() -> None:
    # Restore the legacy types/nullability.
    op.alter_column(
        "orders",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
        server_default=None,
    )

    op.alter_column(
        "orders",
        "status",
        existing_type=sa.String(length=30),
        type_=sa.Text(),
        postgresql_using="status::text",
        nullable=True,
    )
