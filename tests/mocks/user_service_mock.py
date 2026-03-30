import pytest
from app.services.user import UserService


@pytest.fixture
def mock_user_service(mocker, mock_neo4j_session_factory, mock_embedder, mock_graphrag, mock_auth_service):
    factory, _, _ = mock_neo4j_session_factory
    instance = UserService(
        session_factory=factory,
        embedder=mock_embedder,
        rag=mock_graphrag,
        auth_service=mock_auth_service,
        trajectory_vector_index_field="vector_idx",
        trajectory_full_text_index_field="text_idx",
    )
    mock = mocker.MagicMock(spec=UserService)
    mock.create_user = mocker.MagicMock(side_effect=instance.create_user)
    mock.get_user = mocker.MagicMock(side_effect=instance.get_user)
    mock.get_user_by_email = mocker.MagicMock(side_effect=instance.get_user_by_email)
    mock.authenticate = mocker.MagicMock(side_effect=instance.authenticate)
    mock.update_user = mocker.MagicMock(side_effect=instance.update_user)
    mock.get_users_by_role = mocker.MagicMock(side_effect=instance.get_users_by_role)
    mock.get_user_trajectory = mocker.MagicMock(side_effect=instance.get_user_trajectory)
    mock.add_trajectory_entry = mocker.MagicMock(side_effect=instance.add_trajectory_entry)
    mock.get_user_trajectory_by_query_exact_match = mocker.MagicMock(
        side_effect=instance.get_user_trajectory_by_query_exact_match
    )
    mock.get_user_trajectory_by_query_similarity = mocker.MagicMock(
        side_effect=instance.get_user_trajectory_by_query_similarity
    )
    mock.increment_trajectory_query_repeat_count = mocker.MagicMock(
        side_effect=instance.increment_trajectory_query_repeat_count
    )
    mock.get_pending_hints = mocker.MagicMock(side_effect=instance.get_pending_hints)
    mock.update_hint_approval = mocker.MagicMock(side_effect=instance.update_hint_approval)
    return mock
