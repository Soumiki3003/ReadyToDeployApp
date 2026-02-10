from .student import CreateStudent, UpdateStudent
from .knowledge import KnowledgeUploadRequest, KnowledgeUploadResponse
from .file import (
    PaginatedTextualContent,
    SlideTextualContent,
    HTMLTextualContent,
    TextualContent,
)

__all__ = [
    "CreateStudent",
    "UpdateStudent",
    "KnowledgeUploadRequest",
    "KnowledgeUploadResponse",
    "PaginatedTextualContent",
    "SlideTextualContent",
    "HTMLTextualContent",
    "TextualContent",
]
