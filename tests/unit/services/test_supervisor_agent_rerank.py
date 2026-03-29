import pytest
from unittest.mock import MagicMock
import json
from app import models
from app.services.supervisor_agent import Intent, SupervisorAgentService


@pytest.fixture
def supervisor_agent(mock_user_service, mock_graphrag):
    return SupervisorAgentService(
        user_service=mock_user_service,
        graph_rag=mock_graphrag,
        hint_agent=MagicMock(),
    )


def _make_item(
    name,
    node_type,
    difficulty: models.KnowledgeDifficulty = models.KnowledgeDifficulty.MEDIUM,
    score=0.8,
):
    item = MagicMock()
    item.content = json.dumps(
        {"name": name, "type": node_type, "difficulty": difficulty}
    )
    item.metadata = {"score": score, "node_type": node_type, "difficulty": difficulty}
    return item


def _make_item_content(
    node_type, difficulty=models.KnowledgeDifficulty.MEDIUM, score=0.8
):
    item = MagicMock()
    item.content = json.dumps(
        {"name": "X", "type": node_type, "difficulty": difficulty}
    )
    item.metadata = {"score": score}
    return item


class TestDefinitionIntentRerank:
    def test_conceptual_above_procedural(self, supervisor_agent):
        items = [
            _make_item("step1", models.KnowledgeType.PROCEDURAL, score=0.9),
            _make_item("c1", models.KnowledgeType.CONCEPTUAL, score=0.8),
        ]
        result = supervisor_agent._SupervisorAgentService__rerank_results(
            items, Intent.DEFINITION, "u1"
        )
        assert result[0] is items[1]
        assert result[1] is items[0]

    def test_conceptual_above_assessment(self, supervisor_agent):
        items = [
            _make_item("a1", models.KnowledgeType.ASSESSMENT, score=0.9),
            _make_item("c1", models.KnowledgeType.CONCEPTUAL, score=0.8),
        ]
        result = supervisor_agent._SupervisorAgentService__rerank_results(
            items, Intent.DEFINITION, "u1"
        )
        assert result[0] is items[1]
        assert result[1] is items[0]

    def test_conceptual_sorted_by_difficulty(self, supervisor_agent):
        items = [
            _make_item(
                "ch",
                models.KnowledgeType.CONCEPTUAL,
                difficulty=models.KnowledgeDifficulty.HARD,
                score=0.8,
            ),
            _make_item(
                "ce",
                models.KnowledgeType.CONCEPTUAL,
                difficulty=models.KnowledgeDifficulty.EASY,
                score=0.7,
            ),
        ]
        result = supervisor_agent._SupervisorAgentService__rerank_results(
            items, Intent.DEFINITION, "u1"
        )
        assert result[0] is items[1]
        assert result[1] is items[0]


class TestProceduralIntentRerank:
    def test_procedural_above_conceptual(self, supervisor_agent):
        items = [
            _make_item("c1", models.KnowledgeType.CONCEPTUAL, score=0.9),
            _make_item("s1", models.KnowledgeType.PROCEDURAL, score=0.8),
        ]
        result = supervisor_agent._SupervisorAgentService__rerank_results(
            items, Intent.PROCEDURAL, "u1"
        )
        assert result[0] is items[1]
        assert result[1] is items[0]

    def test_procedural_above_assessment(self, supervisor_agent):
        items = [
            _make_item("a1", models.KnowledgeType.ASSESSMENT, score=0.9),
            _make_item("s1", models.KnowledgeType.PROCEDURAL, score=0.8),
        ]
        result = supervisor_agent._SupervisorAgentService__rerank_results(
            items, models.KnowledgeType.PROCEDURAL, "u1"
        )
        assert result[0] is items[1]
        assert result[1] is items[0]


class TestTroubleshootingIntentRerank:
    def test_procedural_above_conceptual(self, supervisor_agent):
        items = [
            _make_item("c1", models.KnowledgeType.CONCEPTUAL, score=0.9),
            _make_item("s1", models.KnowledgeType.PROCEDURAL, score=0.8),
        ]
        result = supervisor_agent._SupervisorAgentService__rerank_results(
            items, Intent.TROUBLESHOOTING, "u1"
        )
        assert result[0] is items[1]
        assert result[1] is items[0]

    def test_procedural_above_assessment(self, supervisor_agent):
        items = [
            _make_item("a1", models.KnowledgeType.ASSESSMENT, score=0.9),
            _make_item("s1", models.KnowledgeType.PROCEDURAL, score=0.8),
        ]
        result = supervisor_agent._SupervisorAgentService__rerank_results(
            items, Intent.TROUBLESHOOTING, "u1"
        )
        assert result[0] is items[1]
        assert result[1] is items[0]


