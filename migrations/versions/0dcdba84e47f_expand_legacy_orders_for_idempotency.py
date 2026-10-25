
"""Expand legacy orders for idempotency."""

from alembic import op
import sqlalchemy as sa

revision = "0dcdba84e47f"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Preserve legacy UUID user IDs as their canonical string form.
    op.alter_column(
        "orders",
        "user_id",
        existing_type=sa.dialects.postgresql.UUID(),
        type_=sa.String(length=100),
        postgresql_using="user_id::text",
        nullable=False,
    )

    # Add new fields as nullable first.
    op.add_column("orders", sa.Column("vendor_id", sa.String(100), nullable=True))
    op.add_column("orders", sa.Column("items", sa.JSON(), nullable=True))
    op.add_column("orders", sa.Column("idempotency_key", sa.String(255), nullable=True))
    op.add_column("orders", sa.Column("request_hash", sa.String(64), nullable=True))

    # Legacy records have no original vendor/items or request payload.
    # Mark them explicitly; do not pretend these are real order details.
    op.execute("""
        UPDATE orders
        SET vendor_id = 'legacy',
            items = '[]'::json,
            idempotency_key = 'legacy:' || id::text,
            request_hash = repeat('0', 64)
        WHERE vendor_id IS NULL
           OR items IS NULL
           OR idempotency_key IS NULL
           OR request_hash IS NULL
    """)

    op.alter_column("orders", "vendor_id", nullable=False)
    op.alter_column("orders", "items", nullable=False)
    op.alter_column("orders", "idempotency_key", nullable=False)
    op.alter_column("orders", "request_hash", nullable=False)

    op.create_unique_constraint(
        "uq_orders_user_idempotency",
        "orders",
        ["user_id", "idempotency_key"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_orders_user_idempotency",
        "orders",
        type_="unique",
    )
    op.drop_column("orders", "request_hash")
    op.drop_column("orders", "idempotency_key")
    op.drop_column("orders", "items")
    op.drop_column("orders", "vendor_id")

    # Restore the original UUID type.
    # This succeeds only if every user_id is a valid UUID.
    op.alter_column(
        "orders",
        "user_id",
        existing_type=sa.String(length=100),
        type_=sa.dialects.postgresql.UUID(),
        postgresql_using="user_id::uuid",
        nullable=True,
    )
