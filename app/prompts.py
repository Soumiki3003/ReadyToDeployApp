from jinja2 import Environment
from app import models


def get_knowledge_system_prompt(env: Environment) -> str:
    return env.get_template("knowledge_system_prompt.j2").render(
        relation_types=[e.value for e in models.KnowledgeConceptualLinkType],
        bloom_levels={
            "conceptual": [e.value for e in models.KnowledgeConceptualBloomLevel],
            "procedural": [e.value for e in models.KnowledgeProceduralBloomLevel],
            "assessment": [e.value for e in models.KnowledgeAssessmentBloomLevel],
        },
        visibility_options=[e.value for e in models.KnowledgeVisibility],
        validation_statuses=[e.value for e in models.KnowledgeValidationStatus],
        difficulty_levels=[e.value for e in models.KnowledgeDifficulty],
        # ── Schema field tables ─────────────────────────────────
        field_docs={
            "conceptual": models.ConceptualKnowledge.model_json_schema(),
            "procedural": models.ProceduralKnowledge.model_json_schema(),
            "assessment": models.AssessmentKnowledge.model_json_schema(),
        },
    )
