import pytest
from unittest.mock import MagicMock
from app.controllers.knowledge import KnowledgeController
from app.schemas import (
    UpdateConceptualNodeRequest,
    CreateConceptualNodeRequest,
    CreateRelationshipRequest,
    UpdateRelationshipRequest,
    DeleteRelationshipRequest,
)
from app.models.knowledge import KnowledgeConceptualLinkType


@pytest.fixture
def knowledge_controller(mock_knowledge_service):
    return KnowledgeController(knowledge_service=mock_knowledge_service, uploads_service=MagicMock())


def test_get_uploads(knowledge_controller):
    knowledge_controller._KnowledgeController__uploads_service.get_many.return_value = ["u1"]
    res = knowledge_controller.get_uploads(1, 10)
    assert res == ["u1"]
    knowledge_controller._KnowledgeController__uploads_service.get_many.assert_called_with(limit=10, offset=0)


def test_get_uploads_invalid(knowledge_controller):
    with pytest.raises(ValueError):
        knowledge_controller.get_uploads(0, 10)


def test_get_knowledge(knowledge_controller, mock_knowledge_service):
    mock_knowledge_service.get_knowledge.side_effect = lambda k_id: MagicMock(id=k_id)
    knowledge_controller.get_knowledge("k1")
    mock_knowledge_service.get_knowledge.assert_called_with("k1")


def test_get_knowledge_invalid(knowledge_controller):
    with pytest.raises(ValueError):
        knowledge_controller.get_knowledge("")


def test_update_node(knowledge_controller, mock_knowledge_service):
    mock_knowledge_service.update_node.side_effect = lambda *a: None
    req = UpdateConceptualNodeRequest(name="New Name", type="conceptual", label="t", definition="d", learning_objective="l", source="s")
    knowledge_controller.update_node("n1", req)
    mock_knowledge_service.update_node.assert_called_once()


def test_delete_node(knowledge_controller, mock_knowledge_service):
    mock_knowledge_service.delete_node.side_effect = lambda *a: None
    knowledge_controller.delete_node("n1", "c1")
    mock_knowledge_service.delete_node.assert_called_with("n1", "c1")


def test_add_child_node(knowledge_controller, mock_knowledge_service):
    mock_knowledge_service.add_child_node.side_effect = lambda *a: MagicMock()
    req = CreateConceptualNodeRequest(type="conceptual", name="C1", label="L1", definition="x", learning_objective="y", source="z")
    knowledge_controller.add_child_node("n1", req)
    mock_knowledge_service.add_child_node.assert_called_once()


def test_add_relationship(knowledge_controller, mock_knowledge_service):
    mock_knowledge_service.add_relationship.side_effect = lambda *a: None
    req = CreateRelationshipRequest(to_id="n2", relation=KnowledgeConceptualLinkType.PREREQUISITE_FOR)
    knowledge_controller.add_relationship("n1", req)
    mock_knowledge_service.add_relationship.assert_called_with("n1", "n2", KnowledgeConceptualLinkType.PREREQUISITE_FOR.value)


def test_update_relationship(knowledge_controller, mock_knowledge_service):
    mock_knowledge_service.update_relationship.side_effect = lambda *a: None
    req = UpdateRelationshipRequest(to_id="n2", old_relation=KnowledgeConceptualLinkType.PREREQUISITE_FOR, new_relation=KnowledgeConceptualLinkType.DEPENDS_ON)
    knowledge_controller.update_relationship("n1", req)
    mock_knowledge_service.update_relationship.assert_called_with("n1", "n2", KnowledgeConceptualLinkType.PREREQUISITE_FOR.value, KnowledgeConceptualLinkType.DEPENDS_ON.value)


def test_delete_relationship(knowledge_controller, mock_knowledge_service):
    mock_knowledge_service.delete_relationship.side_effect = lambda *a: None
    req = DeleteRelationshipRequest(to_id="n2", relation=KnowledgeConceptualLinkType.PREREQUISITE_FOR)
    knowledge_controller.delete_relationship("n1", req)
    mock_knowledge_service.delete_relationship.assert_called_with("n1", "n2", KnowledgeConceptualLinkType.PREREQUISITE_FOR.value)
