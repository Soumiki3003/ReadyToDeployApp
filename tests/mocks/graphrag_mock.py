import pytest
from neo4j_graphrag.generation import GraphRAG
from neo4j_graphrag.llm.base import LLMInterface
from neo4j_graphrag.retrievers import VectorRetriever


@pytest.fixture
def mock_graphrag(mocker):
    mock_retriever = mocker.MagicMock(spec=VectorRetriever)
    mock_llm = mocker.MagicMock(spec=LLMInterface)
    instance = GraphRAG(retriever=mock_retriever, llm=mock_llm)
    mock = mocker.MagicMock(spec=GraphRAG)
    mock.search = mocker.MagicMock(side_effect=instance.search)
    return mock
