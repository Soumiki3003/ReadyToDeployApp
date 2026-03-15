from pydantic import BaseModel, Field

from app.schemas.common import Paginated


class CreateCourse(BaseModel):
    name: str = Field(min_length=2, description="Course name")
    description: str | None = Field(default=None, description="Course description")
    instructor_ids: list[str] = Field(
        default_factory=list, description="IDs of instructors to assign"
    )
    student_ids: list[str] = Field(
        default_factory=list, description="IDs of students to enroll"
    )


class UpdateCourseMembers(BaseModel):
    instructor_ids: list[str] = Field(
        default_factory=list, description="IDs of instructors to assign"
    )
    student_ids: list[str] = Field(
        default_factory=list, description="IDs of students to enroll"
    )


class CourseMember(BaseModel):
    id: str
    name: str
    email: str
    role: str


class PaginatedCourses(Paginated):
    user_id: str | None = None
    user_role: str | None = None


class CreateManualHint(BaseModel):
    student_id: str = Field(description="ID of the student to receive the hint, or 'all'")
    hint_text: str = Field(description="The hint content")
