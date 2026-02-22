from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, computed_field, model_validator


class KnowledgeDifficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class KnowledgeType(StrEnum):
    CONCEPTUAL = "conceptual"
    PROCEDURAL = "procedural"
    ASSESSMENT = "assessment"
    ROOT = "root"


class KnowledgeConceptualBloomLevel(StrEnum):
    REMEMBER = "remember"
    UNDERSTAND = "understand"


class KnowledgeProceduralBloomLevel(StrEnum):
    APPLY = "apply"
    ANALYZE = "analyze"


class KnowledgeAssessmentBloomLevel(StrEnum):
    EVALUATE = "evaluate"
    CREATE = "create"


class KnowledgeVisibility(StrEnum):
    SUPERVISOR_AGENT = "supervisor_agent"
    INSTRUCTOR = "instructor"


class KnowledgeConceptualLinkType(StrEnum):
    PREREQUISITE_FOR = "PREREQUISITE_FOR"
    DEPENDS_ON = "DEPENDS_ON"
    EXTENDS_TO = "EXTENDS_TO"
    GENERALIZES_TO = "GENERALIZES_TO"
    USES_INIT_FROM = "USES_INIT_FROM"
    IMPLEMENTED_BY = "IMPLEMENTED_BY"
    ENABLES = "ENABLES"


class KnowledgeValidationStatus(StrEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"


class BaseChildKnowledge(BaseModel):
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for the knowledge node, used for referencing and retrieval",
        examples=[uuid4().hex],
    )

    name: str = Field(
        description="A unique name for the knowledge, used for internal referencing and retrieval",
        examples=["angr_project_initialization"],
    )
    label: str = Field(
        description="A human-readable label for the knowledge, used in the UI and explanations",
        examples=["Angr Project Initialization"],
    )

    difficulty: KnowledgeDifficulty = Field(
        description="Difficulty level of the knowledge, can be used for adaptive learning purposes",
        examples=[e.value for e in KnowledgeDifficulty],
    )


class ConceptualKnowledgeConnection(BaseModel):
    relation: KnowledgeConceptualLinkType = Field(
        description="Type of the connection between conceptual knowledge nodes, used for structuring the knowledge graph and providing explanations to students",
        examples=[e.value for e in KnowledgeConceptualLinkType],
    )
    to: str = Field(
        description="Name of the target conceptual knowledge node that this connection points to, used for structuring the knowledge graph and providing explanations to students",
        examples=[uuid4().hex],
    )


class ConceptualKnowledge(BaseChildKnowledge):
    type_: Literal[KnowledgeType.CONCEPTUAL] = Field(
        default=KnowledgeType.CONCEPTUAL, alias="type"
    )
    bloom_level: KnowledgeConceptualBloomLevel = Field(
        description="Bloom's taxonomy level for conceptual knowledge, used for adaptive learning and providing appropriate explanations and hints to students"
    )

    definition: str = Field(
        description="A clear and concise definition of the knowledge, used for explanations and hints"
    )
    prerequisites: list[str] = Field(
        default_factory=list,
        description="List of names of prerequisite knowledge that should be understood before this knowledge, used for providing learning paths and prerequisite hints to students",
    )
    misconceptions: list[str] = Field(
        default_factory=list,
        description="List of common misconceptions related to this knowledge, used for providing targeted explanations and hints to students",
    )
    visibility: list[KnowledgeVisibility] = Field(
        default_factory=list,
        description="List of contexts in which this knowledge should be visible",
    )
    validation_status: KnowledgeValidationStatus = Field(
        default=KnowledgeValidationStatus.PENDING,
        description="Status of the knowledge validation process, can be used to filter out unverified knowledge from retrieval results",
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score of the knowledge correctness, can be used for ranking and filtering. The value should be between 0.0 and 1.0, where 1.0 means completely confident.",
    )
    relevance_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Relevance score of the knowledge to the curriculum and learning objectives, can be used for ranking and filtering. The value should be between 0.0 and 1.0, where 1.0 means highly relevant.",
    )
    source: str = Field(
        description="Source of the knowledge, such as a textbook, lecture, or external resource. This can be used for traceability and providing additional context to students.",
    )
    learning_objective: str = Field(
        description="The specific learning objective that this knowledge is meant to address. This can be used for aligning the knowledge with the curriculum and for providing targeted explanations and hints to students.",
    )
    connections: list[ConceptualKnowledgeConnection] = Field(
        default_factory=list,
        description="List of conceptual connections from this knowledge node to others, used for structuring the knowledge graph and providing explanations to students",
    )

    children: list[ProceduralKnowledge | AssessmentKnowledge] = Field(
        default_factory=list,
        description="List of child nodes in the knowledge graph, used for hierarchical structuring and traversal. Must avoid circular references.",
    )

    @model_validator(mode="after")
    def validate_visibility(self):
        self.visibility = list(set(self.visibility))
        return self

    def set_source_recursively(self, source: str):
        self.source = source
        for child in self.children:
            if isinstance(child, ConceptualKnowledge):
                child.set_source_recursively(source)


