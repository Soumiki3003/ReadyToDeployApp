import pytest
from pathlib import Path
from unittest.mock import MagicMock
from app.services.knowledge import KnowledgeService


@pytest.fixture
def mock_knowledge_service(mocker, mock_neo4j_session_factory):
    factory, _, _ = mock_neo4j_session_factory
    instance = KnowledgeService(
        session_factory=factory,
        agent=MagicMock(),
        file_service=MagicMock(),
        upload_service=MagicMock(),
        static_folder=Path("/tmp"),
        template_env=MagicMock(),
    )
    mock = mocker.MagicMock(spec=KnowledgeService)
    mock.get_knowledge = mocker.MagicMock(side_effect=instance.get_knowledge)
    mock.get_root_nodes = mocker.MagicMock(side_effect=instance.get_root_nodes)
    mock.create_empty_course = mocker.MagicMock(side_effect=instance.create_empty_course)
    mock.add_document_to_course = mocker.MagicMock(side_effect=instance.add_document_to_course)
    mock.set_course_instructors = mocker.MagicMock(side_effect=instance.set_course_instructors)
    mock.set_course_students = mocker.MagicMock(side_effect=instance.set_course_students)
    mock.get_course_members = mocker.MagicMock(side_effect=instance.get_course_members)
    mock.delete_course = mocker.MagicMock(side_effect=instance.delete_course)
    mock.clear_course = mocker.MagicMock(side_effect=instance.clear_course)
    mock.update_node = mocker.MagicMock(side_effect=instance.update_node)
    mock.delete_node = mocker.MagicMock(side_effect=instance.delete_node)
    mock.add_child_node = mocker.MagicMock(side_effect=instance.add_child_node)
    mock.add_relationship = mocker.MagicMock(side_effect=instance.add_relationship)
    mock.update_relationship = mocker.MagicMock(side_effect=instance.update_relationship)
    mock.delete_relationship = mocker.MagicMock(side_effect=instance.delete_relationship)
    return mock
