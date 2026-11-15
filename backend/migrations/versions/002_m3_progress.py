"""PR-1: persist enrolment on the shared schema.

Revision ID: 002_m3_progress
Revises: 001_initial_schema
"""

import sqlalchemy as sa
from alembic import op

revision = "002_m3_progress"
down_revision = "001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "progress",
        sa.Column("progress_id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(),
                  sa.ForeignKey("student.student_id", ondelete="CASCADE"), nullable=False),
        sa.Column("resource_id", sa.Integer(),
                  sa.ForeignKey("learning_item.item_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(15), nullable=False, server_default="enrolled"),
        sa.Column("completion_percentage", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("student_id", "resource_id", name="uq_progress_student_resource"),
        sa.CheckConstraint("completion_percentage BETWEEN 0 AND 100", name="ck_progress_percentage"),
        sa.CheckConstraint(
            "status IN ('enrolled', 'in-progress', 'completed')", name="ck_progress_status"
        ),
    )
    op.create_index("ix_progress_student_id", "progress", ["student_id"])


def downgrade() -> None:
    op.drop_index("ix_progress_student_id", table_name="progress")
    op.drop_table("progress")