class ProceduralKnowledge(BaseChildKnowledge):
    type_: Literal[KnowledgeType.PROCEDURAL] = Field(
        default=KnowledgeType.PROCEDURAL,
        alias="type",
        examples=[KnowledgeType.PROCEDURAL],
    )
    bloom_level: KnowledgeProceduralBloomLevel = Field(
        description="Bloom's taxonomy level for procedural knowledge, used for adaptive learning and providing appropriate explanations and hints to students",
        examples=[e.value for e in KnowledgeProceduralBloomLevel],
    )

    common_errors: list[str] = Field(
        default_factory=list,
        description="List of common errors or pitfalls related to this procedure, used for providing targeted explanations and hints to students",
        examples=[["Wrong binary path", "Using wrong initialization state"]],
    )
    visibility: list[KnowledgeVisibility] = Field(
        default_factory=list,
        description="List of contexts in which this knowledge should be visible",
        examples=[list(e.value for e in KnowledgeVisibility)],
    )
    validation_status: KnowledgeValidationStatus = Field(
        default=KnowledgeValidationStatus.PENDING,
        description="Status of the knowledge validation process, can be used to filter out unverified knowledge from retrieval results",
        examples=[[e.value for e in KnowledgeValidationStatus]],
    )
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score of the knowledge correctness, can be used for ranking and filtering. The value should be between 0.0 and 1.0, where 1.0 means completely confident.",
        examples=[0.90, 0.95],
    )
    relevance_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Relevance score of the knowledge to the curriculum and learning objectives, can be used for ranking and filtering. The value should be between 0.0 and 1.0, where 1.0 means highly relevant.",
        examples=[0.85, 0.90],
    )
    source: str = Field(
        description="Source of the knowledge, such as a textbook, lecture, or external resource. This can be used for traceability and providing additional context to students.",
        examples=["CTF_copy.pdf [page 5]"],
    )
    learning_objective: str = Field(
        description="The specific learning objective that this knowledge is meant to address. This can be used for aligning the knowledge with the curriculum and for providing targeted explanations and hints to students.",
        examples=["Execute the initialization procedure for an angr project."],
    )
    percent_done: float = Field(
        ge=0.0,
        le=100.0,
        description="For procedural knowledge, this field indicates the percentage of the procedure that has been completed. This can be used for tracking progress and providing targeted hints to students.",
        examples=[0.0, 50.0, 100.0],
    )

    child: "Optional[ProceduralKnowledge]" = Field(
        None,
        description="The next step in the procedure, used for structuring the knowledge graph and providing explanations to students. Must avoid circular references.",
    )

    @computed_field
    @property
    def completed(self) -> bool:
        return self.percent_done >= 100.0  # >= to allow for any rounding issues


