import pytest
from app.controllers.auth import AuthController
from app.schemas.auth import LoginRequest
from app.schemas.user import CreateUser
from app.models.user import UserRole


@pytest.fixture
def auth_controller(mock_user_service, mock_auth_service):
    return AuthController(user_service=mock_user_service, auth_service=mock_auth_service)


def test_login_success(auth_controller, mock_user_service, user):
    mock_user_service.authenticate.side_effect = lambda email, password: user

    result = auth_controller.login(LoginRequest(email="test@test.com", password="password123"))

    assert result is user
    mock_user_service.authenticate.assert_called_once_with("test@test.com", "password123")


def test_login_failure(auth_controller, mock_user_service):
    mock_user_service.authenticate.side_effect = lambda email, password: None

    result = auth_controller.login(LoginRequest(email="bad@test.com", password="wrong"))

    assert result is None
    mock_user_service.authenticate.assert_called_once()


def test_register(auth_controller, mock_user_service, user):
    mock_user_service.create_user.side_effect = lambda params: user

    params = CreateUser(
        name="New User",
        email="new@test.com",
        password="securepass",
        role=UserRole.STUDENT,
        enabled=True,
    )
    result = auth_controller.register(params)

    assert result is user
    mock_user_service.create_user.assert_called_once_with(params)


def test_register_duplicate_email(auth_controller, mock_user_service):
    mock_user_service.create_user.side_effect = ValueError("already exists")

    params = CreateUser(
        name="Dup User",
        email="dup@test.com",
        password="duplicate123",
        role=UserRole.STUDENT,
        enabled=True,
    )
    with pytest.raises(ValueError, match="already exists"):
        auth_controller.register(params)
