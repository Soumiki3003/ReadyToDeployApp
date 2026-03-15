import pytest
from app.models.knowledge import (
    ConceptualKnowledge, 
    ProceduralKnowledge, 
    KnowledgeVisibility,
    RootKnowledge
)

def test_conceptual_knowledge_visibility_validation(conceptual_knowledge):
    conceptual_knowledge.visibility = [KnowledgeVisibility.INSTRUCTOR, KnowledgeVisibility.INSTRUCTOR]
    conceptual_knowledge.validate_visibility()
    assert len(conceptual_knowledge.visibility) == 1

def test_conceptual_knowledge_set_source(conceptual_knowledge, procedural_knowledge):
    conceptual_knowledge.children.append(procedural_knowledge)
    conceptual_knowledge.set_source_recursively("new_source.pdf")
    assert conceptual_knowledge.source == "new_source.pdf"

def test_procedural_knowledge_completed(procedural_knowledge):
    procedural_knowledge.percent_done = 100.0
    assert procedural_knowledge.completed is True
    
    procedural_knowledge.percent_done = 99.9
    assert procedural_knowledge.completed is False

def test_root_knowledge_override_sources(root_knowledge, conceptual_knowledge_factory):
    child1 = conceptual_knowledge_factory.build()
    child2 = conceptual_knowledge_factory.build()
    root_knowledge.children = [child1, child2]
    
    root_knowledge.override_conceptual_sources("new_source.pdf")
    
    assert "new_source.pdf" in root_knowledge.sources
    assert child1.source == "new_source.pdf"
    assert child2.source == "new_source.pdf"
