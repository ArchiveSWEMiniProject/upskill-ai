"""PR-6: retain a pending roadmap refresh until M2 accepts it."""

import sqlalchemy as sa
from alembic import op

revision = "005_m3_roadmap_refresh_state"
down_revision = "004_m3_evidence_vector_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("completion_evidence", sa.Column(
        "roadmap_refresh_pending", sa.Boolean(), nullable=False, server_default=sa.false()
    ))


def downgrade() -> None:
    op.drop_column("completion_evidence", "roadmap_refresh_pending")
