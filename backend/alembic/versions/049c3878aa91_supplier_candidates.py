"""supplier_candidates

Revision ID: 049c3878aa91
Revises: d72639185693
Create Date: 2026-04-07 21:39:02.324291

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "049c3878aa91"
down_revision: Union[str, Sequence[str], None] = "d72639185693"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "supplier_candidates",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("job_id", sa.UUID(), sa.ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("component_id", sa.UUID(), sa.ForeignKey("components.id", ondelete="CASCADE"), nullable=True),
        sa.Column(
            "category_ids",
            postgresql.ARRAY(sa.UUID()),
            nullable=False,
            server_default=sa.text("'{}'::uuid[]"),
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False, server_default="company"),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("website", sa.String(length=500), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("notes", sa.String(length=2000), nullable=True),
        sa.Column("completeness", sa.String(length=20), nullable=False, server_default="incomplete"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_supplier_candidates_status"), "supplier_candidates", ["status"], unique=False)
    op.create_index(op.f("ix_supplier_candidates_component_id"), "supplier_candidates", ["component_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_supplier_candidates_component_id"), table_name="supplier_candidates")
    op.drop_index(op.f("ix_supplier_candidates_status"), table_name="supplier_candidates")
    op.drop_table("supplier_candidates")
