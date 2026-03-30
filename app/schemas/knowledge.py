from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app import models


class KnowledgeRootNode(BaseModel):
    id: str = Field(description="Knowledge graph root node ID")
    name: str | None = Field(
        default=None,
        description="Root node display name (course title)",
    )
    description: str | None = Field(
        default=None,
        description="Course description",
    )
    sources: list[str] = Field(
        default_factory=list,
        description="List of source files for this knowledge graph",
    )


# ── Type mappings (passed to templates) ──

ALLOWED_CHILDREN: dict[str, list[str]] = {
    models.KnowledgeType.ROOT.value: [models.KnowledgeType.CONCEPTUAL.value],
    models.KnowledgeType.CONCEPTUAL.value: [
        models.KnowledgeType.PROCEDURAL.value,
        models.KnowledgeType.ASSESSMENT.value,
    ],
    models.KnowledgeType.PROCEDURAL.value: [models.KnowledgeType.PROCEDURAL.value],
    models.KnowledgeType.ASSESSMENT.value: [],
}

BLOOM_LEVELS: dict[str, list[str]] = {
    models.KnowledgeType.CONCEPTUAL.value: [
        e.value for e in models.KnowledgeConceptualBloomLevel
    ],
    models.KnowledgeType.PROCEDURAL.value: [
        e.value for e in models.KnowledgeProceduralBloomLevel
    ],
    models.KnowledgeType.ASSESSMENT.value: [
        e.value for e in models.KnowledgeAssessmentBloomLevel
    ],
}


# ── Update schemas (type-specific) ──


class UpdateRootNodeRequest(BaseModel):
    """Partial update for a root node."""

    type: Literal["root"]
    name: str | None = None
    description: str | None = None


class UpdateConceptualNodeRequest(BaseModel):
    """Partial update for a conceptual node."""

    type: Literal["conceptual"]
    name: str | None = None
    label: str | None = None
    difficulty: models.KnowledgeDifficulty | None = None
    bloom_level: models.KnowledgeConceptualBloomLevel | None = None
    definition: str | None = None
    learning_objective: str | None = None
    source: str | None = None
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)
    relevance_score: float | None = Field(default=None, ge=0.0, le=1.0)
    validation_status: models.KnowledgeValidationStatus | None = None
    visibility: list[models.KnowledgeVisibility] | None = None
    prerequisites: list[str] | None = None
    misconceptions: list[str] | None = None


class UpdateProceduralNodeRequest(BaseModel):
    """Partial update for a procedural node."""

    type: Literal["procedural"]
    name: str | None = None
    label: str | None = None
    difficulty: models.KnowledgeDifficulty | None = None
    bloom_level: models.KnowledgeProceduralBloomLevel | None = None
    percent_done: float | None = Field(default=None, ge=0.0, le=100.0)
    common_errors: list[str] | None = None
    learning_objective: str | None = None
    source: str | None = None
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)
    relevance_score: float | None = Field(default=None, ge=0.0, le=1.0)
    validation_status: models.KnowledgeValidationStatus | None = None
    visibility: list[models.KnowledgeVisibility] | None = None


class UpdateAssessmentNodeRequest(BaseModel):
    """Partial update for an assessment node."""

    type: Literal["assessment"]
    name: str | None = None
    label: str | None = None
    difficulty: models.KnowledgeDifficulty | None = None
    bloom_level: models.KnowledgeAssessmentBloomLevel | None = None
    linked_challenges: list[str] | None = None
    objectives: list[str] | None = None
    question_prompts: list[str] | None = None
    evaluation_criteria: list[str] | None = None


UpdateNodeRequest = Annotated[
    UpdateRootNodeRequest
    | UpdateConceptualNodeRequest
    | UpdateProceduralNodeRequest
    | UpdateAssessmentNodeRequest,
    Field(discriminator="type"),
]


# ── Create schemas (type-specific) ──


class CreateConceptualNodeRequest(BaseModel):
    """Create a new conceptual child node."""

    type: Literal["conceptual"]
    name: str = Field(min_length=1)
    label: str = Field(min_length=1)
    difficulty: models.KnowledgeDifficulty = models.KnowledgeDifficulty.MEDIUM
    bloom_level: models.KnowledgeConceptualBloomLevel = (
        models.KnowledgeConceptualBloomLevel.REMEMBER
    )
    definition: str = ""
    learning_objective: str = ""
    source: str = ""
    confidence_score: float = Field(default=0.8, ge=0.0, le=1.0)
    relevance_score: float = Field(default=0.8, ge=0.0, le=1.0)


class CreateProceduralNodeRequest(BaseModel):
    """Create a new procedural child node."""

    type: Literal["procedural"]
    name: str = Field(min_length=1)
    label: str = Field(min_length=1)
    difficulty: models.KnowledgeDifficulty = models.KnowledgeDifficulty.MEDIUM
    bloom_level: models.KnowledgeProceduralBloomLevel = (
        models.KnowledgeProceduralBloomLevel.APPLY
    )
    learning_objective: str = ""
    source: str = ""
    confidence_score: float = Field(default=0.8, ge=0.0, le=1.0)
    relevance_score: float = Field(default=0.8, ge=0.0, le=1.0)
    percent_done: float = Field(default=0.0, ge=0.0, le=100.0)


class CreateAssessmentNodeRequest(BaseModel):
    """Create a new assessment child node."""

    type: Literal["assessment"]
    name: str = Field(min_length=1)
    label: str = Field(min_length=1)
    difficulty: models.KnowledgeDifficulty = models.KnowledgeDifficulty.MEDIUM
    bloom_level: models.KnowledgeAssessmentBloomLevel = (
        models.KnowledgeAssessmentBloomLevel.EVALUATE
    )


CreateChildNodeRequest = Annotated[
    CreateConceptualNodeRequest
    | CreateProceduralNodeRequest
    | CreateAssessmentNodeRequest,
    Field(discriminator="type"),
]


class CreateRelationshipRequest(BaseModel):
    """Create a conceptual relationship between two nodes."""

    to_id: str = Field(min_length=1, description="Target node ID")
    relation: models.KnowledgeConceptualLinkType


class UpdateRelationshipRequest(BaseModel):
    """Update the type of an existing conceptual relationship."""

    to_id: str = Field(min_length=1, description="Target node ID")
    old_relation: models.KnowledgeConceptualLinkType
    new_relation: models.KnowledgeConceptualLinkType


class DeleteRelationshipRequest(BaseModel):
    """Delete a conceptual relationship between two nodes."""

    to_id: str = Field(min_length=1, description="Target node ID")
    relation: models.KnowledgeConceptualLinkType


class DeleteNodeRequest(BaseModel):
    """Delete a node and its subtree from a course."""

    course_id: str = Field(min_length=1, description="Course root ID for scoping")
