from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field
from werkzeug.datastructures import FileStorage


class KnowledgeUploadRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    files: list[FileStorage] = Field(
        min_length=1, description="List of files to be uploaded"
    )
    html_link: str | None = Field(
        default=None,
        description="Optional HTML link to be associated with the uploaded files",
    )


class KnowledgeIdsRequest(BaseModel):
    page: int = Field(1, ge=1, description="Page number for pagination")
    page_size: int = Field(5, ge=1, le=50, description="Number of items per page")


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


class KnowledgeUploadResponse(BaseModel):
    uploaded: list[Path]
    html_link: str | None
    graph_generated: bool
