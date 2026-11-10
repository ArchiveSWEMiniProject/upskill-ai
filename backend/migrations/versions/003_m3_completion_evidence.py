"""PR-4: store validated completion evidence.

Revision ID: 003_m3_completion_evidence
Revises: 002_m3_progress
"""

import sqlalchemy as sa
from alembic import op

revision = "003_m3_completion_evidence"
down_revision = "002_m3_progress"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "completion_evidence",
        sa.Column("evidence_id", sa.Integer(), primary_key=True),
        sa.Column("progress_id", sa.Integer(),
                  sa.ForeignKey("progress.progress_id", ondelete="CASCADE"), nullable=False),
        sa.Column("evidence_type", sa.String(20), nullable=False),
        sa.Column("evidence_url", sa.String(255)),
        sa.Column("score", sa.Integer()),
        sa.Column("submitted_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("progress_id"),
        sa.CheckConstraint(
            "(evidence_type = 'quiz' AND score IS NOT NULL AND score BETWEEN 0 AND 100 "
            "AND evidence_url IS NULL) OR "
            "(evidence_type = 'certificate' AND evidence_url IS NOT NULL AND score IS NULL)",
            name="ck_completion_evidence_payload",
        ),
    )


def downgrade() -> None:
    op.drop_table("completion_evidence")
