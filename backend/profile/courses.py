"""Course entries on a student's profile (UP-3, REQ-F1-02).

Every operation is scoped to the caller's own profile (REQ-F1-39): another
student's entry id behaves exactly like one that does not exist.
"""

from backend.profile.exceptions import ProfileItemNotFoundError, ProfileNotFoundError
from backend.profile.models import ProfileItem
from backend.profile.repository import ProfileItemRepository, StudentRepository
from backend.profile.schemas import CourseIn, CourseOut

COURSE = "course"


def to_out(item: ProfileItem) -> CourseOut:
    return CourseOut(
        course_id=item.profile_item_id,
        course_name=item.title,
        course_code=item.course_code,
        grade=item.grade,
        completion_term=item.completion_term,
    )


class CourseService:
    def __init__(self, students: StudentRepository, items: ProfileItemRepository):
        self._students = students
        self._items = items

    def _student_id(self, user_id: int) -> int:
        student = self._students.get_by_user_id(user_id)
        if student is None:
            raise ProfileNotFoundError
        return student.student_id

    def _own(self, user_id: int, course_id: int) -> ProfileItem:
        item = self._items.get(self._student_id(user_id), COURSE, course_id)
        if item is None:
            raise ProfileItemNotFoundError
        return item

    def list_courses(self, user_id: int) -> list[CourseOut]:
        return [to_out(item) for item in self._items.list(self._student_id(user_id), COURSE)]

    def add_course(self, user_id: int, course: CourseIn) -> CourseOut:
        item = ProfileItem(student_id=self._student_id(user_id), item_type=COURSE)
        self._apply(item, course)
        return to_out(self._items.add(item))

    def replace_course(self, user_id: int, course_id: int, course: CourseIn) -> CourseOut:
        item = self._own(user_id, course_id)
        self._apply(item, course)
        return to_out(self._items.add(item))

    def delete_course(self, user_id: int, course_id: int) -> None:
        self._items.delete(self._own(user_id, course_id))

    @staticmethod
    def _apply(item: ProfileItem, course: CourseIn) -> None:
        item.title = course.course_name
        item.course_code = course.course_code
        item.grade = course.grade
        item.completion_term = course.completion_term
