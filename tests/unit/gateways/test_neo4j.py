import pytest
from neo4j import Driver
from neo4j_graphrag.llm.base import LLMInterface
from neo4j_graphrag.embeddings.base import Embedder as EmbedderInterface
from unittest.mock import MagicMock
from app.gateways.neo4j import (
    neo4j_driver,
    neo4j_session,
    neo4j_graphrag,
    Neo4jAgent,
    Neo4jEmbedder,
    Neo4jGraphRAGParams,
    Neo4jGraphRAGVectorIndexParams,
    Neo4jGraphRAGFulltextIndexParams
)

def test_neo4j_driver(mocker):
    mock_driver = mocker.patch("app.gateways.neo4j.GraphDatabase.driver")
    mock_driver.return_value = MagicMock()
    with neo4j_driver("uri", user="user", password="password") as driver:
        assert driver is not None
    mock_driver.assert_called_once()
    
def test_neo4j_session(mocker):
    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session
    
    with neo4j_session(mock_driver) as session:
        assert session == mock_session
        
def test_neo4j_graphrag(mocker):
    mocker.patch("app.gateways.neo4j.create_vector_index")
    mocker.patch("app.gateways.neo4j.create_fulltext_index")
    mocker.patch("app.gateways.neo4j.GraphRAG")
    mocker.patch("app.gateways.neo4j.VectorRetriever")
    
    mock_embedder = MagicMock(spec=EmbedderInterface)
    mock_embedder.embed_query.return_value = [0.1] * 384
    mock_llm = MagicMock(spec=LLMInterface)
    
    params = Neo4jGraphRAGParams(
        driver=MagicMock(spec=Driver),
        llm=mock_llm,
        embedder=mock_embedder,
        vector_index=Neo4jGraphRAGVectorIndexParams(name="v", label="l"),
        fulltext_index=Neo4jGraphRAGFulltextIndexParams(name="f", label="l", node_properties=["p"])
    )
    
    res = neo4j_graphrag(params)
    assert res is not None

def test_neo4j_agent(mocker):
    mock_agent = MagicMock()
    mock_agent.model.model_name = "test"
    mock_agent.model_settings = {}
    
    agent = Neo4jAgent.from_pydantic_agent(mock_agent)
    assert agent.model_name == "test"
    
def test_neo4j_embedder():
    mock_pa_embedder = MagicMock()
    mock_result = MagicMock()
    mock_result.embeddings = [[0.1]*10]
    mock_pa_embedder.embed_documents_sync.return_value = mock_result
    
    embedder = Neo4jEmbedder(mock_pa_embedder)
    
    # We must patch rate limit handler since EmbedderInterface uses it internally
    embedder._rate_limit_handler = MagicMock()
    embedder._rate_limit_handler.handle_sync.return_value = mock_pa_embedder.embed_documents_sync
    
    res = embedder.embed_query("test")
    assert len(res) == 10
