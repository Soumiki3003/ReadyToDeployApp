import pytest

from app.models.knowledge import ContentChunkType
from app.schemas.file import (
    HTMLTextualContent,
    PaginatedTextualContent,
    SlideTextualContent,
)
from app.services.file import FileService


@pytest.fixture
def file_service():
    return FileService()


def test_chunk_single_page_no_paragraphs(file_service):
    contents = [PaginatedTextualContent(page=1, text="Simple text")]
    chunks = file_service.chunk_textual_content(
        contents, source_file="test.pdf", course_id="c1"
    )
    assert len(chunks) == 1
    assert chunks[0].chunk_type == ContentChunkType.PAGE
    assert chunks[0].content == "Simple text"
    assert chunks[0].page == 1
    assert chunks[0].chunk_index == 0


def test_chunk_single_page_with_paragraphs(file_service):
    contents = [
        PaginatedTextualContent(page=1, text="Para one\n\nPara two\n\nPara three")
    ]
    chunks = file_service.chunk_textual_content(
        contents, source_file="test.pdf", course_id="c1"
    )
    # 1 page-level + 3 paragraph-level = 4 chunks
    assert len(chunks) == 4
    assert chunks[0].chunk_type == ContentChunkType.PAGE
    assert chunks[0].content == "Para one\n\nPara two\n\nPara three"
    assert chunks[1].chunk_type == ContentChunkType.PARAGRAPH
    assert chunks[1].content == "Para one"
    assert chunks[2].content == "Para two"
    assert chunks[3].content == "Para three"
    # chunk_index increments globally
    assert [c.chunk_index for c in chunks] == [0, 1, 2, 3]


def test_chunk_multiple_pages_global_index(file_service):
    contents = [
        PaginatedTextualContent(page=1, text="Page one text"),
        PaginatedTextualContent(page=2, text="Page two text"),
    ]
    chunks = file_service.chunk_textual_content(
        contents, source_file="test.pdf", course_id="c1"
    )
    assert len(chunks) == 2
    assert chunks[0].page == 1
    assert chunks[0].chunk_index == 0
    assert chunks[1].page == 2
    assert chunks[1].chunk_index == 1


def test_chunk_filters_empty_paragraphs(file_service):
    contents = [PaginatedTextualContent(page=1, text="Para\n\n\n\nPara2")]
    chunks = file_service.chunk_textual_content(
        contents, source_file="test.pdf", course_id="c1"
    )
    # 1 page + 2 paragraphs (empty one filtered out)
    paragraph_chunks = [c for c in chunks if c.chunk_type == ContentChunkType.PARAGRAPH]
    assert len(paragraph_chunks) == 2
    assert paragraph_chunks[0].content == "Para"
    assert paragraph_chunks[1].content == "Para2"


def test_chunk_slide_content_uses_slide_number(file_service):
    contents = [SlideTextualContent(slide=3, text="Slide text")]
    chunks = file_service.chunk_textual_content(
        contents, source_file="deck.pptx", course_id="c1"
    )
    assert len(chunks) == 1
    assert chunks[0].page == 3


def test_chunk_html_content_uses_page_zero(file_service):
    contents = [HTMLTextualContent(section="html", text="Section text")]
    chunks = file_service.chunk_textual_content(
        contents, source_file="page.html", course_id="c1"
    )
    assert len(chunks) == 1
    assert chunks[0].page == 0


def test_chunk_empty_list(file_service):
    chunks = file_service.chunk_textual_content(
        [], source_file="test.pdf", course_id="c1"
    )
    assert chunks == []


def test_chunk_propagates_source_and_course(file_service):
    contents = [PaginatedTextualContent(page=1, text="Text")]
    chunks = file_service.chunk_textual_content(
        contents, source_file="uploads/doc.pdf", course_id="course_abc"
    )
    for chunk in chunks:
        assert chunk.source_file == "uploads/doc.pdf"
        assert chunk.course_id == "course_abc"


def test_chunk_skips_duplicate_paragraph_when_single(file_service):
    """When text has no \\n\\n splits, only the page chunk is created (no duplicate paragraph)."""
    contents = [PaginatedTextualContent(page=1, text="Single paragraph only")]
    chunks = file_service.chunk_textual_content(
        contents, source_file="test.pdf", course_id="c1"
    )
    assert len(chunks) == 1
    assert chunks[0].chunk_type == ContentChunkType.PAGE
