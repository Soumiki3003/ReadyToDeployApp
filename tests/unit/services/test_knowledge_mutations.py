import pytest
from unittest.mock import MagicMock
from pathlib import Path
from app.services.knowledge import KnowledgeService
from app.schemas.knowledge import UpdateRootNodeRequest, CreateRelationshipRequest, UpdateRelationshipRequest, DeleteRelationshipRequest, CreateConceptualNodeRequest

@pytest.fixture
def knowledge_service(mock_neo4j_session_factory):
    factory, session, tx = mock_neo4j_session_factory
    
    agent = MagicMock()
    file_service = MagicMock()
    upload_service = MagicMock()
    template_env = MagicMock()
    
    return KnowledgeService(
        session_factory=factory,
        agent=agent,
        file_service=file_service,
        upload_service=upload_service,
        static_folder=Path("/tmp"),
        template_env=template_env
    )

def test_update_node(knowledge_service, mock_neo4j_session_factory):
    factory, session, tx = mock_neo4j_session_factory
    
    req = UpdateRootNodeRequest(name="Updated", type="root").model_dump()
    knowledge_service.update_node("n1", req)
    assert tx.run.call_count >= 1
    
def test_delete_node(knowledge_service, mock_neo4j_session_factory):
    factory, session, tx = mock_neo4j_session_factory
    
    knowledge_service.delete_node("n1", "c1")
    assert tx.run.call_count >= 1
    
def test_add_child_node(knowledge_service, mock_neo4j_session_factory):
    factory, session, tx = mock_neo4j_session_factory
    tx.run.return_value.single.return_value = {"type": "root"}
    
    req = CreateConceptualNodeRequest(name="Child", type="conceptual", label="L", difficulty="easy", bloom_level="remember", definition="def", learning_objective="lo").model_dump()
    res = knowledge_service.add_child_node("c1", "conceptual", req)
    assert res is not None
    assert tx.run.call_count >= 1
    
def test_add_relationship(knowledge_service, mock_neo4j_session_factory):
    factory, session, tx = mock_neo4j_session_factory
    
    knowledge_service.add_relationship("n1", "n2", "DEPENDS_ON")
    assert tx.run.call_count >= 1
    
def test_update_relationship(knowledge_service, mock_neo4j_session_factory):
    factory, session, tx = mock_neo4j_session_factory
    
    knowledge_service.update_relationship("n1", "n2", "DEPENDS_ON", "PREREQUISITE_FOR")
    assert tx.run.call_count >= 1
    
def test_delete_relationship(knowledge_service, mock_neo4j_session_factory):
    factory, session, tx = mock_neo4j_session_factory
    
    knowledge_service.delete_relationship("n1", "n2", "DEPENDS_ON")
    assert tx.run.call_count >= 1
