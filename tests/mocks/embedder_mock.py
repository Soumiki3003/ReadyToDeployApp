import pytest
from pydantic_ai import Embedder


@pytest.fixture
def mock_embedder(mocker):
    mock = mocker.MagicMock(spec=Embedder)
    mock.embed_documents_sync = mocker.MagicMock(side_effect=lambda texts: [[0.1] * 384])
    return mock
