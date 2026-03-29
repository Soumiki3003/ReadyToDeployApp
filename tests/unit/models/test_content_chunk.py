import pytest
from pydantic import ValidationError

from app.models.knowledge import ContentChunk, ContentChunkType


def test_content_chunk_creation():
    chunk = ContentChunk(
        content="Some text content",
        page=1,
        source_file="uploads/test.pdf",
        chunk_index=0,
        course_id="course_123",
        chunk_type=ContentChunkType.PAGE,
    )
    assert chunk.content == "Some text content"
    assert chunk.page == 1
    assert chunk.source_file == "uploads/test.pdf"
    assert chunk.chunk_index == 0
    assert chunk.course_id == "course_123"
    assert chunk.chunk_type == ContentChunkType.PAGE


def test_content_chunk_default_id():
    chunk = ContentChunk(
        content="Text",
        page=0,
        source_file="test.pdf",
        chunk_index=0,
        course_id="c1",
    )
    assert isinstance(chunk.id, str)
    assert len(chunk.id) > 0


def test_content_chunk_default_chunk_type():
    chunk = ContentChunk(
        content="Text",
        page=0,
        source_file="test.pdf",
        chunk_index=0,
        course_id="c1",
    )
    assert chunk.chunk_type == ContentChunkType.PARAGRAPH


def test_content_chunk_validates_page_non_negative():
    with pytest.raises(ValidationError):
        ContentChunk(
            content="Text",
            page=-1,
            source_file="test.pdf",
            chunk_index=0,
            course_id="c1",
        )


def test_content_chunk_validates_chunk_index_non_negative():
    with pytest.raises(ValidationError):
        ContentChunk(
            content="Text",
            page=0,
            source_file="test.pdf",
            chunk_index=-1,
            course_id="c1",
        )


def test_content_chunk_validates_content_not_empty():
    with pytest.raises(ValidationError):
        ContentChunk(
            content="",
            page=0,
            source_file="test.pdf",
            chunk_index=0,
            course_id="c1",
        )


def test_content_chunk_type_values():
    assert ContentChunkType.PAGE == "page"
    assert ContentChunkType.PARAGRAPH == "paragraph"


def test_content_chunk_rejects_invalid_chunk_type():
    with pytest.raises(ValidationError):
        ContentChunk(
            content="Text",
            page=0,
            source_file="test.pdf",
            chunk_index=0,
            course_id="c1",
            chunk_type="invalid",
        )
