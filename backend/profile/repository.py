from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.profile.exceptions import ProfileAlreadyExistsError
from backend.profile.models import ProfileItem, Student


class StudentRepository:
    def __init__(self, session: Session):
        self._session = session

    def get_by_user_id(self, user_id: int) -> Student | None:
        return self._session.scalars(select(Student).where(Student.user_id == user_id)).first()

    def add(self, student: Student) -> Student:
        """Insert and flush. The unique constraint on user_id is the final guard
        against two concurrent creates for the same account. The insert runs in a
        savepoint, so a failure undoes only this insert, not the caller's other
        work in the same transaction."""
        try:
            with self._session.begin_nested():
                self._session.add(student)
        except IntegrityError as error:
            if "uq_student_user_id" in str(error.orig):
                raise ProfileAlreadyExistsError from error
            raise
        return student


class ProfileItemRepository:
    """Course and project entries, always scoped to one student: an entry that
    belongs to someone else is indistinguishable from one that does not exist."""

    def __init__(self, session: Session):
        self._session = session

    def list(self, student_id: int, item_type: str) -> list[ProfileItem]:
        return list(
            self._session.scalars(
                select(ProfileItem)
                .where(ProfileItem.student_id == student_id, ProfileItem.item_type == item_type)
                .order_by(ProfileItem.profile_item_id)
            )
        )

    def get(self, student_id: int, item_type: str, item_id: int) -> ProfileItem | None:
        return self._session.scalars(
            select(ProfileItem).where(
                ProfileItem.profile_item_id == item_id,
                ProfileItem.student_id == student_id,
                ProfileItem.item_type == item_type,
            )
        ).first()

    def add(self, item: ProfileItem) -> ProfileItem:
        self._session.add(item)
        self._session.flush()
        return item

    def delete(self, item: ProfileItem) -> None:
        self._session.delete(item)
        self._session.flush()
