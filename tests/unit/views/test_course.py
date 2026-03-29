import pytest
from unittest.mock import MagicMock

from tests.unit.views.conftest import (
    _mock_dashboard_service,
    _mock_course_controller,
    _mock_knowledge_controller,
    _login_as,
    _reset_mocks,
)


@pytest.fixture(autouse=True)
def reset_mocks():
    _reset_mocks()
    yield
    _reset_mocks()


def _make_member(uid, name):
    m = MagicMock()
    m.configure_mock(id=uid, name=name)
    return m


class TestDashboardProgressPage:
    def test_instructor_can_access(self, app, client, instructor_user):
        _login_as(app, client, instructor_user)
        _mock_course_controller.get_course.return_value = MagicMock(name="Test Course")

        resp = client.get("/course/course-1/progress")
        assert resp.status_code == 200
        assert b"Student Progress" in resp.data

    def test_student_cannot_access(self, app, client, student_user):
        _login_as(app, client, student_user)
        resp = client.get("/course/course-1/progress")
        assert resp.status_code == 403

    def test_unauthenticated_redirected(self, app, client):
        resp = client.get("/course/course-1/progress")
        assert resp.status_code == 302


class TestApiNodeStruggle:
    def test_returns_enriched_json(self, app, client, instructor_user):
        _login_as(app, client, instructor_user)

        _mock_dashboard_service.calculate_node_struggle.return_value = [
            {"node_id": "n1", "struggle": 5.0},
            {"node_id": "n2", "struggle": 2.5},
        ]

        knowledge_obj = MagicMock()
        node1 = MagicMock()
        node1.configure_mock(id="n1", label="Phishing")
        node2 = MagicMock()
        node2.configure_mock(id="n2", label="Malware")
        knowledge_obj.nodes = [node1, node2]
        _mock_knowledge_controller.get_knowledge.return_value = knowledge_obj

        resp = client.get("/course/course-1/api/node-struggle")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 2
        assert data[0]["node_name"] == "Phishing"
        assert data[0]["struggle"] == 5.0
        assert data[1]["node_name"] == "Malware"
        assert data[1]["struggle"] == 2.5

    def test_empty_course_returns_empty_list(self, app, client, instructor_user):
        _login_as(app, client, instructor_user)
        _mock_dashboard_service.calculate_node_struggle.return_value = []
        _mock_knowledge_controller.get_knowledge.return_value = None

        resp = client.get("/course/course-1/api/node-struggle")
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_student_cannot_access(self, app, client, student_user):
        _login_as(app, client, student_user)
        resp = client.get("/course/course-1/api/node-struggle")
        assert resp.status_code == 403


class TestApiStudentStruggle:
    def test_returns_enriched_json(self, app, client, instructor_user):
        _login_as(app, client, instructor_user)

        _mock_dashboard_service.calculate_student_struggle.return_value = [
            {"student_id": "s1", "struggle": 10.0},
            {"student_id": "s2", "struggle": 6.5},
        ]

        _mock_course_controller.get_course_members.return_value = {
            "instructors": [],
            "students": [_make_member("s1", "Alice"), _make_member("s2", "Bob")],
        }

        resp = client.get("/course/course-1/api/student-struggle")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 2
        assert data[0]["student_name"] == "Alice"
        assert data[0]["struggle"] == 10.0
        assert data[1]["student_name"] == "Bob"
        assert data[1]["struggle"] == 6.5

    def test_empty_course_returns_empty_list(self, app, client, instructor_user):
        _login_as(app, client, instructor_user)
        _mock_dashboard_service.calculate_student_struggle.return_value = []
        _mock_course_controller.get_course_members.return_value = {
            "instructors": [],
            "students": [],
        }

        resp = client.get("/course/course-1/api/student-struggle")
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_student_cannot_access(self, app, client, student_user):
        _login_as(app, client, student_user)
        resp = client.get("/course/course-1/api/student-struggle")
        assert resp.status_code == 403


class TestApiNodeStruggleDetail:
    def test_returns_html_partial(self, app, client, instructor_user):
        _login_as(app, client, instructor_user)

        traj1 = MagicMock()
        traj1.retrieved_nodes = ["n1"]
        traj1.user_id = "s1"
        _mock_dashboard_service._fetch_trajectories.return_value = [traj1]
        _mock_dashboard_service._struggle.return_value = 5.0

        _mock_course_controller.get_course_members.return_value = {
            "instructors": [],
            "students": [_make_member("s1", "Alice")],
        }

        resp = client.get("/course/course-1/api/struggle-detail/node/n1")
        assert resp.status_code == 200
        assert b"Alice" in resp.data
        assert b"View Chat" in resp.data

    def test_no_students_returns_empty_message(self, app, client, instructor_user):
        _login_as(app, client, instructor_user)
        _mock_dashboard_service._fetch_trajectories.return_value = []
        _mock_course_controller.get_course_members.return_value = {
            "instructors": [],
            "students": [],
        }

        resp = client.get("/course/course-1/api/struggle-detail/node/n1")
        assert resp.status_code == 200
        assert b"No student data found" in resp.data

    def test_student_cannot_access(self, app, client, student_user):
        _login_as(app, client, student_user)
        resp = client.get("/course/course-1/api/struggle-detail/node/n1")
        assert resp.status_code == 403


class TestApiStudentStruggleDetail:
    def test_returns_html_partial(self, app, client, instructor_user):
        _login_as(app, client, instructor_user)

        traj1 = MagicMock()
        traj1.user_id = "s1"
        traj1.retrieved_nodes = ["n1"]
        _mock_dashboard_service._fetch_trajectories.return_value = [traj1]
        _mock_dashboard_service._struggle.return_value = 5.0

        knowledge_obj = MagicMock()
        node = MagicMock()
        node.configure_mock(id="n1", label="SQL Injection")
        knowledge_obj.nodes = [node]
        _mock_knowledge_controller.get_knowledge.return_value = knowledge_obj

        _mock_course_controller.get_course_members.return_value = {
            "instructors": [],
            "students": [_make_member("s1", "Alice")],
        }

        resp = client.get("/course/course-1/api/struggle-detail/student/s1")
        assert resp.status_code == 200
        assert b"SQL Injection" in resp.data
        assert b"Alice" in resp.data

    def test_no_data_returns_empty_message(self, app, client, instructor_user):
        _login_as(app, client, instructor_user)
        _mock_dashboard_service._fetch_trajectories.return_value = []
        _mock_knowledge_controller.get_knowledge.return_value = None

        _mock_course_controller.get_course_members.return_value = {
            "instructors": [],
            "students": [_make_member("s1", "Alice")],
        }

        resp = client.get("/course/course-1/api/struggle-detail/student/s1")
        assert resp.status_code == 200
        assert b"No topic data found" in resp.data

    def test_student_cannot_access(self, app, client, student_user):
        _login_as(app, client, student_user)
        resp = client.get("/course/course-1/api/struggle-detail/student/s1")
        assert resp.status_code == 403


class TestDashboardNavigation:
    def test_dashboard_has_progress_link_for_instructor(self, app, client, instructor_user):
        _login_as(app, client, instructor_user)

        course_mock = MagicMock()
        course_mock.configure_mock(id="c1", name="Course 1", description=None, sources=[])
        _mock_course_controller.get_courses.return_value = ([course_mock], False)
        _mock_course_controller.get_users_by_role.return_value = []

        resp = client.get("/")
        assert resp.status_code == 200
        assert b"dashboard_progress" in resp.data or b"Progress" in resp.data
