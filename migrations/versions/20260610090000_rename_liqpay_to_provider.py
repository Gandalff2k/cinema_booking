"""rename transactions.liqpay_order_id -> provider_payment_id

Revision ID: b1c2d3e4f5a6
Revises: add6a4bd514b
Create Date: 2026-06-10 09:00:00.000000

The payment provider moved from LiqPay to Stripe; the column now stores a
Stripe payment intent, so it is renamed to a provider-neutral name.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "b1c2d3e4f5a6"
down_revision = "add6a4bd514b"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "transactions",
        "liqpay_order_id",
        new_column_name="provider_payment_id",
    )


def downgrade():
    op.alter_column(
        "transactions",
        "provider_payment_id",
        new_column_name="liqpay_order_id",
    )