class TestExampleRequestIntentRerank:
    def test_assessment_above_conceptual(self, supervisor_agent):
        items = [
            _make_item("c1", models.KnowledgeType.CONCEPTUAL, score=0.9),
            _make_item("a1", models.KnowledgeType.ASSESSMENT, score=0.8),
        ]
        result = supervisor_agent._SupervisorAgentService__rerank_results(
            items, Intent.EXAMPLE_REQUEST, "u1"
        )
        assert result[0] is items[1]
        assert result[1] is items[0]

    def test_assessment_above_procedural(self, supervisor_agent):
        items = [
            _make_item("s1", models.KnowledgeType.PROCEDURAL, score=0.9),
            _make_item("a1", models.KnowledgeType.ASSESSMENT, score=0.8),
        ]
        result = supervisor_agent._SupervisorAgentService__rerank_results(
            items, Intent.EXAMPLE_REQUEST, "u1"
        )
        assert result[0] is items[1]
        assert result[1] is items[0]


class TestRerankPreservesResults:
    def test_preserves_all_items(self, supervisor_agent):
        items = [
            _make_item("a", models.KnowledgeType.CONCEPTUAL),
            _make_item("b", models.KnowledgeType.PROCEDURAL),
            _make_item("c", models.KnowledgeType.ASSESSMENT),
            _make_item("d", models.KnowledgeType.CONCEPTUAL),
        ]
        result = supervisor_agent._SupervisorAgentService__rerank_results(
            items, models.KnowledgeType.PROCEDURAL, "u1"
        )
        assert len(result) == len(items)
        assert set(result) == set(items)

    def test_preserves_single_item(self, supervisor_agent):
        items = [_make_item("only", models.KnowledgeType.CONCEPTUAL)]
        result = supervisor_agent._SupervisorAgentService__rerank_results(
            items, Intent.DEFINITION, "u1"
        )
        assert result == items

    def test_empty_list_returns_empty(self, supervisor_agent):
        result = supervisor_agent._SupervisorAgentService__rerank_results(
            [], Intent.DEFINITION, "u1"
        )
        assert result == []


class TestDifficultyRerank:
    def test_easier_ranked_higher_same_type(self, supervisor_agent):
        items = [
            _make_item(
                "hc",
                models.KnowledgeType.CONCEPTUAL,
                difficulty=models.KnowledgeDifficulty.HARD,
                score=0.9,
            ),
            _make_item(
                "ec",
                models.KnowledgeType.CONCEPTUAL,
                difficulty=models.KnowledgeDifficulty.EASY,
                score=0.8,
            ),
            _make_item(
                "mc",
                models.KnowledgeType.CONCEPTUAL,
                difficulty=models.KnowledgeDifficulty.MEDIUM,
                score=0.85,
            ),
        ]
        result = supervisor_agent._SupervisorAgentService__rerank_results(
            items, Intent.DEFINITION, "u1"
        )
        assert result[0] is items[1]
        assert result[1] is items[2]
        assert result[2] is items[0]


class TestPedagogicalSequence:
    def test_conceptual_before_procedural_before_assessment(self, supervisor_agent):
        items = [
            _make_item("a", models.KnowledgeType.ASSESSMENT, score=0.9),
            _make_item("p", models.KnowledgeType.PROCEDURAL, score=0.85),
            _make_item("c", models.KnowledgeType.CONCEPTUAL, score=0.8),
        ]
        result = supervisor_agent._SupervisorAgentService__rerank_results(
            items, Intent.CONTEXT_REQUEST, "u1"
        )
        assert result[0] is items[2]
        assert result[1] is items[1]
        assert result[2] is items[0]


class TestContentTypeExtraction:
    def test_fallback_parse_from_content(self, supervisor_agent):
        items = [
            _make_item_content(models.KnowledgeType.PROCEDURAL, score=0.9),
            _make_item_content(models.KnowledgeType.CONCEPTUAL, score=0.8),
        ]
        result = supervisor_agent._SupervisorAgentService__rerank_results(
            items, Intent.DEFINITION, "u1"
        )
        assert result[0] is items[1]

    def test_fallback_difficulty_from_content(self, supervisor_agent):
        items = [
            _make_item_content(
                models.KnowledgeType.CONCEPTUAL,
                difficulty=models.KnowledgeDifficulty.HARD,
                score=0.9,
            ),
            _make_item_content(
                models.KnowledgeType.CONCEPTUAL,
                difficulty=models.KnowledgeDifficulty.EASY,
                score=0.8,
            ),
        ]
        result = supervisor_agent._SupervisorAgentService__rerank_results(
            items, Intent.DEFINITION, "u1"
        )
        assert result[0] is items[1]
