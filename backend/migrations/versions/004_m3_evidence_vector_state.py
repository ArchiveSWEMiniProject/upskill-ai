"""PR-5: track whether M1 has processed completion evidence."""

import sqlalchemy as sa
from alembic import op

revision = "004_m3_evidence_vector_state"
down_revision = "003_m3_completion_evidence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("completion_evidence", sa.Column("vector_applied_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("completion_evidence", "vector_applied_at")
