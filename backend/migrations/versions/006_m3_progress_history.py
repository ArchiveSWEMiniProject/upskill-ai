"""PR-9: persist progress state changes independently of roadmap rows."""

import sqlalchemy as sa
from alembic import op

revision = "006_m3_progress_history"
down_revision = "005_m3_roadmap_refresh_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "progress_event",
        sa.Column("event_id", sa.Integer(), primary_key=True),
        sa.Column("progress_id", sa.Integer(),
                  sa.ForeignKey("progress.progress_id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(15), nullable=False),
        sa.Column("completion_percentage", sa.Integer(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("completion_percentage BETWEEN 0 AND 100", name="ck_event_percentage"),
        sa.CheckConstraint(
            "status IN ('enrolled', 'in-progress', 'completed')", name="ck_event_status"
        ),
    )
    op.create_index("ix_progress_event_progress_id", "progress_event", ["progress_id"])


def downgrade() -> None:
    op.drop_index("ix_progress_event_progress_id", table_name="progress_event")
    op.drop_table("progress_event")
