"""Initial schema with all M1 and M4 shared tables

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-10-04 14:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Enums with create_type=False for column definitions
user_role_enum = postgresql.ENUM(
    "student", "faculty_mentor", "administrator", name="user_role", create_type=False
)
skill_level_enum = postgresql.ENUM(
    "beginner", "intermediate", "advanced", name="skill_level", create_type=False
)
skill_source_enum = postgresql.ENUM(
    "manual", "course", "resume", "completion", name="skill_source", create_type=False
)
learning_item_type_enum = postgresql.ENUM(
    "course", "certification", "project_idea", name="learning_item_type", create_type=False
)
moderation_state_enum = postgresql.ENUM(
    "pending", "approved", "inactive", name="moderation_state", create_type=False
)
profile_item_type_enum = postgresql.ENUM(
    "course", "project", name="profile_item_type", create_type=False
)
resume_file_type_enum = postgresql.ENUM(
    "pdf", "docx", name="resume_file_type", create_type=False
)
resume_status_enum = postgresql.ENUM(
    "uploaded", "processing", "extracted", "unreadable", "failed", name="resume_status", create_type=False
)
candidate_status_enum = postgresql.ENUM(
    "pending", "confirmed", "rejected", name="candidate_status", create_type=False
)
unresolved_status_enum = postgresql.ENUM(
    "open", "mapped", name="unresolved_status", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()

    # 1. Create Enums explicitly in PostgreSQL
    postgresql.ENUM("student", "faculty_mentor", "administrator", name="user_role").create(bind, checkfirst=True)
    postgresql.ENUM("beginner", "intermediate", "advanced", name="skill_level").create(bind, checkfirst=True)
    postgresql.ENUM("manual", "course", "resume", "completion", name="skill_source").create(bind, checkfirst=True)
    postgresql.ENUM("course", "certification", "project_idea", name="learning_item_type").create(bind, checkfirst=True)
    postgresql.ENUM("pending", "approved", "inactive", name="moderation_state").create(bind, checkfirst=True)
    postgresql.ENUM("course", "project", name="profile_item_type").create(bind, checkfirst=True)
    postgresql.ENUM("pdf", "docx", name="resume_file_type").create(bind, checkfirst=True)
    postgresql.ENUM("uploaded", "processing", "extracted", "unreadable", "failed", name="resume_status").create(bind, checkfirst=True)
    postgresql.ENUM("pending", "confirmed", "rejected", name="candidate_status").create(bind, checkfirst=True)
    postgresql.ENUM("open", "mapped", name="unresolved_status").create(bind, checkfirst=True)

    # 2. Table: user_account (M4)
    op.create_table(
        "user_account",
        sa.Column("user_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", user_role_enum, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("email", name="uq_user_account_email"),
    )
    op.create_index("ix_user_account_email", "user_account", ["email"])

    # 3. Table: career_role (M4)
    op.create_table(
        "career_role",
        sa.Column("role_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("role_name", sa.String(length=60), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.UniqueConstraint("role_name", name="uq_career_role_role_name"),
    )

    # 4. Table: skill (M4)
    op.create_table(
        "skill",
        sa.Column("skill_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("skill_name", sa.String(length=60), nullable=False),
        sa.Column("category", sa.String(length=60), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("skill_name", name="uq_skill_skill_name"),
    )

    # 5. Table: skill_alias (M4)
    op.create_table(
        "skill_alias",
        sa.Column("alias_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("skill_id", sa.Integer(), sa.ForeignKey("skill.skill_id", ondelete="CASCADE"), nullable=False),
        sa.Column("alias_text", sa.String(length=120), nullable=False),
        sa.UniqueConstraint("alias_text", name="uq_skill_alias_alias_text"),
    )
    op.create_index("ix_skill_alias_skill_id", "skill_alias", ["skill_id"])

    # 6. Table: skill_prerequisite (M4)
    op.create_table(
        "skill_prerequisite",
        sa.Column("skill_id", sa.Integer(), sa.ForeignKey("skill.skill_id", ondelete="CASCADE"), nullable=False),
        sa.Column("prerequisite_skill_id", sa.Integer(), sa.ForeignKey("skill.skill_id", ondelete="CASCADE"), nullable=False),
        sa.PrimaryKeyConstraint("skill_id", "prerequisite_skill_id", name="pk_skill_prerequisite"),
    )

    # 7. Table: role_skill_requirement (M4)
    op.create_table(
        "role_skill_requirement",
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("career_role.role_id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill_id", sa.Integer(), sa.ForeignKey("skill.skill_id", ondelete="CASCADE"), nullable=False),
        sa.Column("required_level", skill_level_enum, nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.PrimaryKeyConstraint("role_id", "skill_id", name="pk_role_skill_requirement"),
    )

    # 8. Table: learning_item (M4)
    op.create_table(
        "learning_item",
        sa.Column("item_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(length=150), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False),
        sa.Column("item_type", learning_item_type_enum, nullable=False),
        sa.Column("level", skill_level_enum, nullable=False),
        sa.Column("duration", sa.String(length=30), nullable=True),
        sa.Column("source_url", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=60), nullable=True),
        sa.Column("moderation_state", moderation_state_enum, nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_learning_item_moderation_state", "learning_item", ["moderation_state"])

    # 9. Table: learning_item_skill (M4 join table)
    op.create_table(
        "learning_item_skill",
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("learning_item.item_id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill_id", sa.Integer(), sa.ForeignKey("skill.skill_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("coverage_level", skill_level_enum, nullable=False),
        sa.PrimaryKeyConstraint("item_id", "skill_id", name="pk_learning_item_skill"),
    )
    op.create_index("ix_learning_item_skill_skill_id", "learning_item_skill", ["skill_id"])

    # 10. Table: student (M1)
    op.create_table(
        "student",
        sa.Column("student_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user_account.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("education_level", sa.String(length=30), nullable=True),
        sa.Column("target_role_id", sa.Integer(), sa.ForeignKey("career_role.role_id", ondelete="SET NULL"), nullable=True),
        sa.Column("target_role_set_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", name="uq_student_user_id"),
    )

    # 11. Table: mentor_assignment (M4)
    op.create_table(
        "mentor_assignment",
        sa.Column("assignment_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("mentor_id", sa.Integer(), sa.ForeignKey("user_account.user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("student.student_id", ondelete="CASCADE"), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("student_id", name="uq_mentor_assignment_student_id"),
    )
    op.create_index("ix_mentor_assignment_mentor_id", "mentor_assignment", ["mentor_id"])

    # 12. Table: audit_record (M4)
    op.create_table(
        "audit_record",
        sa.Column("audit_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("user_account.user_id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=False),
        sa.Column("target_id", sa.String(length=100), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_audit_record_actor_id", "audit_record", ["actor_id"])
    op.create_index("ix_audit_record_created_at", "audit_record", ["created_at"])

    # 13. Table: profile_item (M1)
    op.create_table(
        "profile_item",
        sa.Column("profile_item_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("student.student_id", ondelete="CASCADE"), nullable=False),
        sa.Column("item_type", profile_item_type_enum, nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("course_code", sa.String(length=15), nullable=True),
        sa.Column("grade", sa.String(length=3), nullable=True),
        sa.Column("completion_term", sa.String(length=10), nullable=True),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("repository_url", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "(item_type = 'course' AND grade IS NOT NULL AND completion_term IS NOT NULL) OR "
            "(item_type = 'project' AND description IS NOT NULL)",
            name="chk_profile_item_type_fields",
        ),
    )
    op.create_index("ix_profile_item_student_id", "profile_item", ["student_id"])

    # 14. Table: student_skill (M1)
    op.create_table(
        "student_skill",
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("student.student_id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill_id", sa.Integer(), sa.ForeignKey("skill.skill_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source", skill_source_enum, nullable=False),
        sa.Column("level", skill_level_enum, nullable=False),
        sa.Column("confidence", sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("student_id", "skill_id", "source", name="pk_student_skill"),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0.00 AND confidence <= 1.00)",
            name="chk_student_skill_confidence",
        ),
    )

    # 15. Table: skill_change_history (M1)
    op.create_table(
        "skill_change_history",
        sa.Column("history_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("student.student_id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill_id", sa.Integer(), sa.ForeignKey("skill.skill_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("previous_level", skill_level_enum, nullable=True),
        sa.Column("new_level", skill_level_enum, nullable=True),
        sa.Column("source", skill_source_enum, nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_skill_change_history_student_id", "skill_change_history", ["student_id"])
    op.create_index("ix_skill_change_history_skill_id", "skill_change_history", ["skill_id"])

    # 16. Table: resume_upload (M1)
    op.create_table(
        "resume_upload",
        sa.Column("upload_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("student.student_id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_path", sa.String(length=255), nullable=False),
        sa.Column("file_type", resume_file_type_enum, nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("status", resume_status_enum, nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delete_after", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("size_bytes <= 5242880", name="chk_resume_upload_size"),
    )
    op.create_index("ix_resume_upload_student_id", "resume_upload", ["student_id"])

    # 17. Table: extracted_skill_candidate (M1)
    op.create_table(
        "extracted_skill_candidate",
        sa.Column("candidate_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("upload_id", sa.Integer(), sa.ForeignKey("resume_upload.upload_id", ondelete="CASCADE"), nullable=False),
        sa.Column("skill_id", sa.Integer(), sa.ForeignKey("skill.skill_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("suggested_level", skill_level_enum, nullable=False),
        sa.Column("confidence", sa.Numeric(precision=3, scale=2), nullable=False),
        sa.Column("source_sentence", sa.Text(), nullable=False),
        sa.Column("status", candidate_status_enum, nullable=False, server_default="pending"),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("upload_id", "skill_id", name="uq_candidate_upload_skill"),
        sa.CheckConstraint("confidence >= 0.00 AND confidence <= 1.00", name="chk_candidate_confidence"),
    )
    op.create_index("ix_extracted_skill_candidate_upload_id", "extracted_skill_candidate", ["upload_id"])

    # 18. Table: unresolved_skill (M1)
    op.create_table(
        "unresolved_skill",
        sa.Column("unresolved_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("student.student_id", ondelete="CASCADE"), nullable=False),
        sa.Column("upload_id", sa.Integer(), sa.ForeignKey("resume_upload.upload_id", ondelete="SET NULL"), nullable=True),
        sa.Column("raw_text", sa.String(length=120), nullable=False),
        sa.Column("normalised_text", sa.String(length=120), nullable=False),
        sa.Column("status", unresolved_status_enum, nullable=False, server_default="open"),
        sa.Column("mapped_skill_id", sa.Integer(), sa.ForeignKey("skill.skill_id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_unresolved_skill_student_id", "unresolved_skill", ["student_id"])
    op.create_index("ix_unresolved_skill_normalised_text", "unresolved_skill", ["normalised_text"])


def downgrade() -> None:
    # 1. Drop tables in reverse order of creation
    op.drop_table("unresolved_skill")
    op.drop_table("extracted_skill_candidate")
    op.drop_table("resume_upload")
    op.drop_table("skill_change_history")
    op.drop_table("student_skill")
    op.drop_table("profile_item")
    op.drop_table("audit_record")
    op.drop_table("mentor_assignment")
    op.drop_table("student")
    op.drop_table("learning_item_skill")
    op.drop_table("learning_item")
    op.drop_table("role_skill_requirement")
    op.drop_table("skill_prerequisite")
    op.drop_table("skill_alias")
    op.drop_table("skill")
    op.drop_table("career_role")
    op.drop_table("user_account")

    # 2. Drop Enums
    bind = op.get_bind()
    postgresql.ENUM(name="unresolved_status").drop(bind, checkfirst=True)
    postgresql.ENUM(name="candidate_status").drop(bind, checkfirst=True)
    postgresql.ENUM(name="resume_status").drop(bind, checkfirst=True)
    postgresql.ENUM(name="resume_file_type").drop(bind, checkfirst=True)
    postgresql.ENUM(name="profile_item_type").drop(bind, checkfirst=True)
    postgresql.ENUM(name="moderation_state").drop(bind, checkfirst=True)
    postgresql.ENUM(name="learning_item_type").drop(bind, checkfirst=True)
    postgresql.ENUM(name="skill_source").drop(bind, checkfirst=True)
    postgresql.ENUM(name="skill_level").drop(bind, checkfirst=True)
    postgresql.ENUM(name="user_role").drop(bind, checkfirst=True)
