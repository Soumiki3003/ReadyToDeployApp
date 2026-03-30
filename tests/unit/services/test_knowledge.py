import pytest
from unittest.mock import MagicMock
from pathlib import Path
from app.services.knowledge import KnowledgeService
from app.models.knowledge import RootKnowledge

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

def test_delete_course(knowledge_service, mock_neo4j_session_factory):
    factory, session, tx = mock_neo4j_session_factory
    
    tx.run.return_value.single.return_value = {"id": "course_123"}
    knowledge_service.delete_course("course_123")
    assert tx.run.call_count == 3

def test_clear_course(knowledge_service, mock_neo4j_session_factory):
    factory, session, tx = mock_neo4j_session_factory
    
    tx.run.return_value.single.return_value = {"id": "course_123"}
    knowledge_service.clear_course("course_123")
    assert tx.run.call_count == 3

def test_set_course_instructors(knowledge_service, mock_neo4j_session_factory):
    factory, session, tx = mock_neo4j_session_factory
    knowledge_service.set_course_instructors("course_123", ["user_1"])
    assert tx.run.call_count == 2

def test_set_course_students(knowledge_service, mock_neo4j_session_factory):
    factory, session, tx = mock_neo4j_session_factory
    knowledge_service.set_course_students("course_123", ["user_1"])
    assert tx.run.call_count == 2

def test_get_root_nodes(knowledge_service, mock_neo4j_session_factory):
    factory, session, tx = mock_neo4j_session_factory
    
    # Mocking session.run for reading root nodes
    session.run.return_value.data.return_value = [
        {"id": "course_123", "name": "Test Course", "description": "Desc", "sources": []}
    ]
    
    nodes = knowledge_service.get_root_nodes()
    assert len(nodes) == 1
    assert nodes[0].id == "course_123"

def test_create_empty_course(knowledge_service, mock_neo4j_session_factory):
    factory, session, tx = mock_neo4j_session_factory
    
    tx.run.return_value.single.return_value = {"n": {
        "id": "course_123",
        "type": "root",
        "name": "Test Course"
    }}
    
    course_id = knowledge_service.create_empty_course("Test Course")
    assert isinstance(course_id, str)
    assert len(course_id) > 0

def test_get_knowledge(knowledge_service, mock_neo4j_session_factory):
    factory, session, tx = mock_neo4j_session_factory
    
    tx.run.return_value.single.return_value = {
        "nodes": [
            {"id": "root_1", "type": "root", "name": "Course"},
            {"id": "concept_1", "type": "conceptual", "name": "Concept", "label": "L", "difficulty": "easy", "bloom_level": "remember", "definition": "A", "learning_objective": "B", "source": "C", "relevance_score": 1.0, "confidence_score": 1.0},
        ],
        "child_edges": [{"parent": "root_1", "child": "concept_1"}],
        "other_edges": []
    }
    
    root = knowledge_service.get_knowledge("root_1")
    assert root.id == "root_1"
    assert len(root.children) == 1
    assert root.children[0].id == "concept_1"

def test_create_knowledge_from_file_success(knowledge_service, mock_neo4j_session_factory, mocker, root_knowledge_factory):
    factory, session, tx = mock_neo4j_session_factory
    tx.run.return_value.single.return_value = {"n": {
        "id": "course_123",
        "type": "root",
        "name": "Test Course"
    }}
    
    knowledge_service._KnowledgeService__file_service.extract_textual_content.return_value = ["test"]
    knowledge_service._KnowledgeService__file_service.extract_visual_content.return_value = ["visual"]
    knowledge_service._KnowledgeService__upload_service.create.return_value = "upload_123"
    
    mock_agent_output = MagicMock()
    mock_agent_output.output = MagicMock()
    knowledge_service._KnowledgeService__agent.run_sync.return_value = mock_agent_output
    
    mocker.patch("app.models.knowledge.RootKnowledge.model_validate", return_value=root_knowledge_factory.build())
    mocker.patch.object(knowledge_service, "_KnowledgeService__create_knowledge_graph")
    
    from pathlib import Path
    p = Path("/tmp/test.pdf")
    res = knowledge_service.create_knowledge_from_file(p)
    assert res is not None

def test_add_document_to_course(knowledge_service, mock_neo4j_session_factory, mocker, root_knowledge_factory):
    factory, session, tx = mock_neo4j_session_factory
    tx.run.return_value.single.return_value = {"n": {"id": "course_123", "type": "root", "name": "Course"}}
    
    knowledge_service._KnowledgeService__file_service.extract_textual_content.return_value = ["test"]
    knowledge_service._KnowledgeService__file_service.extract_visual_content.return_value = ["visual"]
    knowledge_service._KnowledgeService__upload_service.create.return_value = "upload_123"
    
    mock_agent_output = MagicMock()
    mock_agent_output.output = MagicMock()
    knowledge_service._KnowledgeService__agent.run_sync.return_value = mock_agent_output
    
    mocker.patch("app.models.knowledge.RootKnowledge.model_validate", return_value=root_knowledge_factory.build())
    mocker.patch.object(knowledge_service, "_KnowledgeService__create_knowledge_graph")
    
    from pathlib import Path
    res = knowledge_service.add_document_to_course("course_123", Path("/tmp/doc.pdf"))
    assert res == "course_123"
