"""Add nullable status_code alongside legacy status for rolling compatibility."""

from alembic import op
import sqlalchemy as sa

revision = "76bdc2ef9a10"
down_revision = "c2ee75790b23"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Expand-only: old binaries can continue reading/writing the text status column.
    # New binaries write both columns. NULL is allowed for rows written by old binaries.
    op.add_column("orders", sa.Column("status_code", sa.SmallInteger(), nullable=True))

    # Preserve the original status text. Map unknown legacy values to 0 rather than
    # inventing a false known state. The nullable column supports old/new overlap.
    op.execute("""
        UPDATE orders
        SET status_code = CASE lower(trim(status))
            WHEN 'pending'   THEN 1
            WHEN 'confirmed' THEN 2
            WHEN 'preparing' THEN 3
            WHEN 'ready'     THEN 4
            WHEN 'completed' THEN 5
            WHEN 'cancelled' THEN 6
            ELSE 0
        END
        WHERE status_code IS NULL
    """)

    op.create_check_constraint(
        "ck_orders_status_code_range",
        "orders",
        "status_code IS NULL OR status_code BETWEEN 0 AND 6",
    )


def downgrade() -> None:
    # Safe only while status_code is an additive mirror and status text remains
    # authoritative. Never run automatically as part of application rollback.
    op.drop_constraint("ck_orders_status_code_range", "orders", type_="check")
    op.drop_column("orders", "status_code")
