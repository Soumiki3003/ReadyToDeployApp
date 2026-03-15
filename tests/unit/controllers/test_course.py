import pytest
from pathlib import Path
from unittest.mock import MagicMock
from app.controllers.course import CourseController
from app.schemas import course as schemas_course


@pytest.fixture
def course_controller(mock_knowledge_service, mock_user_service, mock_chat_service, mock_supervisor_agent_service):
    return CourseController(
        knowledge_service=mock_knowledge_service,
        user_service=mock_user_service,
        chat_service=mock_chat_service,
        supervisor_agent_service=mock_supervisor_agent_service,
        uploads_folder=Path("/tmp"),
        uploads_service=MagicMock(),
    )


def test_get_courses(course_controller, mock_knowledge_service):
    params = schemas_course.PaginatedCourses(page=1, page_size=10, user_id="u1", user_role="student")
    mock_knowledge_service.get_root_nodes.side_effect = lambda **kwargs: ["n1"] * 11

    courses, has_next = course_controller.get_courses(params)
    assert len(courses) == 10
    assert has_next is True


def test_create_course(course_controller, mock_knowledge_service):
    params = schemas_course.CreateCourse(name="Math", description="Basic Math", instructor_ids=["i1"], student_ids=["s1"])
    mock_knowledge_service.create_empty_course.side_effect = lambda *a, **kw: "c1"

    c_id = course_controller.create_course(params, creator_id="i2")
    assert c_id == "c1"


def test_upload_to_course(course_controller, mock_knowledge_service):
    mock_knowledge_service.add_document_to_course.side_effect = lambda *a: None
    mock_file = MagicMock()
    mock_file.filename = "lecture.pdf"
    processed = course_controller.upload_to_course("c1", [mock_file])
    assert processed == 1
    mock_file.save.assert_called_once()
    saved_path = mock_file.save.call_args[0][0]
    assert ".." not in str(saved_path)
    assert str(saved_path).endswith("lecture.pdf")
    mock_knowledge_service.add_document_to_course.assert_called_once()


def test_upload_to_course_multiple_files(course_controller, mock_knowledge_service):
    """Returns the count of files actually saved."""
    mock_knowledge_service.add_document_to_course.side_effect = lambda *a: None
    files = [MagicMock(filename=f"file{i}.pdf") for i in range(3)]
    processed = course_controller.upload_to_course("c1", files)
    assert processed == 3
    assert mock_knowledge_service.add_document_to_course.call_count == 3


def test_upload_to_course_path_traversal_rejected(course_controller, mock_knowledge_service):
    """A filename with path-traversal sequences must never be written outside the uploads folder."""
    mock_knowledge_service.add_document_to_course.side_effect = lambda *a: None
    mock_file = MagicMock()
    mock_file.filename = "../../app/controllers/course.py"
    processed = course_controller.upload_to_course("c1", [mock_file])
    assert processed == 1
    saved_path = mock_file.save.call_args[0][0]
    assert ".." not in str(saved_path), "Path traversal sequences must be stripped"
    assert str(saved_path).endswith("course.py")


def test_upload_to_course_dotonly_filename_raises(course_controller, mock_knowledge_service):
    """A filename that reduces to nothing after sanitization raises ValueError."""
    mock_file = MagicMock()
    mock_file.filename = ".."
    with pytest.raises(ValueError, match="No valid files"):
        course_controller.upload_to_course("c1", [mock_file])
    mock_file.save.assert_not_called()
    mock_knowledge_service.add_document_to_course.assert_not_called()


def test_upload_to_course_empty_list_raises(course_controller, mock_knowledge_service):
    """An empty file list raises ValueError."""
    with pytest.raises(ValueError, match="No valid files"):
        course_controller.upload_to_course("c1", [])


