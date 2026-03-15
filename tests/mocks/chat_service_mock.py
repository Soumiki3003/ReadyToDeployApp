import pytest
from app.services.chat import ChatService


@pytest.fixture
def mock_chat_service(mocker, mock_neo4j_session_factory):
    factory, _, _ = mock_neo4j_session_factory
    instance = ChatService(session_factory=factory)
    mock = mocker.MagicMock(spec=ChatService)
    mock.get_messages = mocker.MagicMock(side_effect=instance.get_messages)
    mock.add_message = mocker.MagicMock(side_effect=instance.add_message)
    mock.to_llm_messages = mocker.MagicMock(side_effect=ChatService.to_llm_messages)
    return mock
