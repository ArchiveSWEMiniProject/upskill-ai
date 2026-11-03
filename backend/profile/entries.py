"""Course and project entries on a student's profile (UP-3, UP-4).

Both are rows of profile_item and share the same lifecycle: list, add,
replace, delete. Every operation is scoped to the caller's own profile
(REQ-F1-39): another student's entry id behaves exactly like one that does
not exist.
"""

from abc import ABC, abstractmethod

from pydantic import BaseModel

from backend.profile.exceptions import ProfileItemNotFoundError, ProfileNotFoundError
from backend.profile.models import ProfileItem
from backend.profile.repository import ProfileItemRepository, StudentRepository
from backend.profile.schemas import CourseIn, CourseOut, ProjectIn, ProjectOut


class EntryService(ABC):
    item_type: str

    def __init__(self, students: StudentRepository, items: ProfileItemRepository):
        self._students = students
        self._items = items

    @abstractmethod
    def apply(self, item: ProfileItem, body: BaseModel) -> None:
        """Copy the request body onto the row."""

    @abstractmethod
    def to_out(self, item: ProfileItem) -> BaseModel:
        """The response shape for one row."""

    def _student_id(self, user_id: int) -> int:
        student = self._students.get_by_user_id(user_id)
        if student is None:
            raise ProfileNotFoundError
        return student.student_id

    def _own(self, user_id: int, entry_id: int) -> ProfileItem:
        item = self._items.get(self._student_id(user_id), self.item_type, entry_id)
        if item is None:
            raise ProfileItemNotFoundError
        return item

    def list(self, user_id: int) -> list[BaseModel]:
        items = self._items.list(self._student_id(user_id), self.item_type)
        return [self.to_out(item) for item in items]

    def add(self, user_id: int, body: BaseModel) -> BaseModel:
        item = ProfileItem(student_id=self._student_id(user_id), item_type=self.item_type)
        self.apply(item, body)
        return self.to_out(self._items.add(item))

    def replace(self, user_id: int, entry_id: int, body: BaseModel) -> BaseModel:
        item = self._own(user_id, entry_id)
        self.apply(item, body)
        return self.to_out(self._items.add(item))

    def delete(self, user_id: int, entry_id: int) -> None:
        self._items.delete(self._own(user_id, entry_id))


class CourseService(EntryService):
    item_type = "course"

    def apply(self, item: ProfileItem, body: CourseIn) -> None:
        item.title = body.course_name
        item.course_code = body.course_code
        item.grade = body.grade
        item.completion_term = body.completion_term

    def to_out(self, item: ProfileItem) -> CourseOut:
        return CourseOut(
            course_id=item.profile_item_id,
            course_name=item.title,
            course_code=item.course_code,
            grade=item.grade,
            completion_term=item.completion_term,
        )


class ProjectService(EntryService):
    item_type = "project"

    def apply(self, item: ProfileItem, body: ProjectIn) -> None:
        item.title = body.title
        item.description = body.description
        item.repository_url = body.repository_url

    def to_out(self, item: ProfileItem) -> ProjectOut:
        return ProjectOut(
            project_id=item.profile_item_id,
            title=item.title,
            description=item.description,
            repository_url=item.repository_url,
        )
