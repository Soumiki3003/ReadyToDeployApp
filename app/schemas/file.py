from pydantic import BaseModel, Field


class BaseTextualContent(BaseModel):
    text: str = Field(..., description="The textual content extracted from the file")
    from_image: bool = Field(
        False, description="Whether the text was extracted from an image (OCR)"
    )


class PaginatedTextualContent(BaseTextualContent):
    page: int = Field(
        ..., description="The page number from which the text was extracted"
    )


class SlideTextualContent(BaseTextualContent):
    slide: int = Field(
        ..., description="The slide number from which the text was extracted"
    )


class HTMLTextualContent(BaseTextualContent):
    section: str = Field(
        ...,
        description="The section of the HTML document from which the text was extracted",
    )


TextualContent = PaginatedTextualContent | SlideTextualContent | HTMLTextualContent
