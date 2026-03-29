import pytest
from unittest.mock import MagicMock
from pathlib import Path

from flask import Flask
from flask_login import LoginManager
from dependency_injector import providers

from app.models.user import User, UserRole
from app.containers import Application
from app.views import auth, course, knowledge


# Pre-build mock dependencies
_mock_dashboard_service = MagicMock()
_mock_course_controller = MagicMock()
_mock_knowledge_controller = MagicMock()


def _create_mock_container():
    """Create a mock Application container that returns our mocks."""
    container = Application()
    # Override providers with Object returning our mocks
    container.services.dashboard.override(providers.Object(_mock_dashboard_service))
    container.controllers.course_controller.override(
        providers.Object(_mock_course_controller)
    )
    container.controllers.knowledge_controller.override(
        providers.Object(_mock_knowledge_controller)
    )
    # Mock resources that need real infra
    container.core.logging.override(providers.Object(None))
    container.core.static_folder.override(providers.Object(Path("/tmp/static")))
    container.core.uploads_folder.override(providers.Object(Path("/tmp/uploads")))
    container.gateways.neo4j_driver.override(providers.Object(MagicMock()))
    container.gateways.neo4j_session.override(providers.Factory(lambda: MagicMock()))
    container.gateways.neo4j_agent.override(providers.Object(MagicMock()))
    container.gateways.neo4j_embedder.override(providers.Object(MagicMock()))
    container.gateways.trajectory_graphrag.override(providers.Object(MagicMock()))
    container.ai.prompt_template_env.override(providers.Object(MagicMock()))
    container.ai.default_agent.override(providers.Object(MagicMock()))
    container.ai.default_embedder.override(providers.Object(MagicMock()))
    container.ai.knowledge_file_agent.override(providers.Object(MagicMock()))
    container.ai.graph_agent.override(providers.Object(MagicMock()))
    return container


def _make_test_app():
    flask_app = Flask(
        __name__,
        template_folder=Path(__file__).parents[3] / "app" / "templates" / "web",
    )
    flask_app.config["TESTING"] = True
    flask_app.config["SECRET_KEY"] = "test-secret-key"

    # Create and wire mock container
    container = _create_mock_container()
    container.wire(
        modules=[
            "app.views.knowledge",
            "app.views.auth",
            "app.views.course",
        ]
    )
    flask_app.container = container

    lm = LoginManager()
    lm.login_view = "auth.login_page"
    lm.init_app(flask_app)

    flask_app._test_user = None

    @lm.user_loader
    def load_user(user_id):
        if flask_app._test_user and flask_app._test_user.get_id() == user_id:
            return flask_app._test_user
        return None

    flask_app.register_blueprint(knowledge.app, url_prefix="/knowledge")
    flask_app.register_blueprint(auth.app, url_prefix="/auth")
    flask_app.register_blueprint(course.app, url_prefix="/")

    return flask_app


@pytest.fixture
def app():
    return _make_test_app()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def instructor_user():
    return User(
        id="instructor-1",
        name="Test Instructor",
        email="instructor@test.com",
        password="hashedpassword123",
        role=UserRole.INSTRUCTOR,
    )


@pytest.fixture
def student_user():
    return User(
        id="student-1",
        name="Test Student",
        email="student@test.com",
        password="hashedpassword123",
        role=UserRole.STUDENT,
    )


def _login_as(app, client, user):
    app._test_user = user
    with client.session_transaction() as sess:
        sess["_user_id"] = user.get_id()


def _reset_mocks():
    """Reset all shared mock objects between tests."""
    _mock_dashboard_service.reset_mock()
    _mock_course_controller.reset_mock()
    _mock_knowledge_controller.reset_mock()