def test_get_uploads(course_controller):
    course_controller._CourseController__uploads_service.get_many.return_value = ["upload1"]
    res = course_controller.get_uploads(1, 10)
    assert res == ["upload1"]
    course_controller._CourseController__uploads_service.get_many.assert_called_with(limit=10, offset=0)


def test_get_course(course_controller, mock_knowledge_service):
    mock_knowledge_service.get_knowledge.side_effect = lambda course_id: MagicMock(id=course_id)
    course_controller.get_course("c1")
    mock_knowledge_service.get_knowledge.assert_called_once_with("c1")


def test_get_course_members(course_controller, mock_knowledge_service):
    mock_knowledge_service.get_course_members.side_effect = lambda course_id: {"instructors": []}
    res = course_controller.get_course_members("c1")
    assert "instructors" in res


def test_update_course_members(course_controller, mock_knowledge_service):
    params = schemas_course.UpdateCourseMembers(instructor_ids=["i1"], student_ids=["s1"])
    mock_knowledge_service.set_course_instructors.side_effect = lambda *a: None
    mock_knowledge_service.set_course_students.side_effect = lambda *a: None

    course_controller.update_course_members("c1", params)
    mock_knowledge_service.set_course_instructors.assert_called_with("c1", ["i1"])
    mock_knowledge_service.set_course_students.assert_called_with("c1", ["s1"])


def test_chat_send(course_controller, mock_chat_service, mock_supervisor_agent_service):
    from app.services.supervisor_agent import SupervisorResult
    from app.models.chat import ChatMessage, ChatMessageRole

    mock_chat_service.get_messages.side_effect = lambda *a: []
    mock_chat_service.to_llm_messages.side_effect = lambda msgs: []
    mock_chat_service.add_message.side_effect = lambda user_id, course_id, msg: msg

    mock_result = SupervisorResult(answer="Hello", hint_text="Hint")
    mock_supervisor_agent_service.retrieve_context.side_effect = lambda *a, **kw: mock_result

    res = course_controller.chat_send("u1", "c1", "Hi")
    assert res.answer == "Hello"
    assert res.hint_text == "Hint"


def test_get_users_by_role(course_controller, mock_user_service):
    user_mock = MagicMock()
    user_mock.id = "u1"
    user_mock.name = "Test"
    user_mock.email = "e"
    role_mock = MagicMock()
    role_mock.value = "student"
    user_mock.role = role_mock

    mock_user_service.get_users_by_role.side_effect = lambda role: [user_mock]
    res = course_controller.get_users_by_role("student")
    assert res[0].id == "u1"


def test_clear_course(course_controller, mock_knowledge_service):
    mock_knowledge_service.clear_course.side_effect = lambda course_id: None
    course_controller.clear_course("c1")
    mock_knowledge_service.clear_course.assert_called_once()


def test_delete_course(course_controller, mock_knowledge_service):
    mock_knowledge_service.delete_course.side_effect = lambda course_id: None
    course_controller.delete_course("c1")
    mock_knowledge_service.delete_course.assert_called_once()


def test_create_manual_hint(course_controller, mock_user_service, user_trajectory):
    params = MagicMock()
    params.student_id = "s1"
    params.hint_text = "Watch out!"
    mock_user_service.add_trajectory_entry.side_effect = lambda *a: user_trajectory

    course_controller.create_manual_hint("c1", params)
    mock_user_service.add_trajectory_entry.assert_called_once()


def test_create_manual_hint_all(course_controller, mock_knowledge_service, mock_user_service, user_trajectory):
    params = MagicMock()
    params.student_id = "all"
    params.hint_text = "Watch out!"
    student_mock = MagicMock()
    student_mock.id = "s1"
    mock_knowledge_service.get_course_members.side_effect = lambda course_id: {"students": [student_mock]}
    mock_user_service.add_trajectory_entry.side_effect = lambda *a: user_trajectory

    course_controller.create_manual_hint("c1", params)
    mock_user_service.add_trajectory_entry.assert_called_once()
