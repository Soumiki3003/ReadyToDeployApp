import pytest
from app.services.user import UserService
from app.schemas.user import CreateUser, UpdateUser
from app.models.user import UserRole, HintApprovalStatus, UserTrajectory

@pytest.fixture
def user_service(mock_neo4j_session_factory, mock_embedder, mock_graphrag, mock_auth_service):
    factory, session, tx = mock_neo4j_session_factory
    return UserService(
        session_factory=factory,
        embedder=mock_embedder,
        rag=mock_graphrag,
        auth_service=mock_auth_service,
        trajectory_vector_index_field="vector_idx",
        trajectory_full_text_index_field="text_idx"
    )

def test_create_user(user_service, mock_auth_service, mock_neo4j_session_factory, user):
    factory, session, tx = mock_neo4j_session_factory
    user_data = user.model_dump(by_alias=True)
    
    # execute_read get_user_by_email -> None
    # execute_write creation -> user_data
    tx.run.return_value.single.side_effect = [None, {"u": user_data}]
    
    schemas_user = CreateUser(
        name="Test",
        email="test@test.com",
        password="password123",
        role=UserRole.STUDENT,
        enabled=True
    )
    
    created_user = user_service.create_user(schemas_user)
    assert created_user.email == user.email
    mock_auth_service.hash_password.assert_called_once()

def test_create_user_already_exists(user_service, mock_neo4j_session_factory, user):
    factory, session, tx = mock_neo4j_session_factory
    user_data = user.model_dump(by_alias=True)
    tx.run.return_value.single.side_effect = [{"u": user_data}]

    schemas_user = CreateUser(
        name="Test",
        email="test@test.com",
        password="password123",
        role=UserRole.STUDENT,
        enabled=True
    )
    with pytest.raises(ValueError, match="already exists"):
        user_service.create_user(schemas_user)

def test_get_user(user_service, mock_neo4j_session_factory, user):
    factory, session, tx = mock_neo4j_session_factory
    user_data = user.model_dump(by_alias=True)
    
    tx.run.return_value.single.return_value = {"u": user_data}
    fetched = user_service.get_user("some_id")
    assert fetched.email == user.email

def test_authenticate(user_service, mock_neo4j_session_factory, mock_auth_service, user):
    factory, session, tx = mock_neo4j_session_factory
    user_data = user.model_dump(by_alias=True)
    
    tx.run.return_value.single.return_value = {"u": user_data}
    mock_auth_service.verify_password.side_effect = lambda *a: True

    authenticated = user_service.authenticate("test@test.com", "password")
    assert authenticated.email == user.email
    mock_auth_service.verify_password.assert_called_once()
    
def test_authenticate_fails(user_service, mock_neo4j_session_factory, mock_auth_service, user):
    factory, session, tx = mock_neo4j_session_factory
    user_data = user.model_dump(by_alias=True)
    
    tx.run.return_value.single.return_value = {"u": user_data}
    mock_auth_service.verify_password.side_effect = lambda *a: False

    assert user_service.authenticate("test@test.com", "wrong") is None

def test_get_user_trajectory(user_service, mock_neo4j_session_factory, user_trajectory):
    factory, session, tx = mock_neo4j_session_factory
    traj_data = user_trajectory.model_dump(by_alias=True)
    
    tx.run.return_value.__iter__.return_value = [{"t": traj_data, "user_id": "u1"}]
    
    trajectories = user_service.get_user_trajectory(user_id="u1", limit=10)
    assert len(trajectories) == 1
    assert trajectories[0].query == user_trajectory.query

def test_add_trajectory(user_service, mock_neo4j_session_factory, user_trajectory, mock_embedder):
    factory, session, tx = mock_neo4j_session_factory
    traj_data = user_trajectory.model_dump(by_alias=True)
    
    tx.run.return_value.single.return_value = {"t": traj_data, "user_id": "test_id"}
    
    added = user_service.add_trajectory_entry("test_id", user_trajectory)
    assert added is not None
    mock_embedder.embed_documents_sync.assert_called_once()

def test_get_users_by_role(user_service, mock_neo4j_session_factory, user):
    factory, session, tx = mock_neo4j_session_factory
    user_data = user.model_dump(by_alias=True)
    
    tx.run.return_value.__iter__.return_value = [{"u": user_data}]
    users = user_service.get_users_by_role("student")
    assert len(users) == 1
    assert users[0].role == user.role
