import pytest
from app.services.chat import ChatService
from app.models.chat import ChatMessage, ChatMessageRole


@pytest.fixture
def chat_service(mock_neo4j_session_factory):
    factory, _, _ = mock_neo4j_session_factory
    return ChatService(session_factory=factory)


def test_get_messages(chat_service, mock_neo4j_session_factory):
    factory, session, tx = mock_neo4j_session_factory
    msg_data = {
        "id": "m1",
        "role": "user",
        "content": "Hello",
        "timestamp": "2024-01-01T00:00:00Z",
    }
    tx.run.return_value.__iter__.return_value = [{"m": msg_data}]

    messages = chat_service.get_messages("u1", "c1")

    assert len(messages) == 1
    assert messages[0].content == "Hello"
    assert messages[0].role == ChatMessageRole.USER


def test_get_messages_with_limit(chat_service, mock_neo4j_session_factory):
    factory, session, tx = mock_neo4j_session_factory
    msg_data = {
        "id": "m1",
        "role": "assistant",
        "content": "Hi there",
        "timestamp": "2024-01-01T00:00:00Z",
    }
    tx.run.return_value.__iter__.return_value = [{"m": msg_data}]

    messages = chat_service.get_messages("u1", "c1", limit=5)

    assert len(messages) == 1
    assert messages[0].role == ChatMessageRole.ASSISTANT


def test_add_message(chat_service, mock_neo4j_session_factory):
    factory, session, tx = mock_neo4j_session_factory
    msg = ChatMessage(role=ChatMessageRole.USER, content="What is this?")
    msg_data = {
        "id": msg.id,
        "role": "user",
        "content": "What is this?",
        "timestamp": msg.timestamp.isoformat(),
    }
    tx.run.return_value.single.return_value = {"m": msg_data}

    result = chat_service.add_message("u1", "c1", msg)

    assert result.content == "What is this?"
    assert result.role == ChatMessageRole.USER
    tx.run.assert_called_once()


def test_to_llm_messages():
    messages = [
        ChatMessage(role=ChatMessageRole.USER, content="Hello"),
        ChatMessage(role=ChatMessageRole.ASSISTANT, content="Hi"),
    ]
    llm_messages = ChatService.to_llm_messages(messages)

    assert len(llm_messages) == 2
    assert llm_messages[0]["role"] == "user"
    assert llm_messages[0]["content"] == "Hello"
    assert llm_messages[1]["role"] == "assistant"
    assert llm_messages[1]["content"] == "Hi"
