from jinja2 import Environment

from app import models


def get_knowledge_system_prompt(env: Environment) -> str:
    return env.get_template("knowledge_system_prompt.j2").render(
        relation_types=[e.value for e in models.KnowledgeConceptualLinkType],
        relation_descriptions={
            models.KnowledgeConceptualLinkType.PREREQUISITE_FOR.value: "This concept must be learned before the target concept",
            models.KnowledgeConceptualLinkType.DEPENDS_ON.value: "This concept requires the target concept to be understood first",
            models.KnowledgeConceptualLinkType.EXTENDS_TO.value: "This concept is expanded upon or detailed further by the target concept",
            models.KnowledgeConceptualLinkType.GENERALIZES_TO.value: "This concept is a specific case of the more general target concept",
            models.KnowledgeConceptualLinkType.USES_INIT_FROM.value: "This concept uses initialization or setup from the target concept",
            models.KnowledgeConceptualLinkType.IMPLEMENTED_BY.value: "This concept is implemented or realized by the target concept",
            models.KnowledgeConceptualLinkType.ENABLES.value: "This concept enables or makes possible the target concept",
        },
        bloom_levels={
            models.KnowledgeType.CONCEPTUAL.value: [
                e.value for e in models.KnowledgeConceptualBloomLevel
            ],
            models.KnowledgeType.PROCEDURAL.value: [
                e.value for e in models.KnowledgeProceduralBloomLevel
            ],
            models.KnowledgeType.ASSESSMENT.value: [
                e.value for e in models.KnowledgeAssessmentBloomLevel
            ],
        },
        visibility_options=[e.value for e in models.KnowledgeVisibility],
        validation_statuses=[e.value for e in models.KnowledgeValidationStatus],
        difficulty_levels=[e.value for e in models.KnowledgeDifficulty],
        # ── Schema field tables ─────────────────────────────────
        field_docs={
            models.KnowledgeType.CONCEPTUAL.value: models.ConceptualKnowledge.model_json_schema(),
            models.KnowledgeType.PROCEDURAL.value: models.ProceduralKnowledge.model_json_schema(),
            models.KnowledgeType.ASSESSMENT.value: models.AssessmentKnowledge.model_json_schema(),
        },
        example_json=_get_example_json(),
    )


def _get_example_json(*, indent: int = 2) -> str:
    """Return an example JSON structure for the knowledge graph."""
    return models.RootKnowledge.model_validate(
        {
            "id": "root-uuid-12345",
            "type": "root",
            "name": "Central node",
            "sources": ["CTF_tutorial.pdf"],
            "children": [
                {
                    "id": "concept-uuid-001",
                    "type": "conceptual",
                    "name": "angr_framework",
                    "label": "Angr Binary Analysis Framework",
                    "difficulty": "medium",
                    "bloom_level": "understand",
                    "definition": "Angr is a Python framework for analyzing binaries...",
                    "prerequisites": [],
                    "misconceptions": [
                        "Angr automatically solves all binary challenges",
                        "Symbolic execution always finds all paths",
                    ],
                    "visibility": ["supervisor_agent", "instructor"],
                    "validation_status": "pending",
                    "confidence_score": 0.9,
                    "relevance_score": 0.95,
                    "source": "CTF_tutorial.pdf [page 1]",
                    "learning_objective": "Understand the purpose and capabilities of angr",
                    "connections": [
                        {
                            "relation": "PREREQUISITE_FOR",
                            "to": "angr_project_initialization",
                        }
                    ],
                    "children": [
                        {
                            "id": "proc-uuid-001",
                            "type": "procedural",
                            "name": "install_angr",
                            "label": "Install Angr Framework",
                            "difficulty": "easy",
                            "bloom_level": "apply",
                            "common_errors": [
                                "Python version incompatibility",
                                "Missing system dependencies",
                            ],
                            "visibility": ["supervisor_agent"],
                            "validation_status": "pending",
                            "confidence_score": 0.95,
                            "relevance_score": 0.85,
                            "source": "CTF_tutorial.pdf [page 1]",
                            "learning_objective": "Successfully install angr in a Python environment",
                            "percent_done": 33.33,
                            "child": {
                                "id": "proc-uuid-002",
                                "type": "procedural",
                                "name": "verify_installation",
                                "label": "Verify Angr Installation",
                                "difficulty": "easy",
                                "bloom_level": "apply",
                                "common_errors": [],
                                "visibility": ["supervisor_agent"],
                                "validation_status": "pending",
                                "confidence_score": 0.9,
                                "relevance_score": 0.8,
                                "source": "CTF_tutorial.pdf [page 1]",
                                "learning_objective": "Confirm angr is properly installed",
                                "percent_done": 66.66,
                                "child": {
                                    "id": "proc-uuid-003",
                                    "type": "procedural",
                                    "name": "import_angr",
                                    "label": "Import Angr in Python",
                                    "difficulty": "easy",
                                    "bloom_level": "apply",
                                    "common_errors": [],
                                    "visibility": ["supervisor_agent"],
                                    "validation_status": "pending",
                                    "confidence_score": 0.95,
                                    "relevance_score": 0.85,
                                    "source": "CTF_tutorial.pdf [page 1]",
                                    "learning_objective": "Import angr module in Python",
                                    "percent_done": 100.0,
                                    "child": None,
                                },
                            },
                        },
                        {
                            "id": "assess-uuid-001",
                            "type": "assessment",
                            "name": "angr_basics_quiz",
                            "label": "Angr Basics Assessment",
                            "difficulty": "medium",
                            "bloom_level": "evaluate",
                            "linked_challenges": ["quiz_01", "coding_exercise_01"],
                            "objectives": [
                                "Evaluate understanding of angr capabilities",
                                "Assess ability to identify appropriate use cases",
                            ],
                            "question_prompts": [
                                "When is symbolic execution most effective?",
                                "What are the limitations of angr?",
                            ],
                            "evaluation_criteria": [
                                "Correctly identifies symbolic execution scenarios",
                                "Understands performance trade-offs",
                            ],
                        },
                    ],
                }
            ],
        }
    ).model_dump_json(ensure_ascii=True, indent=indent)