class AssessmentKnowledge(BaseChildKnowledge):
    type_: Literal[KnowledgeType.ASSESSMENT] = Field(
        default=KnowledgeType.ASSESSMENT,
        alias="type",
        examples=[KnowledgeType.ASSESSMENT],
    )
    bloom_level: KnowledgeAssessmentBloomLevel = Field(
        examples=[e.value for e in KnowledgeAssessmentBloomLevel],
        description="Bloom's taxonomy level for assessment knowledge, used for adaptive learning and providing appropriate explanations and hints to students",
    )

    linked_challenges: list[str] = Field(
        default_factory=list,
        examples=[{"00_angr_find", "01_angr_symbolic_execution"}],
        description="List of challenges (e.g. quiz questions, coding exercises) that are linked to this assessment knowledge, used for providing targeted practice opportunities to students",
    )
    objectives: list[str] = Field(
        default_factory=list,
        examples=[
            "Load binary in angr",
            "Initialize a correct symbolic state",
        ],
        description="List of specific learning objectives that this assessment knowledge is meant to evaluate. This can be used for aligning the knowledge with the curriculum and for providing targeted explanations and hints to students.",
    )
    question_prompts: list[str] = Field(
        default_factory=list,
        examples=[
            "Which function creates a symbolic start state?",
            "What happens if you use full_init_state()?",
        ],
        description="List of question prompts or assessment items related to this knowledge, used for providing targeted practice opportunities to students",
    )
    evaluation_criteria: list[str] = Field(
        default_factory=list,
        examples=[
            "Binary loads without crash",
            "State includes symbolic stdin",
        ],
        description="List of criteria used for evaluating student responses related to this knowledge, used for providing targeted feedback and explanations to students",
    )

    # TODO: Confirm if AssessmentKnowledge should have children.
    # The children field is included in documentation, but it was always empty.


class RootKnowledge(BaseModel):
    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for the knowledge node, used for referencing and retrieval",
        examples=[uuid4().hex],
    )
    type_: Literal[KnowledgeType.ROOT] = Field(
        default=KnowledgeType.ROOT, alias="type", examples=[KnowledgeType.ROOT]
    )
    name: str = Field(
        default="Central node",
        description="Display name for the knowledge graph root node (course title).",
    )
    description: str = Field(
        default="",
        description="Description of the course or knowledge domain covered by this graph.",
    )
    sources: list[str] = Field(
        default_factory=list,
        description="List of source files that contributed to this knowledge graph.",
        examples=[["CTF_copy.pdf", "lecture_notes.pptx"]],
    )
    children: list[ConceptualKnowledge] = Field(
        default_factory=list,
        description="List of child nodes in the knowledge graph, used for hierarchical structuring and traversal. Must avoid circular references.",
    )

    def override_conceptual_sources(self, source: str):
        if source not in self.sources:
            self.sources.append(source)
        for child in self.children:
            child.source = source


Knowledge = (
    ConceptualKnowledge | ProceduralKnowledge | AssessmentKnowledge | RootKnowledge
)


class KnowledgeUploadStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class KnowledgeUploadRecord(BaseModel):
    id: str = Field(
        description="Unique identifier for the upload",
        default_factory=lambda: uuid.uuid4().hex,
    )
    filepath: Path = Field(description="Name of the uploaded file", exclude=True)
    status: KnowledgeUploadStatus = Field(
        default=KnowledgeUploadStatus.PENDING,
        description="Current processing status",
    )
    error_message: str | None = Field(
        default=None, description="Error message if processing failed"
    )
    knowledge_id: str | None = Field(
        default=None, description="ID of the generated knowledge graph"
    )

    created_at: datetime = Field(description="Timestamp when file was uploaded")
    updated_at: datetime | None = Field(
        default=None, description="Timestamp when file was updated"
    )

    @computed_field
    @property
    def filename(self) -> str:
        return self.filepath.name
