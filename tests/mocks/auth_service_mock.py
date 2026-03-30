import pytest
from app.services.auth import AuthService


@pytest.fixture
def mock_auth_service(mocker):
    instance = AuthService()
    mock = mocker.MagicMock(spec=AuthService)
    mock.hash_password = mocker.MagicMock(side_effect=instance.hash_password)
    mock.verify_password = mocker.MagicMock(side_effect=instance.verify_password)
    return mock
