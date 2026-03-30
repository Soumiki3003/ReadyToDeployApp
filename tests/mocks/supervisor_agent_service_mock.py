import pytest
from app.services.supervisor_agent import SupervisorAgentService


@pytest.fixture
def mock_supervisor_agent_service(mocker, mock_user_service, mock_graphrag):
    instance = SupervisorAgentService(
        user_service=mock_user_service,
        graph_rag=mock_graphrag,
        hint_agent=mocker.MagicMock(),
    )
    mock = mocker.MagicMock(spec=SupervisorAgentService)
    mock.retrieve_context = mocker.MagicMock(side_effect=instance.retrieve_context)
    return mock
