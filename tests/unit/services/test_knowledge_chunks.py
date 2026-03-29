import pytest
from pathlib import Path
from unittest.mock import MagicMock

from app.models.knowledge import ContentChunk, ContentChunkType
from app.services.knowledge import KnowledgeService


@pytest.fixture
def mock_file_service():
    return MagicMock()


@pytest.fixture
def knowledge_service_with_embedder(
    mock_neo4j_session_factory, mock_embedder, mock_file_service
):
    factory, session, tx = mock_neo4j_session_factory
    return KnowledgeService(
        session_factory=factory,
        agent=MagicMock(),
        file_service=mock_file_service,
        upload_service=MagicMock(),
        static_folder=Path("/tmp"),
        template_env=MagicMock(),
        embedder=mock_embedder,
    )


def _make_chunks(count: int, course_id: str = "course_123") -> list[ContentChunk]:
    return [
        ContentChunk(
            content=f"Chunk content {i}",
            page=i,
            source_file="test.pdf",
            chunk_index=i,
            course_id=course_id,
            chunk_type=ContentChunkType.PAGE,
        )
        for i in range(count)
    ]


def test_store_content_chunks_creates_nodes(
    knowledge_service_with_embedder, mock_neo4j_session_factory, mock_embedder
):
    _, session, tx = mock_neo4j_session_factory
    chunks = _make_chunks(3)
    mock_embedder.embed_documents_sync.side_effect = lambda texts: [
        [0.1] * 384 for _ in texts
    ]
    tx.run.reset_mock()

    knowledge_service_with_embedder._KnowledgeService__store_content_chunks(
        chunks, "course_123", tx=tx
    )

    # One tx.run call per chunk (CREATE node + relationship in single query)
    assert tx.run.call_count == 3


def test_store_content_chunks_embeds_content(
    knowledge_service_with_embedder, mock_neo4j_session_factory, mock_embedder
):
    _, session, tx = mock_neo4j_session_factory
    chunks = _make_chunks(2)
    mock_embedder.embed_documents_sync.side_effect = lambda texts: [
        [0.1] * 384 for _ in texts
    ]
    mock_embedder.embed_documents_sync.reset_mock()

    knowledge_service_with_embedder._KnowledgeService__store_content_chunks(
        chunks, "course_123", tx=tx
    )

    mock_embedder.embed_documents_sync.assert_called_once_with(
        ["Chunk content 0", "Chunk content 1"]
    )


def test_store_content_chunks_stores_vector(
    knowledge_service_with_embedder, mock_neo4j_session_factory, mock_embedder
):
    _, session, tx = mock_neo4j_session_factory
    chunks = _make_chunks(1)
    expected_vector = [0.5] * 384
    mock_embedder.embed_documents_sync.side_effect = lambda texts: [expected_vector]

    knowledge_service_with_embedder._KnowledgeService__store_content_chunks(
        chunks, "course_123", tx=tx
    )

    call_kwargs = tx.run.call_args
    props = call_kwargs.kwargs.get("props") or call_kwargs[1].get("props")
    assert props["chunk_vector"] == expected_vector


def test_store_content_chunks_empty_list(
    knowledge_service_with_embedder, mock_neo4j_session_factory, mock_embedder
):
    _, session, tx = mock_neo4j_session_factory
    tx.run.reset_mock()
    mock_embedder.embed_documents_sync.reset_mock()

    knowledge_service_with_embedder._KnowledgeService__store_content_chunks(
        [], "course_123", tx=tx
    )

    tx.run.assert_not_called()
    mock_embedder.embed_documents_sync.assert_not_called()


def test_store_content_chunks_embedding_failure_uses_zero_vector(
    knowledge_service_with_embedder, mock_neo4j_session_factory, mock_embedder
):
    _, session, tx = mock_neo4j_session_factory
    chunks = _make_chunks(2)
    mock_embedder.embed_documents_sync.side_effect = RuntimeError("Embedding failed")
    tx.run.reset_mock()

    knowledge_service_with_embedder._KnowledgeService__store_content_chunks(
        chunks, "course_123", tx=tx
    )

    # Should still create nodes with zero vectors
    assert tx.run.call_count == 2
    for call in tx.run.call_args_list:
        props = call.kwargs.get("props") or call[1].get("props")
        assert props["chunk_vector"] == [0.0] * 384
