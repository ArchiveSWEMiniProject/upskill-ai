"""Shared fixtures for auth and catalogue test suites."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.auth.models import MentorAssignment, UserAccount, UserRole
from backend.auth.security import create_access_token, hash_password
from backend.catalogue.models import Skill, SkillAlias
from backend.database import Base, get_db
from backend.main import app

# In-memory SQLite for fast, completely isolated tests
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database schema and session for each test function."""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()

    # Seed canonical skills for tests
    docker_skill = Skill(skill_id=1, skill_name="Docker", category="DevOps")
    python_skill = Skill(skill_id=2, skill_name="Python", category="Backend")
    postgres_skill = Skill(skill_id=3, skill_name="PostgreSQL", category="Database")
    go_skill = Skill(skill_id=4, skill_name="Go", category="Backend")
    session.add_all([docker_skill, python_skill, postgres_skill, go_skill])
    session.flush()

    # Seed alias
    alias = SkillAlias(skill_id=docker_skill.skill_id, alias_text="docker containers")
    session.add(alias)
    session.flush()

    # Seed standard test users
    admin_user = UserAccount(
        user_id=1,
        email="admin@pes.edu",
        password_hash=hash_password("AdminPass#2026"),
        role=UserRole.ADMINISTRATOR,
        is_active=True,
    )
    faculty_user = UserAccount(
        user_id=2,
        email="faculty@pes.edu",
        password_hash=hash_password("FacultyPass#2026"),
        role=UserRole.FACULTY_MENTOR,
        is_active=True,
    )
    student1_user = UserAccount(
        user_id=3,
        email="s1@pes.edu",
        password_hash=hash_password("StudentPass#2026"),
        role=UserRole.STUDENT,
        is_active=True,
    )
    student2_user = UserAccount(
        user_id=4,
        email="s2@pes.edu",
        password_hash=hash_password("StudentPass#2026"),
        role=UserRole.STUDENT,
        is_active=True,
    )
    session.add_all([admin_user, faculty_user, student1_user, student2_user])
    session.flush()

    # Student records seeded via SQL text
    session.execute(
        text(
            "INSERT INTO student (student_id, user_id, name) VALUES "
            "(101, :uid1, 'Student One'), (102, :uid2, 'Student Two')"
        ),
        {"uid1": student1_user.user_id, "uid2": student2_user.user_id},
    )
    session.flush()

    # Mentor assignment: faculty (user_id=2) mentors student 1 (student_id=101)
    assignment = MentorAssignment(
        mentor_id=faculty_user.user_id,
        student_id=101,
    )
    session.add(assignment)
    session.commit()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI TestClient with overridden get_db dependency."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_token():
    return create_access_token(
        {"sub": "1", "user_id": 1, "email": "admin@pes.edu", "role": "administrator"}
    )


@pytest.fixture
def faculty_token():
    return create_access_token(
        {"sub": "2", "user_id": 2, "email": "faculty@pes.edu", "role": "faculty_mentor"}
    )


@pytest.fixture
def student1_token():
    return create_access_token({"sub": "3", "user_id": 3, "email": "s1@pes.edu", "role": "student"})


@pytest.fixture
def student2_token():
    return create_access_token({"sub": "4", "user_id": 4, "email": "s2@pes.edu", "role": "student"})
