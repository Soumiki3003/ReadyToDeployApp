import io
import logging
from pathlib import Path

import fitz
import pytesseract
from bs4 import BeautifulSoup
from pdf2image import convert_from_path
from PIL import Image
from pptx import Presentation

from app import schemas

logger = logging.getLogger(__name__)


class FileService:
    def extract_textual_content(self, filepath: Path) -> list[schemas.TextualContent]:
        text_data = []

        if filepath.suffix == ".pdf":
            doc = fitz.open(filepath)
            for i, page in enumerate(doc.pages(), 1):
                text = page.get_text("text").strip()
                if text:
                    text_data.append(
                        schemas.PaginatedTextualContent(
                            page=i, text=text, from_image=False
                        )
                    )

        elif filepath.suffix == ".pptx":
            prs = Presentation(filepath.as_posix())
            for i, slide in enumerate(prs.slides, 1):
                slide_text = " ".join(
                    getattr(shape, "text")
                    for shape in slide.shapes
                    if hasattr(shape, "text")
                )
                text_data.append(
                    schemas.SlideTextualContent(
                        slide=i, text=slide_text, from_image=False
                    )
                )

        elif filepath.suffix == ".html":
            with open(filepath, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f, "html.parser")
            body_text = soup.get_text(separator=" ", strip=True)
            text_data.append(
                schemas.HTMLTextualContent(
                    section="html", text=body_text, from_image=False
                )
            )

        else:
            logger.warning(
                f"Unsupported file type for textual content extraction: {filepath.suffix}"
            )

        return text_data

    def extract_visual_content(self, filepath: Path) -> list[schemas.TextualContent]:
        visual_text = []

        if filepath.suffix == ".pdf":
            pages = convert_from_path(filepath, dpi=200)
            for i, page_img in enumerate(pages, 1):
                ocr_text = pytesseract.image_to_string(page_img)
                if ocr_text.strip():
                    visual_text.append(
                        schemas.PaginatedTextualContent(
                            page=i, text=ocr_text.strip(), from_image=True
                        )
                    )

        elif filepath.suffix == ".pptx":
            prs = Presentation(filepath.as_posix())
            for i, slide in enumerate(prs.slides, 1):
                for shape in slide.shapes:
                    if shape.shape_type == 13:  # picture
                        image = getattr(shape, "image", None)
                        if image is None:
                            continue
                        image_bytes = io.BytesIO(image.blob)
                        img = Image.open(image_bytes)
                        ocr_text = pytesseract.image_to_string(img)
                        if not isinstance(ocr_text, str):
                            logger.warning(
                                f"OCR returned non-string result for slide {i} in {filepath.name}"
                            )
                            continue
                        if ocr_text.strip():
                            visual_text.append(
                                schemas.SlideTextualContent(
                                    slide=i,
                                    text=ocr_text.strip(),
                                    from_image=True,
                                )
                            )
        else:
            logger.warning(
                f"Unsupported file type for visual content extraction: {filepath.suffix}"
            )

        return visual_text
